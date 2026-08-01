# parse-video Windows x64 候选版

当前状态：`v1.0.0-rc.1` 候选包。

它已经完成 Windows x64 交叉编译、离线结构测试和安装/回滚测试，但尚未在真实 Windows 10/11 x64 电脑上完成端到端验收。不要把本候选包宣传为 Windows 正式稳定版。

## 安装

1. 完整解压 ZIP，不能只从压缩包预览窗口运行。
2. 双击 `verify.cmd`，确认文件集合、大小和 SHA-256 全部匹配。
3. 双击 `install.cmd`。
4. 双击 `doctor.cmd` 检查解析器、FFmpeg、Whisper 和模型状态。

安装默认写入 `%CODEX_HOME%\skills\parse-video`；未设置 `CODEX_HOME` 时使用当前用户的 `.codex\skills\parse-video`。安装不需要管理员权限，不修改注册表、系统 `PATH` 或 PowerShell 执行策略。

## 使用

命令行入口：

```bat
parse-video.cmd doctor
parse-video.cmd download "公开视频分享文本或链接"
parse-video.cmd understand "公开视频分享文本或链接"
parse-video.cmd distill "公开视频分享文本或链接"
```

- 下载：保存到 Windows 系统登记的真实桌面下“下载视频”文件夹；每条视频一个独立目录。
- 理解：完整媒体只进入系统临时目录，报告读取后清理。
- 蒸馏：完整 MP4/WAV 清理，只把证据包保存在系统“文档\Parse Video\证据包”。

本候选包暂未捆绑 FFmpeg、Whisper CLI 或语音模型。`doctor.cmd` 会如实说明哪些模式可用；缺少依赖时不会静默联网下载。

需要补依赖时先查看来源、体积、SHA-256 和许可：

```bat
parse-video.cmd dependencies plan all
```

只有确认约 262 MB 的下载及本地占用后，才执行：

```bat
parse-video.cmd dependencies install all --confirm-download
```

也可以只安装下载/画面处理必需的 `media`，或单独安装 `asr`。依赖助手固定版本和 SHA-256，校验失败不会安装。

## 回滚和卸载

- `rollback.cmd`：恢复最近一次升级前的 Skill。
- `uninstall.cmd`：把当前 Skill 移到可恢复备份目录。

回滚和卸载均不会删除桌面视频、蒸馏证据包或语音模型。

## 安全边界

- 只处理有权下载或合法归档的公开内容。
- 不读取浏览器 Cookie，不要求提前打开或登录浏览器。
- 不绕过验证码、登录、付费、私密权限、DRM 或其他访问限制。
- 不启动 parse-video 默认 HTTP 服务。
- 未签名程序可能触发 SmartScreen；请先对照 `manifest.json` 或发布页的 SHA-256。
