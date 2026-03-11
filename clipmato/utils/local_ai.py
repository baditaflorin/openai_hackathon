"""Lightweight local fallbacks for non-transcription AI steps."""
from __future__ import annotations

import re
from collections import Counter


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "but", "by",
    "can", "compared", "creator", "creators", "did", "do", "does", "explained",
    "for", "from", "had", "has", "have", "he", "her", "hers", "him", "his",
    "i", "if", "in", "into", "is", "it", "its", "me", "more", "most", "my",
    "of", "on", "or", "our", "ours", "podcast", "podcasts", "said", "she",
    "ship", "small", "so", "stay", "strategy", "talk", "talked", "team", "teams",
    "that", "the", "their", "tools",
    "them", "there", "these", "they", "this", "to", "us", "was", "we", "were",
    "what", "when", "where", "which", "who", "why", "with", "workflows", "would",
    "you", "your",
    "yours",
    "aceasta", "acest", "această", "aceste", "acolo", "acum", "ai", "ale", "alt",
    "alta", "alte", "altor", "am", "ar", "asupra", "asta", "astfel", "au", "avea",
    "avem", "avut", "azi", "ca", "care", "ce", "cel", "cele", "cei", "chiar",
    "cind", "când", "cu", "cum", "că", "către", "da", "dar", "de", "deja", "din",
    "dintre", "doar", "după", "ea", "ei", "el", "este", "eu", "fara", "fie",
    "fiind", "foarte", "fost", "iar", "in", "îi", "îl", "în", "încă", "între",
    "la", "le", "li", "lor", "lui", "mai", "mea", "mei", "mereu", "mi", "mult",
    "ne", "ni", "nici", "noi", "nostru", "nu", "orice", "pe", "pentru", "peste",
    "prin", "sa", "sau", "se", "si", "spre", "sub", "sunt", "să", "te", "toate",
    "toată", "tot", "toti", "toți", "tu", "un", "una", "unde", "unei", "unii",
    "unor", "unui", "va", "vă",
}

LOCATION_HINTS = {"in", "at", "from", "to", "near", "across", "around"}
LOCATION_WORDS = {
    "America", "Asia", "Africa", "Europe", "Romania", "London", "Paris", "Berlin",
    "Tokyo", "New York", "San Francisco", "California", "Bucharest",
}


