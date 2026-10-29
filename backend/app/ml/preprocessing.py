import html
import re
import unicodedata
from nltk.tokenize import PunktSentenceTokenizer


def clean_text(text: str) -> str:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(
        r"\s+", " ", unicodedata.normalize("NFKC", html.unescape(text))
    ).strip()


def tokens(text: str) -> list[str]:
    return re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text, flags=re.UNICODE)


def sentences(text: str) -> list[tuple[str, int, int]]:
    return [
        (text[a:b], a, b)
        for a, b in PunktSentenceTokenizer().span_tokenize(text)
        if text[a:b].strip()
    ]
