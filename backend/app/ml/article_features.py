"""Shared, source-scrubbed article features used at training and inference."""

import re
from app.ml.preprocessing import clean_text


def article_text(text: str) -> str:
    text = clean_text(text).lower()
    # Remove easy publisher identifiers and URL/byline artifacts in BOTH classes.
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"^.{0,90}?\((?:reuters|ap|afp)\)\s*[-–—:]?", " ", text)
    text = re.sub(
        r"\b(?:reuters|associated press|getty images|image copyright|read more|click here|subscribe now)\b",
        " ",
        text,
    )
    text = re.sub(r"\[(?:video|photos?|audio)\]", " ", text)
    text = re.sub(
        r"\b(?:reporting by|editing by|additional reporting by)\b[^\n.]{0,250}",
        " ",
        text,
    )
    return " ".join(text.split()[:2500])
