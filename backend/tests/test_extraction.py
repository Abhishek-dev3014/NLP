from unittest.mock import patch
import httpx
import pytest
from fastapi import HTTPException
from app.services.extraction import public_target, extract_url
from app.services.evidence import retrieve_evidence
from app.core.config import settings


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/test",
        "http://[::1]/test",
        "http://169.254.169.254/latest",
        "http://10.0.0.1/a",
        "http://localhost/a",
        "https://example.com:8080/a",
        "https://user:pass@example.com/a",
    ],
)
def test_ssrf_rejects_internal_addresses(url):
    with pytest.raises(HTTPException):
        public_target(url)


def test_mixed_dns_and_pinning():
    with patch(
        "socket.getaddrinfo",
        return_value=[
            (2, 1, 6, "", ("93.184.216.34", 443)),
            (2, 1, 6, "", ("127.0.0.1", 443)),
        ],
    ):
        with pytest.raises(HTTPException):
            public_target("https://public.example/story")
    with patch(
        "socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]
    ):
        pinned, host = public_target("https://public.example/story?x=1")
        assert pinned == "https://93.184.216.34/story?x=1" and host == "public.example"


def test_redirect_to_private_host_is_rejected():
    class Response:
        is_redirect = True
        headers = {"location": "http://127.0.0.1/private"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            return Response()

    def addresses(host, *args, **kwargs):
        return [
            (
                2,
                1,
                6,
                "",
                ("127.0.0.1" if host == "127.0.0.1" else "93.184.216.34", 443),
            )
        ]

    with (
        patch("socket.getaddrinfo", side_effect=addresses),
        patch("app.services.extraction.httpx.Client", Client),
    ):
        with pytest.raises(HTTPException):
            extract_url("https://public.example/story")


def test_optional_evidence_failure_is_graceful():
    with (
        patch.object(settings, "evidence_enabled", True),
        patch.object(settings, "fact_check_api_key", "test-key"),
        patch(
            "app.services.evidence.httpx.get", side_effect=httpx.ConnectError("offline")
        ),
    ):
        assert retrieve_evidence("claim", True)["status"] == "unavailable"
        assert retrieve_evidence("claim", False)["status"] == "disabled"


def test_valid_url_extraction_uses_pinned_ip():
    article = "The federal government released its proposed budget on Tuesday. The document outlines education spending and national defense spending for the next fiscal year. Researchers will examine the original figures before comparing the totals."

    class Response:
        is_redirect = False
        status_code = 200
        headers = {"content-type": "text/html"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self):
            yield f"<html><head><title>Budget report</title></head><body><article><h1>Budget report</h1><p>{article}</p></article></body></html>".encode()

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url, **kwargs):
            assert url.startswith("https://93.184.216.34/")
            assert kwargs["headers"]["Host"] == "public.example"
            assert kwargs["extensions"]["sni_hostname"] == "public.example"
            return Response()

    with (
        patch(
            "socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]
        ),
        patch("app.services.extraction.httpx.Client", Client),
    ):
        result = extract_url("https://public.example/article")
        assert (
            article in result["text"]
            and result["source_url"] == "https://public.example/article"
        )


def test_msn_public_feed_extraction_and_tracking_removal():
    import json

    text = "The chief minister is likely to meet party leaders in New Delhi next week to discuss public policy."
    requests = []

    def handler(request):
        requests.append(request)
        if request.headers["host"] == "www.msn.com":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text='<html><title>MSN</title><body><div id="app"></div></body></html>',
            )
        assert request.headers["host"] == "assets.msn.com"
        assert request.url.path == "/content/view/v2/Detail/en-in/AA123abc"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            text=json.dumps(
                {
                    "title": "Scheduled meeting",
                    "body": f"<p>{text}</p>",
                    "renderingRestriction": 0,
                    "subscriptionProductType": 0,
                }
            ),
        )

    real_client = httpx.Client
    with (
        patch(
            "socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]
        ),
        patch(
            "app.services.extraction.httpx.Client",
            side_effect=lambda **kwargs: real_client(
                transport=httpx.MockTransport(handler), **kwargs
            ),
        ),
    ):
        result = extract_url(
            "https://www.msn.com/en-in/news/other/story/ar-AA123abc?ocid=tracking"
        )
    assert result["text"] == text and result["headline"] == "Scheduled meeting"
    assert "?" not in result["source_url"]
    assert len(requests) == 2 and all(
        str(r.url.host) == "93.184.216.34" for r in requests
    )


def test_json_ld_fallback_and_paywall_flag():
    import json
    from app.services.extraction import _structured_article

    data = {
        "@type": "NewsArticle",
        "headline": "A public story",
        "articleBody": "The public library has announced a new collection of books for the local community this week.",
    }
    markup = (
        lambda d: '<script type="application/ld+json">' + json.dumps(d) + "</script>"
    )
    assert _structured_article(markup(data))[0] == data["articleBody"]
    assert _structured_article(markup({**data, "isAccessibleForFree": False})) == (
        "",
        "",
    )


def test_plain_text_url_and_specific_access_error():
    article = "The local council has published a detailed report about schools and public transport for the coming year."
    status = 200

    def handler(request):
        return httpx.Response(
            status, headers={"content-type": "text/plain; charset=utf-8"}, text=article
        )

    real_client = httpx.Client
    with (
        patch(
            "socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]
        ),
        patch(
            "app.services.extraction.httpx.Client",
            side_effect=lambda **kwargs: real_client(
                transport=httpx.MockTransport(handler), **kwargs
            ),
        ),
    ):
        assert extract_url("https://public.example/article.txt")["text"] == article
        status = 403
        with pytest.raises(HTTPException, match="blocks automated readers"):
            extract_url("https://public.example/article.txt")
