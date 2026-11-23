import pytest

from reelkit.errors import classify_ytdlp_error
from reelkit.router import route
from reelkit.errors import ReelError


@pytest.mark.parametrize("url,platform,vid,clean", [
    ("https://www.instagram.com/reel/DAbc123xyz/?igsh=MWQ1ZGUxMzBkMA==", "instagram", "DAbc123xyz",
     "https://instagram.com/reel/DAbc123xyz/"),
    ("instagram.com/reels/DAbc123xyz", "instagram", "DAbc123xyz", "https://instagram.com/reel/DAbc123xyz"),
    ("https://www.instagram.com/someuser/reel/DAbc123xyz/", "instagram", "DAbc123xyz", None),
    ("https://youtube.com/shorts/aBcDeFgHiJk?si=xyz123", "youtube", "aBcDeFgHiJk", "https://youtube.com/shorts/aBcDeFgHiJk"),
    ("https://m.youtube.com/watch?v=aBcDeFgHiJk&feature=share", "youtube", "aBcDeFgHiJk",
     "https://youtube.com/watch?v=aBcDeFgHiJk"),
    ("https://youtu.be/aBcDeFgHiJk", "youtube", "aBcDeFgHiJk", None),
    ("https://www.tiktok.com/@creador.mx/video/7312345678901234567?is_from_webapp=1&sender_device=pc",
     "tiktok", "7312345678901234567", "https://tiktok.com/@creador.mx/video/7312345678901234567"),
    ("https://vm.tiktok.com/ZMabc123/", "tiktok", "ZMabc123", None),
    ("https://twitter.com/user/status/1790000000000000000?s=20", "x", "1790000000000000000",
     "https://x.com/user/status/1790000000000000000"),
    ("https://www.facebook.com/reel/1234567890123456?mibextid=abc", "facebook", "1234567890123456",
     "https://facebook.com/reel/1234567890123456"),
    ("https://fb.watch/abcDEF12/", "facebook", "abcDEF12", None),
    ("https://www.facebook.com/share/r/1AbCdEf/", "facebook", "1AbCdEf", None),
])
def test_route(url, platform, vid, clean):
    src = route(url)
    assert src.platform == platform
    assert src.video_id == vid
    if clean:
        assert src.url == clean


def test_route_unsupported():
    with pytest.raises(ReelError) as e:
        route("https://example.com/video/1")
    assert e.value.code == "UNSUPPORTED_URL"


@pytest.mark.parametrize("stderr,platform,cookies,code", [
    ("ERROR: [instagram] DAbc: Instagram sent an empty media response. Check if this post is accessible in your "
     "browser without being logged-in", "instagram", False, "IG_LOGIN_REQUIRED"),
    ("ERROR: [Instagram] DAbc: Requested content is not available, rate-limit reached or login required. "
     "Use --cookies", "instagram", False, "IG_LOGIN_REQUIRED"),
    ("ERROR: [Instagram] DAbc: Unable to download JSON metadata: HTTP Error 404: Not Found", "instagram", True,
     "IG_LOGIN_REQUIRED"),
    ("ERROR: [Instagram] DAbc: Failed to parse JSON (caused by JSONDecodeError(\"Expecting value in '': "
     "line 1 column 1 (char 0)\"))", "instagram", True, "IG_HTML_RESPONSE"),
    ("ERROR: [youtube] abc: Private video. Sign in if you've been granted access to this video", "youtube", False,
     "PRIVATE_OR_DELETED"),
    ("ERROR: [TikTok] 7312: Video not available, status code 10204", "tiktok", False, "PRIVATE_OR_DELETED"),
    ("ERROR: [youtube] abc: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies",
     "youtube", False, "COOKIES_REQUIRED"),
    ("ERROR: [TikTok] 7312: Unable to extract universal data for rehydration; please report this issue on "
     "https://github.com/yt-dlp/yt-dlp/issues", "tiktok", False, "EXTRACTOR_BROKEN"),
    ("ERROR: Unable to download webpage: <urlopen error [Errno 8] nodename nor servname provided, or not known>",
     "instagram", False, "NETWORK_BLOCKED"),
    ("ERROR: Unable to download webpage: <urlopen error Tunnel connection failed: 403 Forbidden>", "youtube",
     False, "NETWORK_BLOCKED"),
    ("ERROR: something new and weird", "x", False, "DOWNLOAD_FAILED"),
])
def test_classify(stderr, platform, cookies, code):
    err = classify_ytdlp_error(stderr, platform, cookies)
    assert err.code == code
    assert err.mensaje and err.accion
