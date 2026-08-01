---
knowledge_version: 1
last_scanned_at: 2026-06-08
source_commit: ac2a71f
confidence: high
---

# 核心业务流程

## 流程：分享链接解析

### 是否已确认

- 状态：已确认
- 证据来源：`parser/parser.go`、`cmd/handlers.go`、`utils/utils.go`

### 触发入口

| 类型 | 路径/接口/命令 | 入口代码 |
|---|---|---|
| HTTP API | `GET /api/v1/parse?url=xxx` | `cmd/handlers.go:v1ParseURLHandler` |
| HTTP Legacy | `GET /video/share/url/parse?url=xxx` | `cmd/handlers.go:legacyParseURLHandler` |
| CLI | `go run main.go parse "分享文案"` | `cmd/parse.go:parseCmd` |

### 执行链路

1. 从输入字符串中用正则提取 URL（`utils.RegexpMatchUrlFromString`）
2. 遍历 `videoSourceInfoMapping`，通过 `strings.Contains` 匹配域名到平台 source
3. 获取该平台的 `videoShareUrlParser` 实现
4. 调用 `parseShareUrl(shareUrl)` 执行平台特定解析
5. 返回 `VideoParseInfo`（包含作者、标题、视频地址、封面、图集等）

### 关键代码

| 函数/文件 | 职责 | 来源 |
|---|---|---|
| `utils.RegexpMatchUrlFromString` | 正则提取 URL | `utils/utils.go:8` |
| `parser.ParseVideoShareUrl` | 域名匹配 → 平台路由 | `parser/parser.go:23` |
| `parser.ParseVideoShareUrlByRegexp` | 正则+路由组合入口 | `parser/parser.go:13` |
| 各平台 `parseShareUrl` | 平台特定解析逻辑 | `parser/douyin.go`、`parser/kuaishou.go` 等 |

### 数据流

- **输入**：包含分享链接的文本（如 `7.87 Pjm:/ 复制打开抖音 https://v.douyin.com/xxx`）
- **处理**：URL 提取 → 域名匹配 → HTTP 请求平台页面/接口 → 解析 JSON/HTML
- **输出**：`VideoParseInfo` 结构体
- **存储**：无持久化

### 异常处理

- URL 提取失败：返回 `str not have url` 错误
- 域名不匹配：返回 `not have source config` 错误
- 平台接口异常：返回原始错误，HTTP API 分类为 422 PARSE_FAILED
- HTTP API 层有 Recovery 中间件兜底 panic

---

## 流程：视频 ID 解析

### 是否已确认

- 状态：已确认
- 证据来源：`parser/parser.go:ParseVideoId`

### 触发入口

| 类型 | 路径/接口/命令 | 入口代码 |
|---|---|---|
| HTTP API | `GET /api/v1/parse/:source/:video_id` | `cmd/handlers.go:v1ParseIDHandler` |
| HTTP Legacy | `GET /video/id/parse?source=xxx&video_id=xxx` | `cmd/handlers.go:legacyParseIDHandler` |
| CLI | `go run main.go id --source douyin "视频ID"` | `cmd/id.go:idCmd` |

### 执行链路

1. 验证 source 和 videoId 非空
2. 从 `videoSourceInfoMapping` 查找平台
3. 检查平台是否实现了 `videoIdParser` 接口
4. 调用 `parseVideoID(videoId)` 执行解析
5. 返回 `VideoParseInfo`

### 关键代码

| 函数/文件 | 职责 | 来源 |
|---|---|---|
| `parser.ParseVideoId` | source 查找 + ID 解析路由 | `parser/parser.go:53` |
| 各平台 `parseVideoID` | 平台特定 ID 解析 | 部分平台解析器 |

---

## 流程：批量解析

### 是否已确认

- 状态：已确认
- 证据来源：`cmd/parse.go:runBatchParse`、`parser/parser.go:BatchParseVideoId`

