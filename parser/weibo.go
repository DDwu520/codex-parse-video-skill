package parser

import (
	"errors"
	"fmt"
	"net/url"
	"regexp"
	"strings"

	"github.com/tidwall/gjson"
)

type weiBo struct {
}

func (w weiBo) parseShareUrl(shareUrl string) (*VideoParseInfo, error) {
	urlInfo, err := url.Parse(shareUrl)
	if err != nil {
		return nil, errors.New("parse share url fail")
	}

	// Handle video URLs
	if strings.Contains(shareUrl, "show?fid=") {
		if len(urlInfo.Query()["fid"]) <= 0 {
			return nil, errors.New("can not parse video id from share url")
		}
		videoId := urlInfo.Query()["fid"][0]
		return w.parseVideoID(videoId)
	} else if strings.Contains(shareUrl, "/tv/show/") {
		videoId := strings.ReplaceAll(urlInfo.Path, "/tv/show/", "")
		return w.parseVideoID(videoId)
	} else {
		// Handle regular post URLs (potential image albums)
		// Extract post ID from URLs like https://weibo.com/2543858012/Q9pcJ4S21
		pathParts := strings.Split(strings.Trim(urlInfo.Path, "/"), "/")
		if len(pathParts) >= 2 {
			postId := pathParts[len(pathParts)-1]
			return w.parsePostUrl(postId, shareUrl)
		}
	}

	return nil, errors.New("unsupported weibo url format")
}

func (w weiBo) parseVideoID(videoId string) (*VideoParseInfo, error) {
	reqUrl := fmt.Sprintf("https://h5.video.weibo.com/api/component?page=/show/%s", videoId)
	client := newClient()
	videoRes, err := client.R().
		SetHeader(HttpHeaderReferer, "https://h5.video.weibo.com/show/"+videoId).
		SetHeader(HttpHeaderContentType, "application/x-www-form-urlencoded").
		SetHeader(HttpHeaderUserAgent, DefaultUserAgent).
		SetBody([]byte(`data={"Component_Play_Playinfo":{"oid":"` + videoId + `"}}`)).
		Post(reqUrl)
	if err != nil {
		return nil, err
	}
	data := gjson.GetBytes(videoRes.Body(), "data.Component_Play_Playinfo")
	var videoUrl string
	data.Get("urls").ForEach(func(key, value gjson.Result) bool {
		if len(videoUrl) == 0 {
			// 第一条码率最高
			videoUrl = "https:" + value.String()
		}
		return true
	})
	parseInfo := &VideoParseInfo{
		Title:    data.Get("title").String(),
		VideoUrl: videoUrl,
		CoverUrl: "https:" + data.Get("cover_image").String(),
	}
	parseInfo.Author.Name = data.Get("author").String()
	parseInfo.Author.Avatar = "https:" + data.Get("avatar").String()

	return parseInfo, nil
}

func (w weiBo) parsePostUrl(postId string, originalUrl string) (*VideoParseInfo, error) {
	// Try mobile API first
	reqUrl := fmt.Sprintf("https://m.weibo.cn/statuses/show?id=%s", postId)
	client := newClient()

	res, err := client.R().
		SetHeader(HttpHeaderUserAgent, "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1").
		SetHeader(HttpHeaderReferer, "https://m.weibo.cn/").
		SetHeader(HttpHeaderContentType, "application/json;charset=UTF-8").
		SetHeader("X-Requested-With", "XMLHttpRequest").
		Get(reqUrl)
	if err == nil {
		data := gjson.GetBytes(res.Body(), "data")
		if data.Exists() {
			return w.parseMobileApiData(data)
		}
	}

	// Fallback to desktop page parsing using the original URL
	res, err = client.R().
		SetHeader(HttpHeaderUserAgent, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36").
		Get(originalUrl)
	if err != nil {
		return nil, err
	}

	return w.parseHtmlPage(res.Body())
}

func (w weiBo) parseMobileApiData(data gjson.Result) (*VideoParseInfo, error) {
	title := data.Get("text").String()
	authorID := data.Get("user.id").String()
	authorName := data.Get("user.screen_name").String()
	authorAvatar := data.Get("user.avatar_large").String()
	videoURL := w.videoURLFromStatus(data)
	coverURL := data.Get("page_info.page_pic.url").String()
	if coverURL == "" {
		coverURL = data.Get("retweeted_status.page_info.page_pic.url").String()
	}

	// Get images
	images := make([]ImgInfo, 0)
	picsData := data.Get("pics")
	if picsData.Exists() {
		picsArray := picsData.Array()
		for _, pic := range picsArray {
			// Get the largest image URL available
			largePicUrl := pic.Get("large.url").String()
			if largePicUrl == "" {
				largePicUrl = pic.Get("original.url").String()
			}
			if largePicUrl == "" {
				largePicUrl = pic.Get("bmiddle.url").String()
			}
			if largePicUrl == "" {
				largePicUrl = pic.Get("url").String()
			}

			if largePicUrl != "" {
				images = append(images, ImgInfo{
					Url: largePicUrl,
				})
			}
		}
	}

	parseInfo := &VideoParseInfo{
		Title:    w.cleanText(title),
		VideoUrl: videoURL,
		CoverUrl: coverURL,
		Images:   images,
	}
	parseInfo.Author.Uid = authorID
	parseInfo.Author.Name = authorName
	parseInfo.Author.Avatar = authorAvatar

	return parseInfo, nil
}

func (w weiBo) videoURLFromStatus(data gjson.Result) string {
	if videoURL := w.videoURLFromMediaInfo(data.Get("page_info.media_info")); videoURL != "" {
		return videoURL
	}

	var mixedVideoURL string
	data.Get("mix_media_info.items").ForEach(func(_, item gjson.Result) bool {
		mixedVideoURL = w.videoURLFromMediaInfo(item.Get("data.media_info"))
		if mixedVideoURL == "" {
			mixedVideoURL = w.videoURLFromMediaInfo(item.Get("data.page_info.media_info"))
		}
		return mixedVideoURL == ""
	})
	if mixedVideoURL != "" {
		return mixedVideoURL
	}

	return w.videoURLFromMediaInfo(data.Get("retweeted_status.page_info.media_info"))
}

func (w weiBo) videoURLFromMediaInfo(mediaInfo gjson.Result) string {
	for _, field := range []string{"stream_url_hd", "stream_url", "mp4_hd_url", "mp4_sd_url"} {
		if videoURL := mediaInfo.Get(field).String(); videoURL != "" {
			return videoURL
		}
	}
	return ""
}

func (w weiBo) parseHtmlPage(htmlBody []byte) (*VideoParseInfo, error) {
	// Try to extract data from $render_data script
	re := regexp.MustCompile(`\$render_data\s*=\s*(.*?)\[0\]`)
	findRes := re.FindSubmatch(htmlBody)
	if len(findRes) < 2 {
		return nil, errors.New("parse weibo html page fail")
	}

	jsonStr := string(findRes[1]) + "[0]"
	data := gjson.Parse(jsonStr)

	return w.parseMobileApiData(data.Get("status"))
}

// cleanText removes HTML tags from text
func (w weiBo) cleanText(text string) string {
	// Remove HTML tags
	re := regexp.MustCompile(`<[^>]*>`)
	cleaned := re.ReplaceAllString(text, "")
	return strings.TrimSpace(cleaned)
}
