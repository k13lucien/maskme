"""
maskme.ner.language
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Local language detection for French and English text.

Uses langdetect (a port of Google's language-detection library) which
runs entirely offline — no API calls, no network required.

Supported languages: French ("fr") and English ("en").
Any other detected language falls back to the configured default.

Key design decisions:
    - langdetect is non-deterministic by default (uses random sampling).
      A fixed seed is set at import time for reproducible results.
    - Short texts (< MIN_CHARS) are unreliable for detection and fall
      back to the default language immediately.
    - The detect() function never raises — all exceptions return the
      default language so the pipeline never crashes on detection failure.

Installation:
    pip install langdetect
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum character count for reliable language detection.
# Texts shorter than this are too ambiguous and fall back to default.
_MIN_CHARS = 20

# Supported ISO 639-1 language codes.
SUPPORTED_LANGUAGES = {"fr", "en"}

# Module-level flag: True if langdetect is available, False otherwise.
_LANGDETECT_AVAILABLE = False

try:
    from langdetect import detect as _langdetect_detect
    from langdetect import DetectorFactory
    # Fix the random seed for reproducible detection across runs.
    DetectorFactory.seed = 42
    _LANGDETECT_AVAILABLE = True
except ImportError:
    logger.warning(
        "langdetect is not installed. Language detection will always return "
        "the default language. Install it with: pip install langdetect"
    )


def detect(
    text: str,
    default: str = "fr",
    min_chars: int = _MIN_CHARS,
) -> str:
    """
    Detect the language of a text string.

    Returns "fr" or "en". Any other detected language (e.g. "de", "ar")
    falls back to default, since only French and English detectors are
    currently registered.

    Args:
        text:      The text to analyse.
        default:   Language code to return when detection fails or
                   the detected language is not supported.
                   Defaults to "fr" (most common in the target context).
        min_chars: Minimum text length for reliable detection.
                   Texts shorter than this always return default.

    Returns:
        ISO 639-1 language code: "fr" or "en".

    Examples:
        >>> detect("Le patient présente une fièvre de 39°C.")
        'fr'
        >>> detect("The patient presents with a fever of 39°C.")
        'en'
        >>> detect("Hi")          # too short
        'fr'
        >>> detect("", default="en")
        'en'
    """
    if not text or len(text.strip()) < min_chars:
        return default

    if not _LANGDETECT_AVAILABLE:
        return default

    try:
        detected = _langdetect_detect(text)
        if detected in SUPPORTED_LANGUAGES:
            return detected
        logger.debug(
            "Detected language '%s' is not supported. "
            "Falling back to '%s'.", detected, default
        )
        return default
    except Exception as exc:
        logger.debug(
            "Language detection failed (%s). Falling back to '%s'.",
            exc, default,
        )
        return default


def detect_segments(
    text: str,
    segment_size: int = 500,
    default: str = "fr",
) -> str:
    """
    Detect language by voting across multiple text segments.

    More robust than single-pass detection for long documents that may
    contain mixed-language passages (e.g. a French report with English
    medical abbreviations).

    Splits the text into overlapping segments of segment_size characters,
    detects the language of each, and returns the majority language.

    Args:
        text:         The text to analyse.
        segment_size: Characters per segment. Larger values are more
                      accurate but slower for very long documents.
        default:      Fallback language if no majority emerges.

    Returns:
        ISO 639-1 language code: "fr" or "en".
    """
    if not text or len(text) < _MIN_CHARS:
        return default

    # Sample at most 5 segments evenly distributed through the text
    step     = max(len(text) // 5, segment_size)
    segments = [
        text[i: i + segment_size]
        for i in range(0, len(text), step)
        if len(text[i: i + segment_size].strip()) >= _MIN_CHARS
    ][:5]

    if not segments:
        return default

    votes: dict[str, int] = {}
    for segment in segments:
        lang = detect(segment, default=default)
        votes[lang] = votes.get(lang, 0) + 1

    # Return the language with the most votes; default breaks ties
    winner = max(votes, key=lambda k: (votes[k], k == default))
    return winner


def is_french(text: str, default: str = "fr") -> bool:
    """Convenience function: True if the text is detected as French."""
    return detect(text, default=default) == "fr"


def is_english(text: str, default: str = "fr") -> bool:
    """Convenience function: True if the text is detected as English."""
    return detect(text, default=default) == "en"