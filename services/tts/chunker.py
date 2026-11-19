"""Split text into pieces of about 100-120 chars without cutting inside a word."""
import re

MAX_LEN = 90
MIN_LEN = 70  # soft target when packing clauses

_SENT_END = re.compile(r"(?<=[.!?।॥])\s+")
# clause breaks: after , ; : or before the conjunctions aur / lekin / ki
_CLAUSE = re.compile(
    r"(?<=[,;:])\s+|\s+(?=(?:aur|lekin|ki|और|लेकिन|कि)\s)", re.IGNORECASE
)


def _pack(parts: list[str], limit: int) -> list[str]:
    out: list[str] = []
    cur = ""
    for p in parts:
        cand = f"{cur} {p}".strip() if cur else p
        if len(cand) <= limit:
            cur = cand
        else:
            if cur:
                out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    return out


def _split_long(piece: str) -> list[str]:
    """Break one over-long piece: clauses first, then spaces. Never inside a word."""
    clauses = [c.strip() for c in _CLAUSE.split(piece) if c.strip()]
    packed = _pack(clauses, MAX_LEN)
    out: list[str] = []
    for c in packed:
        if len(c) <= MAX_LEN:
            out.append(c)
        else:
            out.extend(_pack(c.split(), MAX_LEN))  # a single huge word stays whole
    return out


def chunk_text(text: str) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    pieces: list[str] = []
    for sent in _SENT_END.split(text):
        sent = sent.strip()
        if not sent:
            continue
        pieces.extend([sent] if len(sent) <= MAX_LEN else _split_long(sent))
    # fold very short pieces into their neighbour so we avoid tiny synth calls
    merged: list[str] = []
    for p in pieces:
        if merged and len(merged[-1]) < 20 and len(merged[-1]) + 1 + len(p) <= MAX_LEN:
            merged[-1] = f"{merged[-1]} {p}"
        else:
            merged.append(p)
    return merged
