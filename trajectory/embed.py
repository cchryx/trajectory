"""Turn text into 384-number vectors.

Uses fastembed with BAAI/bge-small-en-v1.5. It runs on ONNX Runtime, so no GPU and no PyTorch.
The model downloads once (about 70 MB) into MODEL_CACHE (default: models/ at the repo root).

Set EMBEDDER=hash to use a small fake embedder instead. It needs no download and is only
for tests: texts that share words get similar vectors, nothing more.
"""

import hashlib
import os
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384
ROOT = Path(__file__).resolve().parent.parent


def _use_hash():
    return os.environ.get("EMBEDDER", "").lower() == "hash"


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding

    cache = os.environ.get("MODEL_CACHE", str(ROOT / "models"))
    return TextEmbedding(MODEL, cache_dir=cache)


def _hash_vector(text):
    """Fake vector for tests: each word adds 1 to a slot picked by its hash."""
    vec = np.zeros(DIM, dtype=np.float32)
    for word in re.findall(r"[a-z0-9+#]+", text.lower()):
        slot = int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM
        vec[slot] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def embed_passages(texts, batch_size=64):
    """Vectors for documents: postings, courses and resumes."""
    texts = list(texts)
    if _use_hash():
        return [_hash_vector(t).tolist() for t in texts]
    return [v.tolist() for v in _model().embed(texts, batch_size=batch_size)]


def embed_query(text):
    """Vector for a short search question. bge adds its search prefix here."""
    if _use_hash():
        return _hash_vector(text).tolist()
    return next(iter(_model().query_embed([text]))).tolist()


def warm():
    """Load the model now, so the first request is not slow."""
    embed_passages(["warm up"])


def to_pg(vec):
    """Format a vector for Postgres: '[0.1,0.2,...]'. Use it with %s::vector."""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
