"""Local feature encoders. Neural weights are never fetched at inference time."""

from functools import lru_cache
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from app.core.config import ROOT
from app.ml.preprocessing import clean_text

ENCODER_PATH = ROOT / "artifacts/encoders/all-MiniLM-L6-v2"


def normalize_for_vectorizer(text):
    # A custom sklearn preprocessor replaces lowercase=True, so lowercase explicitly.
    return clean_text(text).lower()


@lru_cache(maxsize=1)
def sentence_encoder():
    from sentence_transformers import SentenceTransformer
    import torch

    torch.set_num_threads(2)
    if not ENCODER_PATH.exists():
        raise FileNotFoundError(
            "Local sentence encoder missing. Run training.download_models."
        )
    return SentenceTransformer(str(ENCODER_PATH), device="cpu", local_files_only=True)


def embed(texts):
    return (
        sentence_encoder()
        .encode(
            list(texts),
            batch_size=64,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        .astype(np.float32)
    )


class FeatureEncoder:
    def __init__(self, semantic_weight=0.0, char_weight=0.0):
        self.semantic_weight = semantic_weight
        self.char_weight = char_weight
        self.word = TfidfVectorizer(
            preprocessor=normalize_for_vectorizer,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.98,
            max_features=40000,
            sublinear_tf=True,
            dtype=np.float32,
        )
        self.char = (
            TfidfVectorizer(
                preprocessor=normalize_for_vectorizer,
                analyzer="char_wb",
                ngram_range=(3, 5),
                min_df=3,
                max_features=35000,
                sublinear_tf=True,
                dtype=np.float32,
            )
            if char_weight
            else None
        )

    def fit_transform(self, texts, embeddings=None):
        matrices = [self.word.fit_transform(texts)]
        if self.char:
            matrices.append(self.char.fit_transform(texts) * self.char_weight)
        if self.semantic_weight:
            matrices.append(
                sparse.csr_matrix(
                    (embed(texts) if embeddings is None else embeddings)
                    * self.semantic_weight
                )
            )
        return sparse.hstack(matrices, format="csr")

    def transform(self, texts, embeddings=None):
        matrices = [self.word.transform(texts)]
        if self.char:
            matrices.append(self.char.transform(texts) * self.char_weight)
        if self.semantic_weight:
            matrices.append(
                sparse.csr_matrix(
                    (embed(texts) if embeddings is None else embeddings)
                    * self.semantic_weight
                )
            )
        return sparse.hstack(matrices, format="csr")
