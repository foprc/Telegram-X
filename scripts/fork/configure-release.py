#!/usr/bin/env python3
"""Write CI-only signing/configuration files; never print secret values."""
import base64
import os
from pathlib import Path
import re


def required(name):
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"Missing required secret/environment variable: {name}")
    return value


def properties(values):
    def escape(value):
        return (str(value).replace("\\", "\\\\").replace("\n", "\\n")
                .replace("\r", "\\r").replace("\t", "\\t").replace(" ", "\\ "))
    return "".join(f"{key}={escape(value)}\n" for key, value in values.items())


def main():
    api_id = required("TELEGRAM_API_ID")
    api_hash = required("TELEGRAM_API_HASH")
    if not api_id.isdigit() or int(api_id) <= 0 or api_id == "94575":
        raise SystemExit("Configure your own positive Telegram API ID, not the sample ID")
    if not re.fullmatch(r"[a-fA-F0-9]{32}", api_hash):
        raise SystemExit("Telegram API hash must contain 32 hexadecimal characters")
    build = required("FORK_BUILD_NUMBER")
    if not re.fullmatch(r"[1-9][0-9]{0,5}", build):
        raise SystemExit("Build number must be a positive integer of at most six digits")
    root = Path(__file__).resolve().parents[2]
    if (root / "local.properties").exists():
        raise SystemExit("Refusing to overwrite local.properties; use a clean checkout")
    private = root / "release-private"
    private.mkdir(mode=0o700, exist_ok=True)
    key = private / "release.jks"
    encoded = required("RELEASE_KEYSTORE_BASE64")
    key_data = base64.b64decode("".join(encoded.split()), validate=True)
    if not key_data:
        raise SystemExit("Empty release keystore")
    signing = properties({
        "keystore.file": key,
        "keystore.password": required("RELEASE_STORE_PASSWORD"),
        "key.alias": required("RELEASE_KEY_ALIAS"),
        "key.password": required("RELEASE_KEY_PASSWORD"),
    })
    config = properties({
        "sdk.dir": required("ANDROID_SDK_ROOT"),
        "rust.dir": required("FORK_RUST_HOME"),
        "app.id": "io.github.foprc.telegramx",
        "app.name": "Telegram X Dual",
        "app.file": "Telegram-X-Dual",
        "app.version": build,
        "app.experimental": "true",
        "app.sources_url": "https://github.com/foprc/Telegram-X",
        "app.download_url": "https://github.com/foprc/Telegram-X/releases",
        "tgx.extension": "none",
        "telegram.api_id": api_id,
        "telegram.api_hash": api_hash,
        "keystore.file": private / "keystore.properties",
    })
    # Restrict permissions from creation, including on the temporary CI runner.
    for path, data in [(key, key_data), (private / "keystore.properties", signing.encode()),
                       (root / "local.properties", config.encode())]:
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as file:
            file.write(data)
    print("Configured Telegram X Dual release (Firebase push disabled)")


if __name__ == "__main__":
    main()
