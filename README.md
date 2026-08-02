# parse-video：把公开视频链接交给 Codex 下载、理解或蒸馏

你只要把一条公开视频的分享链接发给 Codex，就可以让它处理；不需要先手动下载视频、上传文件、打开浏览器或登录平台。

目前可处理固定解析器已登记平台的公开链接，例如抖音、哔哩哔哩、小红书、快手、微博、西瓜和腾讯视频等。已完成真实验证的平台与未验证边界，请看 [`platform-validation.md`](skill/parse-video/references/platform-validation.md)。

## 先下载适合你的版本

请从 [GitHub Releases](https://github.com/DDwu520/codex-parse-video-skill/releases/tag/v1.0.0-rc.3) 下载：

| 你的电脑 | 下载文件 |
| --- | --- |
| Windows 10/11 x64 | `parse-video-v1.0.0-rc.3-windows-x64.zip` |
| M 系列 Mac（M1/M2/M3/M4） | `parse-video-v1.0.0-rc.3-macos-arm64.zip` |
| Intel Mac | `parse-video-v1.0.0-rc.3-macos-x64.zip` |

下载后先核对 Release 页面提供的 `SHA256SUMS.txt`，再完整解压 ZIP。安装和使用步骤见：[Windows 说明](packaging/README-WINDOWS.md)｜[macOS 说明](packaging/README-MACOS.md)。

## 这个 Skill 能做什么

| 你对 Codex 说 | 它会做什么 | 最终保留什么 |
| --- | --- | --- |
| “下载这个视频” | 下载完整媒体到桌面“下载视频”，每条视频单独一个文件夹 | 完整视频 |
| “理解 / 总结这个视频” | 临时读取视频、转写口播、抽取关键画面并交叉核对 | 理解报告；完整视频和音频会清理 |
| “蒸馏这个视频” | 生成可审计证据包，交给仓颉阶段 0 评估可提炼的候选 Skill | 时间戳转写、关键帧、证据包；完整视频和音频会清理 |

理解与蒸馏并不等于“完全不用传输媒体”，而是你不用手动下载，且桌面不会保留完整视频。动作教学、软件操作和复杂课件会提高抽帧密度；ASR 不是人工逐字稿，重要结论会结合时间戳、画面和元数据复核。

## 最短使用方式

安装后，在 Codex 对话中直接粘贴一条公开分享链接，并说清意图，例如：

```text
下载这个视频：https://v.douyin.com/xxxx/
总结这个视频：https://www.bilibili.com/video/BVxxxx
蒸馏这个视频：https://www.xiaohongshu.com/explore/xxxx
```

也可以在终端运行包内入口。Windows 使用 `parse-video.cmd`，macOS 使用 `parse-video.command`；先执行 `doctor` 查看 FFmpeg、Whisper 和本地模型是否就绪。

## 重要边界

- 只处理你有权下载或合法归档、无需登录即可观看的公开视频。
- 不读取浏览器 Cookie，不要求浏览器提前打开或登录。
- 不绕过验证码、登录、付费、私密权限、DRM 或其他访问限制；遇到这些情况会停止并说明原因。
- 不启动上游默认 HTTP 服务；普通用户不需要编译 Go、运行 Docker 或开启端口。
- 微信视频号当前不支持；“解析器登记支持”不等于“已在真实平台验证”。
- Windows x64、Apple Silicon Mac、Intel Mac 的 RC.3 自动化构建、安装和清单校验均已通过；但真实用户三模式验收仍在收集，本版本保持 `candidate`，不是正式稳定版。

## 给开发者：上游解析器原始说明

本仓库基于 [`wujunwei928/parse-video`](https://github.com/wujunwei928/parse-video) 的 MIT 许可源码。以下内容保留上游 Go、Docker 与 HTTP 解析服务的开发说明，仅供开发者参考；它不是普通用户安装或调用本 Skill 的必经步骤。

<details>
<summary>展开上游开发说明</summary>


   * [支持平台](#支持平台)
   * [安装](#安装)
   * [命令行使用](#命令行使用)
   * [Docker](#docker)
   * [依赖模块](#依赖模块)

Golang短视频去水印, 视频目前支持22个平台, 图集目前支持4个平台, 欢迎各位Star。
> ps: 使用时, 请尽量使用app分享链接, 电脑网页版未做测试.

# 其他语言版本
- [Python版本](https://github.com/wujunwei928/parse-video-py)

---

# 支持平台
## 图集
| 平台  | 状态 | 
|-----|----|
| 抖音  | ✔  |
| 快手  | ✔  | 
| 小红书 | ✔  | 
| 皮皮虾 | ✔  | 
| 微博   | ✔  |

## 图集 LivePhoto
| 平台  | 状态 |
|-----|----|
| 小红书 | ✔  |

## 视频
| 平台       | 状态 |
|----------|----|
| 小红书      | ✔  |
| 皮皮虾      | ✔  |
| 抖音短视频    | ✔  |
| 火山短视频    | ✔  |
| 皮皮搞笑     | ✔  |
| 快手短视频    | ✔  |
| 微视短视频    | ✔  |
| 西瓜视频     | ✔  |
| 最右       | ✔  |
| 梨视频      | ✔  |
| 度小视(原全民) | ✔  |
| 逗拍       | ✔  |
| 微博       | ✔  |
| 绿洲       | ✔  |
| 全民K歌     | ✔  |
| 6间房      | ✔  |
| 美拍       | ✔  |
| 新片场      | ✔  |
| 好看视频     | ✔  |
| 虎牙       | ✔  |
| AcFun    | ✔  |
| 央视网     | ✔  |
| 哔哩哔哩     | ✔  |
| 腾讯视频     | ✔  |
| 搜狐视频     | ✔  |

# 安装
```go
// 根据分享链接解析
res, _ := parser.ParseVideoShareUrl("分享链接")
fmt.Printf("%#v", res)

// 根据视频id解析
res2, _ := parser.ParseVideoId(parser.SourceDouYin, "视频id")
fmt.Printf("%#v", res2)
```

# 命令行使用

编译安装后，可通过 `parse-video` 命令使用，开发阶段可用 `go run main.go` 代替。

## 子命令

### `serve` - 启动 HTTP 解析服务（默认命令）

```bash
# 默认监听 8080 端口
go run main.go

# 自定义端口
go run main.go serve --port 9090

# 开启 basic auth 认证
export PARSE_VIDEO_USERNAME=basic_auth_username
export PARSE_VIDEO_PASSWORD=basic_auth_password
go run main.go serve
```

> 不带子命令时默认执行 `serve`，`--port` / `--version` 等全局选项可直接使用。

### `parse` - 解析视频分享链接

```bash
# 解析单个链接
go run main.go parse "https://v.douyin.com/xxxxx"

# 也可直接传入包含链接的分享文案
go run main.go parse "7.87 Pjm:/ 复制打开抖音 https://v.douyin.com/xxxxx"

# 批量解析（传入多个链接）
go run main.go parse "链接1" "链接2" "链接3"

# 从文件读取链接（每行一个）
go run main.go parse --file links.txt

# 从标准输入读取
echo "https://v.douyin.com/xxxxx" | go run main.go parse -f -

# JSON 格式输出
go run main.go parse --format json "分享链接"

# 解析并下载媒体文件到当前目录
go run main.go parse --download "分享链接"

# 下载到指定目录
go run main.go parse -d -o ./downloads "分享链接"
```

### `id` - 根据视频 ID 解析

```bash
# 通过平台 + 视频 ID 解析
go run main.go id --source douyin "视频ID"

# JSON 格式输出
go run main.go id --source douyin --format json "视频ID"

# 解析并下载
go run main.go id --source douyin -d "视频ID"
```

> `--source` 为必填参数，可用值可通过解析失败时的错误提示查看。

### `version` - 查看版本

```bash
go run main.go version
```

## 全局选项

| 选项 | 说明 |
|------|------|
| `--port, -p` | 服务监听端口（默认 `8080`，serve 命令） |
| `--version` | 显示版本信息 |

## 解析命令通用选项（parse / id）

| 选项 | 说明 |
|------|------|
| `--format` | 输出格式：`text`（默认）、`json` |
| `--download, -d` | 下载解析到的媒体文件（视频、图集、封面、音乐） |
| `--output-dir, -o` | 下载文件保存目录（默认 `.`，即当前目录） |

## parse 独有选项

| 选项 | 说明 |
|------|------|
| `--file, -f` | 从文件读取链接（每行一个，`-` 代表 stdin） |


# Docker
获取 docker image
```bash
docker pull wujunwei928/parse-video
```

运行 docker 容器, 端口 8080
```bash
docker run -d -p 8080:8080 wujunwei928/parse-video
```

自定义端口运行
```bash
docker run -d -p 9090:9090 wujunwei928/parse-video -port 9090
```

运行docker容器，开启basic auth认证
```bash
docker run -d -p 8080:8080 -e PARSE_VIDEO_USERNAME=basic_auth_username -e PARSE_VIDEO_PASSWORD=basic_auth_password wujunwei928/parse-video
 ```

设置 HTTP 代理（所有解析请求通过代理发送）
```bash
# 无认证代理
docker run -d -p 8080:8080 -e PARSE_VIDEO_PROXY=http://proxy.example.com:端口 wujunwei928/parse-video

# 有认证代理
docker run -d -p 8080:8080 -e PARSE_VIDEO_PROXY=http://user:pass@proxy.example.com:端口 wujunwei928/parse-video
```

查看前端页面  
访问: http://127.0.0.1:8080/  

请求接口, 查看json返回
```bash
curl 'http://127.0.0.1:8080/video/share/url/parse?url=视频分享链接' | jq
```
返回格式
```json
{
  "author": {
    "uid": "uid",
    "name": "name",
    "avatar": "https://xxx"
  },
  "title": "记录美好生活#峡谷天花板",
  "video_url": "https://xxx",
  "music_url": "https://yyy",
  "cover_url": "https://zzz",
  "images": [],
  "image_live_photos": []
}
```
| 字段名                           | 说明                  | 
|-------------------------------|---------------------| 
| author.uid                    | 视频作者id              |
| author.name                   | 视频作者名称              |
| author.avatar                 | 视频作者头像              |
| title                         | 视频标题                |
| video_url                     | 视频无水印链接             |
| music_url                     | 视频音乐链接              |
| cover_url                     | 视频封面                |
| images.[index].url            | 图集图片地址              |
| images.[index].live_photo_url | 图集图片 livePhoto 视频地址 |
> 字段除了视频地址, 其他字段可能为空

# 依赖模块
| 模块                                                                       | 作用               |
|--------------------------------------------------------------------------|------------------|
| [github.com/gin-gonic/gin](https://github.com/gin-gonic/gin)             | web框架            |
| [github.com/go-resty/resty/v2](https://github.com/go-resty/resty/v2)     | HTTP 和 REST 客户端  |
| [github.com/tidwall/gjson](https://github.com/tidwall/gjson)             | 使用一行代码获取JSON的值   |
| [github.com/PuerkitoBio/goquery](https://github.com/PuerkitoBio/goquery) | 类jQuery语法解析html页面 |


```bash
go get github.com/gin-gonic/gin
go get github.com/go-resty/resty/v2
go get github.com/tidwall/gjson
go get github.com/PuerkitoBio/goquery
```

</details>
