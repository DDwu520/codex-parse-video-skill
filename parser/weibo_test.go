package parser

import (
	"testing"

	"github.com/tidwall/gjson"
)

func TestWeiBo_parseMobileApiDataExtractsVideo(t *testing.T) {
	data := gjson.Parse(`{
		"text":"<span>公开微博视频</span>",
		"user":{
			"id":"2803301701",
			"screen_name":"人民日报",
			"avatar_large":"https://example.com/avatar.jpg"
		},
		"page_info":{
			"type":"video",
			"object_type":11,
			"page_pic":{"url":"https://example.com/cover.jpg"},
			"media_info":{
				"stream_url":"https://example.com/video-sd.mp4",
				"stream_url_hd":"https://example.com/video-hd.mp4"
			}
		}
	}`)

	got, err := (weiBo{}).parseMobileApiData(data)
	if err != nil {
		t.Fatalf("解析公开微博响应失败: %v", err)
	}
	if got.VideoUrl != "https://example.com/video-hd.mp4" {
		t.Fatalf("应优先使用高清视频地址，实际: %q", got.VideoUrl)
	}
	if got.CoverUrl != "https://example.com/cover.jpg" {
		t.Fatalf("封面地址不正确，实际: %q", got.CoverUrl)
	}
	if got.Author.Uid != "2803301701" || got.Author.Name != "人民日报" {
		t.Fatalf("作者信息不正确，实际: %#v", got.Author)
	}
}

func TestWeiBo_parseMobileApiDataPreservesImageAlbum(t *testing.T) {
	data := gjson.Parse(`{
		"text":"公开微博图集",
		"user":{"id":"123","screen_name":"测试作者"},
		"pics":[
			{"large":{"url":"https://example.com/one.jpg"}},
			{"original":{"url":"https://example.com/two.jpg"}}
		]
	}`)

	got, err := (weiBo{}).parseMobileApiData(data)
	if err != nil {
		t.Fatalf("解析公开微博图集失败: %v", err)
	}
	if got.VideoUrl != "" {
		t.Fatalf("图集不应伪造视频地址，实际: %q", got.VideoUrl)
	}
	if len(got.Images) != 2 {
		t.Fatalf("应保留两张原图，实际: %#v", got.Images)
	}
}

func TestWeiBo_parseShareUrlRejectsUnsupportedURL(t *testing.T) {
	if _, err := (weiBo{}).parseShareUrl("https://example.com/invalid"); err == nil {
		t.Fatal("不支持的微博 URL 格式必须返回错误")
	}
}

func TestWeiBo_cleanText(t *testing.T) {
	w := weiBo{}

	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "Text with HTML tags",
			input:    "<span class=\"text\">Hello World</span>",
			expected: "Hello World",
		},
		{
			name:     "Text with multiple tags",
			input:    "<div><p>Hello <strong>World</strong></p></div>",
			expected: "Hello World",
		},
		{
			name:     "Plain text",
			input:    "Hello World",
			expected: "Hello World",
		},
		{
			name:     "Text with whitespace",
			input:    "  Hello World  ",
			expected: "Hello World",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := w.cleanText(tt.input)
			if got != tt.expected {
				t.Errorf("weiBo.cleanText() = %v, want %v", got, tt.expected)
			}
		})
	}
}