### 执行链路

1. 从命令行参数或文件读取多条输入
2. 使用 goroutine + semaphore channel（并发度 8）并发解析
3. 收集结果到 `[]batchResult`（含成功/失败标记）
4. 统一输出（text 或 JSON）
5. 可选下载媒体文件

### 关键代码

| 函数/文件 | 职责 | 来源 |
|---|---|---|
| `cmd/parse.go:runBatchParse` | CLI 批量解析编排 | `cmd/parse.go:100` |
| `parser.BatchParseVideoId` | 库级别批量 ID 解析 | `parser/parser.go:67` |

---

## 流程：HTTP 请求中间件链

### 是否已确认

- 状态：已确认
- 证据来源：`cmd/serve.go:43-47`、`cmd/middleware.go`

### 执行链路

1. **Recovery** → 捕获 panic，返回 500 INTERNAL_ERROR
2. **CORS** → 根据 `CORS_ORIGINS` 配置设置响应头
3. **日志** → 记录方法、路径、状态码、耗时
4. **速率限制** → 基于 IP 的令牌桶限流，超限返回 429
5. **Basic Auth** → 可选，通过环境变量开启，`/api/v1/health` 和 `/api/v1/platforms` 豁免

### 配置项

| 配置项 | 用途 | 读取位置 |
|---|---|---|
| `RATE_LIMIT_RPM` | 每分钟每 IP 最大请求数 | `cmd/serve.go:32` |
| `CORS_ORIGINS` | 允许的跨域来源 | `cmd/serve.go:33` |
| `PARSE_VIDEO_USERNAME` | Basic Auth 用户名 | `cmd/serve.go:34` |
| `PARSE_VIDEO_PASSWORD` | Basic Auth 密码 | `cmd/serve.go:35` |

---

## 流程：媒体文件下载

### 是否已确认

- 状态：已确认
- 证据来源：`cmd/download.go`

### 执行链路

1. 创建输出目录
2. 依次下载：视频 → 图集（含 LivePhoto）→ 封面 → 音乐
3. 文件名以视频标题为前缀，自动推断扩展名
4. 视频/图集下载失败直接返回错误，封面/音乐失败仅警告
5. 解析结果没有任何媒体地址时返回错误，不再把零文件当作下载成功
6. 微博 CDN 请求补充公开微博 Referer；不读取 Cookie 或登录状态

### 未确认事项

- 未确认各平台解析器内部 HTTP 请求的超时和重试策略。

---

## 流程：Codex Skill 三模式

### 是否已确认

- 状态：macOS 回归与离线夹具已确认；Windows 真实机器待确认
- 证据来源：`skill/parse-video/scripts/parse_video.py`、`download.py`、`prepare_distillation.py`

### 执行链路

1. `runtime_paths.py` 解析当前系统、架构、`CODEX_HOME`、真实桌面/文档和隔离临时目录。
2. 下载模式先在临时任务目录调用固定解析器，再用 ffprobe 确认可识别媒体流。
3. 下载成功后生成跨 Windows 安全目录名，一条视频一个目录；失败、超时或零媒体不写桌面。
4. 理解/蒸馏模式临时提取音频和均匀关键帧，生成带时间戳 ASR 与证据清单；完整 MP4/WAV 不长期保留。
5. 理解模式报告完成后按精确 `cleanup_argv` 清理；蒸馏模式只保留 candidate-only 证据包。
6. `doctor.py` 只读报告三模式依赖；`dependencies.py` 必须先展示来源、许可、体积和 SHA-256，只有显式 `--confirm-download` 才联网安装。

### 安全边界

- 不读取 Cookie、账号或浏览器登录态，不绕过验证码、付费、私密权限或 DRM。
- 不启动默认 HTTP 服务。
- Windows 子进程以独立进程组启动，超时/中断时终止进程树。
- Windows V1 只批量下载；批量理解和蒸馏不在 V1 范围。
