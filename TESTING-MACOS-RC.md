# macOS RC 公开验收指南

感谢帮助验收 `parse-video v1.0.0-rc.3`。这是候选版，不是正式稳定版。

## 适用范围

- Apple Silicon：下载文件名包含 `macos-arm64`。
- Intel Mac：下载文件名包含 `macos-x64`。
- 只使用有权处理、无需登录即可观看的公开视频。
- 不提交 Cookie、Token、用户名、完整个人路径或私密链接。

## 最小验收顺序

1. 对照 GitHub Release 核对 ZIP 的 SHA-256。
2. 完整解压后运行 `verify.command`，确认清单全部一致。
3. 运行 `install.command`，确认不要求管理员权限、不修改系统 PATH。
4. 运行 `doctor.command`，记录解析器、FFmpeg、Whisper 和模型状态。
5. 在已有 FFmpeg/Whisper 依赖的环境中，使用自己的公开链接测试下载、理解和蒸馏。
6. 运行 `rollback.command` 或 `uninstall.command`，确认已有视频和证据包未被删除。

## 必须核对的结果

- 下载模式：媒体进入当前用户桌面的“下载视频”，每条视频一个目录。
- 理解模式：成功、失败或中断后不遗留完整 MP4/WAV。
- 蒸馏模式：只在“文档/Parse Video/证据包”长期保留可审计证据。
- 遇验证码、登录、付费、私密权限或 DRM 时停止，不读取 Cookie。
- 机器未安装 Python 时，包内自包含助手仍能运行 `--help`、安装和诊断。

当前包尚未签名或公证。若 Gatekeeper 阻止启动，请先核对发布页 SHA-256，再通过“系统设置 → 隐私与安全性”查看系统提供的“仍要打开”选项；不要关闭整机安全机制。

GitHub Actions 通过只证明对应 runner 上构建、安装和清单校验可运行，不能替代真实用户机器的视频端到端验收。
