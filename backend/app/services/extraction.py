import io
import ipaddress
import multiprocessing
import queue
import socket
from urllib.parse import urlsplit, urljoin, urlunsplit
import httpx
import trafilatura
from fastapi import HTTPException
from app.core.config import settings


def public_target(url: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.port not in {None, 80, 443}:
            raise ValueError()
        host = parsed.hostname.encode('idna').decode('ascii')
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
            raise ValueError()
        address = sorted(addresses)[0]
        address = f'[{address}]' if ':' in address else address
        pinned = urlunsplit((parsed.scheme, address + (f':{parsed.port}' if parsed.port else ''), parsed.path or '/', parsed.query, ''))
        return pinned, host
    except (ValueError, OSError, UnicodeError):
        raise HTTPException(422, 'Use a public HTTP(S) article URL on port 80 or 443. Private and internal addresses are blocked.')


def extract_url(url: str) -> dict:
    try:
        with httpx.Client(timeout=httpx.Timeout(12, connect=5), follow_redirects=False, trust_env=False) as client:
            for _ in range(4):
                pinned, host = public_target(url)
                # DNS is resolved and validated once per hop; the actual connection uses that IP.
                with client.stream('GET', pinned, headers={'Host': host, 'User-Agent': 'VeriFactAI/1.0 (academic article extraction)'}, extensions={'sni_hostname': host}) as response:
                    if response.is_redirect:
                        target = response.headers.get('location')
                        if not target:
                            raise HTTPException(422, 'The source returned an invalid redirect.')
                        url = urljoin(url, target)
                        continue
                    if response.status_code != 200:
                        raise HTTPException(422, 'This article could not be accessed. Paste text you have permission to use; access restrictions are respected.')
                    content_type = response.headers.get('content-type', '').lower()
                    if not any(t in content_type for t in ['text/html', 'text/plain', 'application/xhtml+xml']):
                        raise HTTPException(422, 'The URL must point to an HTML or plain-text article.')
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 2 * 1024 * 1024:
                            raise HTTPException(413, 'The article page exceeds the 2 MB extraction limit.')
                        chunks.append(chunk)
                    html = b''.join(chunks).decode('utf-8', errors='replace')
                    article = trafilatura.bare_extraction(html, include_comments=False, include_tables=False)
                    text = article.text if article else ''
                    if not text or len(text.split()) < 12:
                        raise HTTPException(422, 'No readable article was found. This page may require JavaScript or a subscription. Paste the article text instead.')
                    return {'headline': (article.title or '')[:300], 'text': text[:settings.max_text_chars], 'source_url': url}
        raise HTTPException(422, 'The source exceeded the redirect limit.')
    except httpx.HTTPError:
        raise HTTPException(422, 'The source timed out or could not be securely reached. Try pasting the article text.')


def _parse_pdf(data: bytes, output):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ValueError('Encrypted PDFs are not supported.')
        if len(reader.pages) > 50:
            raise ValueError('PDFs must contain at most 50 pages.')
        parts = []
        for page in reader.pages:
            parts.append((page.extract_text() or '')[:60000])
            if sum(map(len, parts)) > 60000:
                raise ValueError('The document exceeds 60,000 characters.')
        output.put({'text': '\n'.join(parts)})
    except Exception:
        output.put({'error': 'This PDF cannot be read. Use an unencrypted, text-based PDF with at most 50 pages and 60,000 characters.'})


def extract_file(name: str, content_type: str, data: bytes) -> dict:
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, 'Files must be 5 MB or smaller.')
    if name.lower().endswith('.txt') and content_type in {'text/plain', 'application/octet-stream'}:
        if b'\x00' in data:
            raise HTTPException(422, 'The file is not a valid UTF-8 text document.')
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise HTTPException(422, 'Save this document as UTF-8 plain text and try again.')
    elif name.lower().endswith('.pdf') and content_type == 'application/pdf' and data.startswith(b'%PDF-'):
        context = multiprocessing.get_context('spawn')
        output = context.Queue()
        process = context.Process(target=_parse_pdf, args=(data, output), daemon=True)
        process.start()
        try:
            result = output.get(timeout=15)
        except queue.Empty:
            raise HTTPException(422, 'PDF extraction timed out. Try a smaller text-based document.')
        finally:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)
            output.close()
        if 'error' in result:
            raise HTTPException(422, result['error'])
        text = result['text']
    else:
        raise HTTPException(415, 'Upload a .txt or .pdf file with the matching document type.')
    if len(text) > settings.max_text_chars:
        raise HTTPException(413, 'Documents must contain at most 60,000 characters.')
    if len(text.split()) < 12:
        raise HTTPException(422, 'Not enough readable text. Scanned PDFs need OCR before upload.')
    return {'headline': name[:300], 'text': text, 'source_url': None}
