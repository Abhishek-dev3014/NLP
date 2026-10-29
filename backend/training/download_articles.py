"""Download the original author-published article corpus with checksum verification."""

import hashlib
import json
import httpx
from app.core.config import ROOT

URL = "https://zenodo.org/api/records/4561253/files/WELFake_Dataset.csv/content"
MD5 = "73c9675a4b3d09f86a6933d0b8d7d908"


def main():
    directory = ROOT.parent / "data/raw/articles"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "WELFake_Dataset.csv"
    if path.exists() and hashlib.md5(path.read_bytes()).hexdigest() == MD5:
        print("Original dataset is present and checksum verified.")
        return
    temporary = path.with_suffix(".download")
    digest = hashlib.md5()
    try:
        with httpx.stream("GET", URL, timeout=60, follow_redirects=True) as response:
            response.raise_for_status()
            with temporary.open("wb") as output:
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > 260_000_000:
                        raise ValueError("Unexpected dataset size")
                    digest.update(chunk)
                    output.write(chunk)
        if digest.hexdigest() != MD5:
            raise ValueError("Original dataset checksum does not match")
        temporary.replace(path)
        (directory / "download-manifest.json").write_text(
            json.dumps(
                {
                    "url": URL,
                    "md5": MD5,
                    "bytes": path.stat().st_size,
                    "attribution": "Verma, Agrawal and Prodan, WELFake (2021), doi:10.5281/zenodo.4561253",
                    "license": "CC BY 4.0 per original record; underlying article rights may differ.",
                },
                indent=2,
            )
        )
        print("Downloaded and verified", path)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
