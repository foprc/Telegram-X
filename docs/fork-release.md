# Telegram X Dual 发布流程

此配置只用于 `foprc/Telegram-X`，保留官方 PR 分支 `feat/adaptive-dual-pane`。
应用名为 **Telegram X Dual**，包名为 `io.github.foprc.telegramx`。
首次只构建 `latest` flavor 的 arm64-v8a 签名 Release APK，关闭 Firebase 推送。
首次安装使用独立应用数据，不会覆盖官方版。GitHub 发布附件不提供应用内自动更新。

## 一次性配置

1. 在 https://my.telegram.org/apps 申请自己的 Telegram API ID / Hash，写入本机
   `local.properties` 的 `telegram.api_id` 和 `telegram.api_hash`。不要提交此文件。
2. 确保 `gh auth status` 正常并使用有仓库管理权限的 foprc 账号。
3. 在仓库根目录运行：

   ```sh
   python3 scripts/fork/setup-secrets.py
   ```

脚本生成专用 RSA 签名密钥，保存在已忽略的 `release-private/`，并通过标准输入上传
GitHub Secrets，不在日志中输出密码。已存在的远程 Secrets 不会被覆盖。
请把整个 `release-private/` 加密备份到仓库之外；后续版本必须继续使用此密钥。
该脚本不会更改现有本地 debug 构建配置。

使用的仓库 Secrets：

| 名称 | 内容 |
| --- | --- |
| `TELEGRAM_API_ID` | 自己申请的 Telegram API ID |
| `TELEGRAM_API_HASH` | 对应 API Hash |
| `RELEASE_KEYSTORE_BASE64` | 专用密钥文件的 Base64 |
| `RELEASE_STORE_PASSWORD` | 密钥库密码 |
| `RELEASE_KEY_ALIAS` | 签名别名 |
| `RELEASE_KEY_PASSWORD` | 签名密码 |

也可以在仓库 Settings → Secrets and variables → Actions 手动添加。

## 触发构建

初次使用标签触发，不要求改动 fork 的默认分支。先确认标签指向包含双栏功能和发布工作流的提交：

```sh
git switch fork/release
git pull --ff-only
git tag fork-v1833
git push origin fork-v1833
```

`1833` 是本次 `app.version`，后续用递增整数（如 `1834`），每个版本使用新标签。
不要复用或移动已发布标签。官方合并更新后也应继续保证 fork 的版本号递增。
标签必须为 `fork-v` 加至多六位正整数。GitHub tag 名称不会直接变成 APK 的 versionName；
项目会根据 `app.version` 和既有规则生成 Android 版本号。

工作流会检出标签对应源码及递归子模块，安装 JDK 25、版本配置指定的 SDK/NDK/Rust，
运行双栏单元测试，构建并验证签名，上传 APK 与 SHA256SUMS.txt，最后创建 **预发布草稿**。
缺少 Secrets 会在构建前报错，不会使用示例 Telegram 凭据发布。

如果 fork 默认分支已经含此工作流，也可从 Actions → Fork release → Run workflow
选择 `fork/release` 分支并输入 build_number；该方式仍创建相同格式的版本标签和草稿。
工作流在默认分支不可见时直接使用标签方式。

## 检查和公开下载

1. 从 Actions 或 Release 草稿下载 APK，安装到 arm64 真机。
2. 检查登录、收发消息、双栏切换、返回手势、键盘、账号切换及 RTL。
3. 在 https://github.com/foprc/Telegram-X/releases 打开草稿，补充实际验证结果。
4. 保留 Pre-release 标记，点击 Publish release 后才公开下载。

首次 Ubuntu CI 构建耗时较长；完整工作流仍需在真实 GitHub runner 验证。
构建产物以 Actions artifact 保留 14 天，公开发布后的 Release 附件不受此期限影响。
当前配置不打包 legacy/lollipop 等旧系统版本，也不配置 Firebase 推送。

配置验证（2026-11-19）：`actionlint` 通过；配置脚本在隔离临时目录中验证了
文件生成、0600 权限、拒绝覆盖已有配置和拒绝示例 API ID。专用签名四项 Secrets 已配置。
未创建版本标签、未触发远程构建、未公开 Release；等待用户提供自己的 Telegram API 凭据。

## 本地复现

在独立干净 checkout 中设置上述六个 Secrets 对应的环境变量，以及
`FORK_BUILD_NUMBER`、`ANDROID_SDK_ROOT`、`FORK_RUST_HOME`，然后运行：

```sh
python3 scripts/fork/configure-release.py
./gradlew :app:assembleLatestRelease -Pabi=arm64 --console=plain
```

配置脚本拒绝覆盖已有 local.properties。签名和本地配置文件始终不应加入 Git。
