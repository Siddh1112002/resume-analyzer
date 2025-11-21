import re
from typing import Dict, List, Any

def word_count(text: str) -> int:
    if not text:
        return 0
    tokens = re.findall(r"\w+", text)
    return len(tokens)

def sentence_count(text: str) -> int:
    return max(1, len(re.findall(r"[.!?]+", text)))

def flesch_reading_ease(text: str) -> float:
    words = re.findall(r"\w+", text)
    wcount = max(1, len(words))
    s_count = sentence_count(text)
    syllables = 0
    for w in words:
        syllables += max(1, len(re.findall(r"[aeiouy]+", w.lower())))
    flesch = 206.835 - 1.015 * (wcount / s_count) - 84.6 * (syllables / wcount)
    return round(max(0.0, min(100.0, flesch)), 1)
