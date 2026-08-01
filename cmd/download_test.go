package cmd

import (
	"strings"
	"testing"

	"github.com/wujunwei928/parse-video/parser"
)

func TestDownloadMediaRejectsResultWithoutMedia(t *testing.T) {
	info := &parser.VideoParseInfo{Title: "只有元数据"}

	err := downloadMedia(info, t.TempDir())
	if err == nil {
		t.Fatal("没有任何媒体地址时，下载命令必须返回错误")
	}
	if !strings.Contains(err.Error(), "无可下载的媒体文件") {
		t.Fatalf("错误信息应说明没有媒体文件，实际: %v", err)
	}
}

func TestRefererForMediaURLUsesPublicWeiboOrigin(t *testing.T) {
	cases := []string{
		"https://f.video.weibocdn.com/path/video.mp4",
		"https://wx1.sinaimg.cn/large/cover.jpg",
	}
	for _, mediaURL := range cases {
		if got := refererForMediaURL(mediaURL); got != "https://weibo.com/" {
			t.Fatalf("微博 CDN 应使用公开微博来源页，url=%s referer=%q", mediaURL, got)
		}
	}
	if got := refererForMediaURL("https://example.com/video.mp4"); got != "" {
		t.Fatalf("其他平台不应被注入微博 Referer，实际: %q", got)
	}
}
