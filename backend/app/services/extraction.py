import io
import json
import re
import html as html_lib
from lxml import html as lxml_html
from app.ml.preprocessing import clean_text
import ipaddress
import multiprocessing
import queue
import socket
import time
from urllib.parse import urlsplit, urljoin, urlunsplit
import httpx
import trafilatura
from fastapi import HTTPException
from app.core.config import settings


def public_target(url: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 80, 443}
        ):
            raise ValueError()
        host = parsed.hostname.encode("idna").decode("ascii")
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                host,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
        if not addresses or any(
            not ipaddress.ip_address(ip).is_global for ip in addresses
        ):
            raise ValueError()
        address = sorted(addresses)[0]
        address = f"[{address}]" if ":" in address else address
        pinned = urlunsplit(
            (
                parsed.scheme,
                address + (f":{parsed.port}" if parsed.port else ""),
                parsed.path or "/",
                parsed.query,
                "",
            )
        )
        return pinned, host
    except (ValueError, OSError, UnicodeError):
        raise HTTPException(
            422,
            "Use a public HTTP(S) article URL on port 80 or 443. Private and internal addresses are blocked.",
        )


def _fetch_public(client, url: str, deadline: float, json_allowed=False):
    """Every redirect is independently resolved and pinned; never follow private targets."""
    for _ in range(6):
        if time.monotonic() >= deadline:
            raise HTTPException(
                422,
                "Article extraction timed out. Try again or paste the article text.",
            )
        pinned, host = public_target(url)
        with client.stream(
            "GET",
            pinned,
            headers={
                "Host": host,
                "User-Agent": "VeriFactAI/2.0 (public article reader)",
                "Accept": "application/json,text/html,text/plain;q=0.9",
            },
            extensions={"sni_hostname": host},
        ) as response:
            if response.is_redirect:
                target = response.headers.get("location")
                if not target:
                    raise HTTPException(422, "The source returned an invalid redirect.")
                url = urljoin(url, target)
                continue
            if response.status_code != 200:
                detail = {
                    401: "This publisher requires sign-in. Paste article text you can access.",
                    403: "This publisher blocks automated readers. Open the original article and paste its text.",
                    404: "This article was not found. Check the URL or use the original publisher link.",
                    410: "This article is no longer available at this URL.",
                    429: "This publisher is rate-limiting requests. Wait briefly or paste the article text.",
                }.get(
                    response.status_code,
                    f"The publisher returned HTTP {response.status_code}. Try the original publisher link or paste text.",
                )
                raise HTTPException(422, detail)
            content_type = response.headers.get("content-type", "").lower()
            allowed = ["text/html", "text/plain", "application/xhtml+xml"]
            if json_allowed:
                allowed.append("application/json")
            if not any(t in content_type for t in allowed):
                raise HTTPException(
                    422, "The URL must point to a public HTML or plain-text article."
                )
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                if time.monotonic() >= deadline:
                    raise HTTPException(
                        422,
                        "Article extraction exceeded its time limit. Paste the text instead.",
                    )
                size += len(chunk)
                if size > 2 * 1024 * 1024:
                    raise HTTPException(
                        413, "The article page exceeds the 2 MB extraction limit."
                    )
                chunks.append(chunk)
            encoding = re.search(r"charset=([\w-]+)", content_type)
            try:
                body = b"".join(chunks).decode(
                    encoding.group(1) if encoding else "utf-8", errors="replace"
                )
            except LookupError:
                body = b"".join(chunks).decode("utf-8", errors="replace")
            return body, content_type, url
    raise HTTPException(422, "The source exceeded the redirect limit.")


def _structured_article(markup: str) -> tuple[str, str]:
    """Read articleBody only from public NewsArticle/Article JSON-LD, never execute scripts."""
    try:
        tree = lxml_html.fromstring(markup)
        scripts = tree.xpath('//script[@type="application/ld+json"]/text()')
    except (ValueError, TypeError):
        return "", ""

    def visit(value, depth=0):
        if depth > 12:
            return None
        if isinstance(value, list):
            for child in value:
                if found := visit(child, depth + 1):
                    return found
        if isinstance(value, dict):
            kind = value.get("@type", [])
            kind = [kind] if isinstance(kind, str) else kind
            if (
                isinstance(kind, list)
                and any(
                    k in {"Article", "NewsArticle", "ReportageNewsArticle"}
                    for k in kind
                    if isinstance(k, str)
                )
                and isinstance(value.get("articleBody"), str)
            ):
                # A publisher's explicit paywall flag is respected.
                if value.get("isAccessibleForFree") in (False, "false", "False"):
                    return None
                return clean_text(value["articleBody"]), str(value.get("headline", ""))
            for key in ("@graph", "mainEntity", "itemListElement"):
                if found := visit(value.get(key), depth + 1):
                    return found
        return None

    for script in scripts[:20]:
        try:
            if result := visit(json.loads(script)):
                return result
        except (ValueError, TypeError):
            continue
    return "", ""


