#!/usr/bin/env python3
"""Create a dedicated fork signing key and upload repository Secrets via gh.

The local backup stays in ignored release-private/. Existing keys are reused.
Telegram credentials are read from local.properties; sample credentials are rejected.
"""
import base64
import json
import os
from pathlib import Path
import re
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REPO = "foprc/Telegram-X"


def main():
    subprocess.run(["gh", "auth", "status"], check=True)
    existing = json.loads(subprocess.check_output(
        ["gh", "secret", "list", "-R", REPO, "--json", "name"], text=True))
    names = {entry["name"] for entry in existing}
    signing_names = {"RELEASE_KEYSTORE_BASE64", "RELEASE_STORE_PASSWORD",
                     "RELEASE_KEY_ALIAS", "RELEASE_KEY_PASSWORD"}
    private = ROOT / "release-private"
    private.mkdir(mode=0o700, exist_ok=True)
    backup = private / "signing.json"
    if not backup.exists():
        if names & signing_names:
            raise SystemExit("Remote signing Secrets already exist. Restore their local key backup first; refusing to replace them.")
        key = private / "release.jks"
        if key.exists():
            raise SystemExit("release.jks exists without signing.json; restore its password backup first")
        password = secrets.token_urlsafe(36)
        values = {"RELEASE_STORE_PASSWORD": password, "RELEASE_KEY_PASSWORD": password,
                  "RELEASE_KEY_ALIAS": "telegram-x-dual"}
        env = dict(os.environ, FORK_KEY_PASSWORD=password)
        subprocess.run([
            "keytool", "-genkeypair", "-noprompt", "-keystore", str(key),
            "-storetype", "PKCS12", "-alias", values["RELEASE_KEY_ALIAS"],
            "-keyalg", "RSA", "-keysize", "4096", "-validity", "10000",
            "-dname", "CN=Telegram X Dual, OU=Fork, O=foprc",
            "-storepass:env", "FORK_KEY_PASSWORD", "-keypass:env", "FORK_KEY_PASSWORD",
        ], check=True, env=env)
        key.chmod(0o600)
        with os.fdopen(os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
            json.dump(values, f)
    values = json.loads(backup.read_text())
    values["RELEASE_KEYSTORE_BASE64"] = base64.b64encode((private / "release.jks").read_bytes()).decode()
    # Do not silently overwrite a signing identity already configured on GitHub.
    for name, value in values.items():
        if name in names:
            print(f"Keeping existing Secret: {name}")
            continue
        subprocess.run(["gh", "secret", "set", name, "-R", REPO], input=value, text=True, check=True)
        print(f"Configured Secret: {name}")
    properties = ROOT / "local.properties"
    config = {}
    if properties.exists():
        config = dict(line.strip().split("=", 1) for line in properties.read_text().splitlines()
                      if "=" in line and not line.lstrip().startswith("#"))
    api_id = config.get("telegram.api_id", "")
    api_hash = config.get("telegram.api_hash", "")
    if (not api_id.isdigit() or int(api_id) <= 0 or api_id == "94575"
            or not re.fullmatch(r"[a-fA-F0-9]{32}", api_hash)):
        print("Signing configured. Telegram API Secrets still need your own credentials in local.properties; rerun this script after configuring them.")
        return
    for name, value in {"TELEGRAM_API_ID": api_id, "TELEGRAM_API_HASH": api_hash}.items():
        if name not in names:
            subprocess.run(["gh", "secret", "set", name, "-R", REPO], input=value, text=True, check=True)
            print(f"Configured Secret: {name}")
    print("Release Secrets configured. Back up release-private/ securely outside the repository.")


if __name__ == "__main__":
    main()
