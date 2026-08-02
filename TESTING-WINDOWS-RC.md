# Windows RC 公开验收指南

感谢帮助验收 `parse-video v1.0.0-rc.2`。这是 Windows x64 候选版，不是正式稳定版。

## 适用范围

- Windows 10 或 Windows 11，x64 处理器。
- 只使用你有权处理、无需登录即可观看的公开视频。
- 不测试验证码、付费、私密权限、DRM 或绕过平台限制。
- 不要在反馈中粘贴 Cookie、Token、用户名、完整个人目录或私密链接。

## 下载与完整性

从 GitHub Releases 下载 `parse-video-v1.0.0-rc.2-windows-x64.zip`，完整解压后运行 `verify.cmd`。

发布包 SHA-256：

```text
0576bbafb24af3c73bf8b7a8f81241158ed365af5a4f9dc0d3b65835707c49f7
```

如果 `verify.cmd` 报告缺失、额外文件或哈希不一致，请停止安装并提交反馈。

## 最小验收顺序

1. 双击 `verify.cmd`，确认 61 个登记文件全部一致。
2. 双击 `install.cmd`，确认不要求管理员权限、不修改系统 PATH。
3. 双击 `doctor.cmd`，记录解析器、FFmpeg、Whisper 和模型状态。
4. 在命令提示符中运行 `parse-video.cmd dependencies plan all`，确认它只展示来源、许可、大小和校验值，不自动联网下载。
5. 若你同意约 262 MB 下载和相应磁盘占用，再运行 `parse-video.cmd dependencies install all --confirm-download`。
6. 使用你自己的公开链接分别测试 `download`、`understand`、`distill`。
7. 运行 `rollback.cmd` 或 `uninstall.cmd`，确认已有视频和证据包未被删除。

## 必须核对的结果

- 下载模式：完整媒体进入系统真实桌面的“下载视频”目录，每条视频一个文件夹。
- 理解模式：媒体只进入系统临时目录，成功、失败或中断后不遗留完整 MP4/WAV。
- 蒸馏模式：系统“文档\Parse Video\证据包”中只保留证据，不能残留完整 MP4/WAV。
- 遇登录、验证码、付费、私密权限或 DRM 时停止，不要求 Cookie，也不尝试绕过。
- 中文用户名、含空格目录、长视频标题和 Windows 保留名不能造成越界写入或假成功。

## 建议测试平台

第一轮优先测试抖音和微博的下载、理解、蒸馏三模式；再分别测试 B 站、小红书和快手下载。不要为了凑平台数量测试来历不明或无权处理的内容。

## 如何反馈

在 GitHub Issues 中选择“Windows RC 验收”模板。请提供脱敏后的命令输出和错误信息；本机路径可写成 `%USERPROFILE%`，链接只写平台和公开/受限状态即可。

只有真实 Windows 10/11 验收通过后，Windows 状态才会从 `candidate-only` 升级为“可用”。GitHub Actions 通过不能代替真实用户机器验收。
