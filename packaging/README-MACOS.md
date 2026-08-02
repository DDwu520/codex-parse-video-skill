# parse-video macOS 候选版

本候选包分别面向 Apple Silicon（M1/M2/M3/M4）和 Intel Mac。它包含解析器和自包含运行助手，不要求用户预装 Python，也不需要管理员权限。

## 安装

1. 从 GitHub Release 下载与处理器一致的 ZIP，并先对照发布页核对 SHA-256。
2. 完整解压 ZIP，运行 `verify.command` 核对包内清单。
3. 运行 `install.command`，默认安装到 `~/.codex/skills/parse-video`。
4. 运行 `doctor.command` 检查解析器、FFmpeg、Whisper 和模型状态。

若 macOS 阻止未签名程序，请先确认 ZIP 的 SHA-256 与公开发布页一致，再到“系统设置 → 隐私与安全性”查看系统给出的“仍要打开”选项。不要关闭整机安全机制。

## 使用

在终端进入解压目录后运行：

```bash
./parse-video.command doctor
./parse-video.command download "公开视频分享文本或链接"
./parse-video.command understand "公开视频分享文本或链接"
./parse-video.command distill "公开视频分享文本或链接"
```

- 下载：保存到当前用户桌面的“下载视频”，每条视频一个独立目录。
- 理解：完整媒体只进入系统临时目录，处理完成或失败后清理。
- 蒸馏：完整 MP4/WAV 清理，只把证据包保存在“文档/Parse Video/证据包”。

包内不捆绑 FFmpeg、Whisper CLI 或语音模型。`doctor.command` 会如实报告缺少的依赖；依赖助手不会静默下载。

## 安全边界

- 只处理有权下载或合法归档、无需登录即可观看的公开视频。
- 不读取 Cookie，不绕过验证码、登录、付费、私密权限或 DRM。
- 不启动上游默认 HTTP 服务。
- 当前候选程序尚未使用 Apple Developer ID 签名或公证，真实用户验收前不能称正式稳定版。
