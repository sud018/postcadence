"""Turn raw model output into a post that looks right on LinkedIn."""
from __future__ import annotations

import re

MAX_LENGTH = 3000
MAX_HASHTAGS = 3

FENCE = re.compile(r"^```.*$", re.MULTILINE)
HEADING = re.compile(r"^#{1,6}\s*", re.MULTILINE)
BOLD_ITALIC = re.compile(r"(\*{1,3}|_{2,3})(.+?)\1")
QUOTE = re.compile(r"^>\s?", re.MULTILINE)
RULE = re.compile(r"^\s*([-*_])\1{2,}\s*$", re.MULTILINE)
BULLET = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)
BLANKS = re.compile(r"\n{3,}")
TRAILING = re.compile(r"[ \t]+$", re.MULTILINE)
HASHTAG = re.compile(r"#\w+")
WRAPPED = re.compile(r'^["\'](.+)["\']$', re.DOTALL)

STOPWORDS = {
    "a", "an", "and", "the", "to", "of", "in", "for", "on", "with", "without",
    "how", "why", "what", "when", "is", "are", "my", "your", "i", "it", "that",
    "this", "they", "them", "from", "at", "by", "or", "vs", "be", "you", "we",
    "actually", "still", "just", "got", "not", "do", "does", "can", "should",
    "first", "end", "learned", "built", "building", "beat", "picking", "right",
    "choosing", "cutting", "changing", "making", "using", "getting", "adding",
    "combining", "measuring", "improving", "shipping", "fail", "fails",
}

def strip_markdown(text: str) -> str:
    """Remove formatting LinkedIn cannot render."""
    text = FENCE.sub("", text)
    text = RULE.sub("", text)
    text = HEADING.sub("", text)
    text = QUOTE.sub("", text)
    text = BOLD_ITALIC.sub(r"\2", text)
    return text

def normalise_bullets(text: str, marker: str = "→ ") -> str:
    """Markdown bullets become a character LinkedIn shows as typed."""
    return BULLET.sub(marker, text)

def tidy_spacing(text: str) -> str:
    """One blank line between paragraphs, no trailing spaces."""
    text = TRAILING.sub("", text)
    text = BLANKS.sub("\n\n", text)
    return text.strip()

def unwrap_quotes(text: str) -> str:
    """Models sometimes wrap the whole post in quotation marks."""
    match = WRAPPED.match(text.strip())
    return match.group(1).strip() if match else text

def hashtags_for(topic: str, existing: str, limit: int = MAX_HASHTAGS) -> list[str]:
    """Pick the most distinctive words in the topic and turn them into hashtags.

    Acronyms (RAG, LLM) win, then longer words - they make better tags than
    short common ones. Anything already hashtagged in the post is skipped.
    """
    already = {tag.lower() for tag in HASHTAG.findall(existing)}
    candidates: list[tuple[int, int, str]] = []

    for position, word in enumerate(re.findall(r"[A-Za-z][A-Za-z0-9]+", topic)):
        if word.lower() in STOPWORDS or len(word) < 3:
            continue
        tag = "#" + (word.upper() if word.isupper() else word.capitalize())
        if tag.lower() in already or any(tag == c[2] for c in candidates):
            continue
        score = (100 if word.isupper() else 0) + len(word)
        candidates.append((score, position, tag))

    best = sorted(candidates, key=lambda c: -c[0])[:limit]
    return [tag for _, _, tag in sorted(best, key=lambda c: c[1])]

def fit_length(text: str, limit: int = MAX_LENGTH) -> str:
    """Trim to the limit at a paragraph or sentence boundary, never mid-word."""
    if len(text) <= limit:
        return text

    cut = text[:limit]
    for boundary in ("\n\n", ". ", "\n"):
        position = cut.rfind(boundary)
        if position > limit * 0.6:
            return cut[:position].rstrip(" .\n") + ("." if boundary == ". " else "")
    return cut.rsplit(" ", 1)[0].rstrip() + "..."

def format_post(raw: str, topic: str, add_hashtags: bool = True) -> str:
    """Full clean-up: raw model text in, publishable post out."""
    text = unwrap_quotes(raw)
    text = strip_markdown(text)
    text = normalise_bullets(text)
    text = tidy_spacing(text)

    if add_hashtags:
        tags = hashtags_for(topic, text)
        if tags:
            text = f"{text}\n\n{' '.join(tags)}"

    return fit_length(text)
