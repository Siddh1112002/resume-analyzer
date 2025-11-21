# -*- coding: utf-8 -*-
"""
semantic.py
Provides semantic matching functions using sentence-transformers when available,
and a robust lexical fallback when not.
"""
import os, re
from typing import List, Tuple

_has_transformers = False
try:
    from sentence_transformers import SentenceTransformer, util
    _has_transformers = True
except Exception:
    _has_transformers = False

_MODEL = None
def _load_model():
    global _MODEL
    if _MODEL is None and _has_transformers:
        _MODEL = SentenceTransformer(os.getenv("LOCAL_EMBED_MODEL", "all-MiniLM-L6-v2"))
    return _MODEL

def embed_texts(texts: List[str]):
    """
    Returns list of numpy-like vectors if model available, else None.
    """
    model = _load_model()
    if not model:
        return None
    return model.encode(texts, convert_to_tensor=True)

def semantic_matches(doc_text: str, candidates: List[str], top_k: int = 10) -> List[Tuple[str, float]]:
    """
    If sentence-transformers available, returns candidates ranked by cosine similarity.
    Otherwise falls back to lexical fuzzy scoring (simple).
    Returns list of (candidate, score 0..100)
    """
    if not doc_text or not candidates:
        return []

    if _has_transformers:
        try:
            doc_emb = embed_texts([doc_text])[0]
            cand_embs = embed_texts(candidates)
            sims = util.cos_sim(doc_emb, cand_embs)[0].tolist()
            out = [(candidates[i], float(sims[i])) for i in range(len(candidates))]
            out.sort(key=lambda x: x[1], reverse=True)
            return [(t[0], int(round(t[1]*100))) for t in out[:top_k]]
        except Exception:
            pass

    doc_tokens = set(re.findall(r"\w+", doc_text.lower()))
    out = []
    for c in candidates:
        c_tokens = set(re.findall(r"\w+", c.lower()))
        overlap = len(doc_tokens & c_tokens)
        total = max(1, len(c_tokens))
        score = int(round(100.0 * overlap / total))
        out.append((c, score))
    out.sort(key=lambda x: x[1], reverse=True)
    return out[:top_k]