def normalize_text(text: str) -> str:
    """Collapse repeated whitespace without changing the content meaningfully."""
    return re.sub(r"\s+", " ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    """Extract rough sentence boundaries for basic summaries."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def top_keywords(text: str, limit: int = 5, exclude: set[str] | None = None) -> list[str]:
    """Return a few high-frequency keywords from transcript text."""
    excluded = {item.lower() for item in (exclude or set())}
    words = re.findall(r"[^\W\d_]{3,}", text.lower(), flags=re.UNICODE)
    counts = Counter(word for word in words if word not in STOP_WORDS and word not in excluded)
    return [word for word, _ in counts.most_common(limit)]


def extract_topics_basic(transcript: str, limit: int = 3) -> list[str]:
    """Pull a few human-readable topic phrases from the transcript."""
    normalized = normalize_text(transcript)
    candidates: list[str] = []

    patterns = [
        r"\babout ([^.?!]+)",
        r"\bdiscuss(?:ed|ing)? ([^.?!]+)",
        r"\bcompare(?:d|s|ing)? ([^.?!]+)",
        r"\bcover(?:ed|ing)? ([^.?!]+)",
    ]
    for pattern in patterns:
        for segment in re.findall(pattern, normalized, flags=re.IGNORECASE):
            candidates.extend(re.split(r",| and ", segment))

    topics: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        cleaned = candidate.strip(" .,:;")
        words = [word for word in cleaned.split() if word.lower() not in STOP_WORDS]
        if not words:
            continue
        phrase = " ".join(words[:3]).title()
        key = phrase.lower()
        if key not in seen:
            topics.append(phrase)
            seen.add(key)
        if len(topics) >= limit:
            break
    return topics


def describe_transcript_basic(transcript: str) -> dict[str, str]:
    """Create a small local summary without an external model."""
    normalized = normalize_text(transcript)
    sentences = split_sentences(normalized)
    if not normalized or not sentences:
        return {
            "short_description": "Transcript available. Local summary could not extract key sentences.",
            "long_description": "Clipmato processed the recording locally, but there was not enough clear transcript text to build a longer summary.",
        }

    keywords = top_keywords(normalized, limit=6)
    primary = keywords[:3]
    secondary = keywords[3:6]

    def format_keywords(values: list[str]) -> str:
        titled = [value.title() for value in values if value]
        if not titled:
            return ""
        if len(titled) == 1:
            return titled[0]
        if len(titled) == 2:
            return f"{titled[0]} and {titled[1]}"
        return f"{', '.join(titled[:-1])}, and {titled[-1]}"

    def sentence_topics(sentence: str) -> list[str]:
        lowered = sentence.lower()
        return [keyword for keyword in keywords if keyword in lowered]

    ranked_sentences = sorted(
        sentences,
        key=lambda sentence: (
            len(set(sentence_topics(sentence))),
            sum(normalized.lower().count(keyword) for keyword in sentence_topics(sentence)),
            -abs(len(sentence) - 160),
        ),
        reverse=True,
    )

    emphasis_phrases: list[str] = []
    seen_phrase_keys: set[str] = set()
    for sentence in ranked_sentences:
        topics = sentence_topics(sentence)
        if not topics:
            continue
        phrase = format_keywords(topics[:3])
        key = phrase.casefold()
        if phrase and key not in seen_phrase_keys:
            emphasis_phrases.append(phrase)
            seen_phrase_keys.add(key)
        if len(emphasis_phrases) >= 2:
            break

    if primary:
        short_description = f"This clip focuses on {format_keywords(primary)}."
    else:
        short_description = "This clip captures a spoken update built from the recovered transcript."

    long_parts = [short_description]
    if emphasis_phrases:
        long_parts.append(f"The discussion keeps returning to {emphasis_phrases[0]}.")
    if len(emphasis_phrases) > 1:
        long_parts.append(f"It also touches on {emphasis_phrases[1]}.")
    elif secondary:
        long_parts.append(f"Additional themes include {format_keywords(secondary[:2])}.")

    long_parts.append("This summary was generated from the transcript fallback path, so review the wording before publishing.")
    long_description = _truncate(" ".join(long_parts), 500)
    return {
        "short_description": _truncate(short_description, 220),
        "long_description": long_description,
    }


def extract_entities_basic(transcript: str) -> dict[str, list[str]]:
    """Extract a few likely names and places using capitalization heuristics."""
    text = normalize_text(transcript)
    phrases = re.findall(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", text)

    people: list[str] = []
    locations: list[str] = []
    seen_people: set[str] = set()
    seen_locations: set[str] = set()

    for phrase in phrases:
        if phrase in {"The", "This", "That", "These", "Those", "Clipmato"}:
            continue
        if phrase in LOCATION_WORDS:
            if phrase not in seen_locations:
                locations.append(phrase)
                seen_locations.add(phrase)
            continue
        if " " in phrase and phrase not in seen_people:
            people.append(phrase)
            seen_people.add(phrase)

    for match in re.finditer(r"\b(" + "|".join(LOCATION_HINTS) + r")\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text):
        phrase = match.group(2)
        if phrase not in seen_locations and phrase not in seen_people:
            locations.append(phrase)
            seen_locations.add(phrase)

    return {
        "people": people[:8],
        "locations": locations[:8],
    }


def propose_titles_basic(transcript: str) -> list[str]:
    """Generate a few usable title candidates from keywords and the opening summary."""
    entities = extract_entities_basic(transcript)
    excluded = {
        token
        for phrase in entities["people"] + entities["locations"]
        for token in phrase.split()
    }
    topics = extract_topics_basic(transcript, limit=3)
    keywords = [word.title() for word in top_keywords(transcript, limit=3, exclude=excluded)]
    subject = " and ".join(topics[:2]) if topics else " and ".join(keywords[:2]) if keywords else "the latest conversation"
    guest = entities["people"][0] if entities["people"] else None

    seeds = [
        f"Inside {subject}",
        f"What We Learned About {subject}",
        f"The Big Takeaway on {subject}",
        f"A Practical Guide to {subject}",
        f"{guest}: Lessons on {subject}" if guest else f"How {subject} Shapes the Next Episode",
    ]

    titles: list[str] = []
    for seed in seeds:
        cleaned = _truncate(seed.replace("  ", " ").strip(" ."), 80)
        if cleaned and cleaned not in titles:
            titles.append(cleaned)

    while len(titles) < 5:
        titles.append(f"Episode Insight #{len(titles) + 1}")
    return titles[:5]


def generate_script_basic(transcript: str) -> str:
    """Produce a lightweight local script outline and interview prompts."""
    description = describe_transcript_basic(transcript)
    entities = extract_entities_basic(transcript)
    excluded = {
        token
        for phrase in entities["people"] + entities["locations"]
        for token in phrase.split()
    }
    topics = extract_topics_basic(transcript, limit=3)
    keywords = top_keywords(transcript, limit=3, exclude=excluded)
    focus = ", ".join(topics or keywords) if (topics or keywords) else "the key themes from the recording"
    return (
        f"Show notes: {description['long_description']}\n\n"
        "Interview questions:\n"
        f"1. What is the most important audience takeaway from {focus}?\n"
        "2. Which example or story best illustrates the main point?\n"
        "3. What should listeners do next if they want to go deeper?"
    )


def distribute_basic(_: str) -> str:
    """Return a clear local placeholder for the distribution step."""
    return "Distribution skipped in local mode. Connect a publishing backend to automate delivery."