def _msn_article(client, url: str, deadline: float):
    parsed = urlsplit(url)
    if parsed.hostname not in {"www.msn.com", "msn.com"}:
        return None
    match = re.search(r"^/([a-z]{2}-[a-z]{2})/.*/ar-([A-Za-z0-9]+)(?:/)?$", parsed.path)
    if not match:
        return None
    market, article_id = match.groups()
    # Public CDN feed used by MSN's client. No cookies, credentials, or paid content.
    feed = f"https://assets.msn.com/content/view/v2/Detail/{market}/{article_id}"
    body, content_type, _ = _fetch_public(client, feed, deadline, json_allowed=True)
    if "application/json" not in content_type:
        return None
    try:
        item = json.loads(body)
    except ValueError:
        return None
    if (
        not isinstance(item, dict)
        or item.get("isPaywall")
        or item.get("isPremium")
        or item.get("renderingRestriction", 0) != 0
        or item.get("subscriptionProductType", 0) != 0
    ):
        return None
    content = item.get("body")
    if not isinstance(content, str):
        return None
    # Preserve paragraph boundaries instead of returning an opaque HTML string.
    content = re.sub(r"</(?:p|div|h[1-6]|li)>|<br\s*/?>", "\n", content, flags=re.I)
    text = clean_text(content)
    return {
        "headline": str(item.get("title", ""))[:300],
        "text": text,
        "source_url": urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")),
    }


def extract_url(url: str) -> dict:
    url = html_lib.unescape(url.strip())
    deadline = time.monotonic() + 28
    try:
        with httpx.Client(
            timeout=httpx.Timeout(10, connect=5),
            follow_redirects=False,
            trust_env=False,
        ) as client:
            markup, content_type, final_url = _fetch_public(client, url, deadline)
            if "text/plain" in content_type:
                result = {
                    "headline": "",
                    "text": clean_text(markup),
                    "source_url": final_url,
                }
            else:
                # MSN returns an app shell even for readable, public news articles.
                result = _msn_article(client, final_url, deadline)
                if result is None:
                    article = trafilatura.bare_extraction(
                        markup, include_comments=False, include_tables=False
                    )
                    text = article.text if article else ""
                    title = article.title if article else ""
                    if not text or len(text.split()) < 12:
                        text, title = _structured_article(markup)
                    result = {
                        "headline": (title or "")[:300],
                        "text": text or "",
                        "source_url": final_url,
                    }
            if len(result["text"].split()) < 12:
                raise HTTPException(
                    422,
                    "No article text was available. This page may require JavaScript, sign-in, or a subscription. Use the original publisher link or paste the text below.",
                )
            if len(result["text"]) > settings.max_text_chars:
                raise HTTPException(
                    413,
                    "The article exceeds 60,000 characters. Paste a shorter excerpt.",
                )
            return result
    except httpx.TimeoutException:
        raise HTTPException(
            422,
            "The publisher did not respond in time. Retry or paste the article text.",
        )
    except httpx.HTTPError:
        raise HTTPException(
            422,
            "The publisher could not be securely reached. Try the original publisher link or paste the article text.",
        )


def _parse_pdf(data: bytes, output):
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")
        if len(reader.pages) > 50:
            raise ValueError("PDFs must contain at most 50 pages.")
        parts = []
        for page in reader.pages:
            parts.append((page.extract_text() or "")[:60000])
            if sum(map(len, parts)) > 60000:
                raise ValueError("The document exceeds 60,000 characters.")
        output.put({"text": "\n".join(parts)})
    except Exception:
        output.put(
            {
                "error": "This PDF cannot be read. Use an unencrypted, text-based PDF with at most 50 pages and 60,000 characters."
            }
        )


def extract_file(name: str, content_type: str, data: bytes) -> dict:
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "Files must be 5 MB or smaller.")
    if name.lower().endswith(".txt") and content_type in {
        "text/plain",
        "application/octet-stream",
    }:
        if b"\x00" in data:
            raise HTTPException(422, "The file is not a valid UTF-8 text document.")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                422, "Save this document as UTF-8 plain text and try again."
            )
    elif (
        name.lower().endswith(".pdf")
        and content_type == "application/pdf"
        and data.startswith(b"%PDF-")
    ):
        context = multiprocessing.get_context("spawn")
        output = context.Queue()
        process = context.Process(target=_parse_pdf, args=(data, output), daemon=True)
        process.start()
        try:
            result = output.get(timeout=15)
        except queue.Empty:
            raise HTTPException(
                422, "PDF extraction timed out. Try a smaller text-based document."
            )
        finally:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)
            output.close()
        if "error" in result:
            raise HTTPException(422, result["error"])
        text = result["text"]
    else:
        raise HTTPException(
            415, "Upload a .txt or .pdf file with the matching document type."
        )
    if len(text) > settings.max_text_chars:
        raise HTTPException(413, "Documents must contain at most 60,000 characters.")
    if len(text.split()) < 12:
        raise HTTPException(
            422, "Not enough readable text. Scanned PDFs need OCR before upload."
        )
    return {"headline": name[:300], "text": text, "source_url": None}
