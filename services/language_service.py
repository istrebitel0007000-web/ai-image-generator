import re

from models.data import RU_VOCAB, UZ_VOCAB, RU_CYRILLIC, UZ_CYR_UNIQUE, UZ_LATIN_WORDS


def detect_language(text):
    lower = text.lower()
    words = set(re.split(r"[\s,،.!?]+", lower))
    total = len(text.replace(" ", ""))
    if total == 0:
        return "English"
    if any(c in UZ_CYR_UNIQUE for c in text):
        return "Uzbek"
    if words & UZ_LATIN_WORDS:
        return "Uzbek"
    for w in UZ_LATIN_WORDS:
        if w in lower:
            return "Uzbek"
    cyrillic = sum(1 for c in text if c in RU_CYRILLIC)
    if cyrillic / max(total, 1) > 0.25:
        return "Russian"
    return "English"


def expand_prompt(text, language):
    if language == "English":
        return text
    vocab  = RU_VOCAB if language == "Russian" else UZ_VOCAB
    result = text.lower()
    for phrase in sorted(vocab, key=len, reverse=True):
        if phrase in result:
            result = result.replace(phrase, vocab[phrase])
    return re.sub(r"\s{2,}", " ", result).strip()
