"""
maskme.ner.pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unstructured text anonymization pipeline for MaskMe.

The :func:`mask` function is the single entry point to the module:
detect entities via spaCy NER and replace them with anonymized tags.

Usage:

    >>> from maskme.ner import mask
    >>> result = mask("Alice habite à Paris.")
    >>> result.output
    '[PERSON] habite à [LOCATION].'

Batch:

    >>> results = mask(["Alice habite à Paris.", "John lives in London."])
    >>> [r.output for r in results]
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from maskme.ner.base import Entity, EntityLabel, resolve_spans
from maskme.ner.language import detect as detect_language

logger = logging.getLogger(__name__)

_MIN_ENTITY_LENGTH = 2


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    """
    Output of a single :func:`mask` call.

    Attributes:
        output:   Text with all detected entities replaced by tags
                  (e.g. ``[PERSON]``, ``[LOCATION]``).
        input:    Original input text.
        entities: Non-overlapping entities after span resolution,
                  sorted by start offset.
        language: Detected or overridden language code (``"fr"`` / ``"en"``).
        stats:    Processing metadata.
    """

    output:   str
    input:    str
    entities: List[Entity]
    language: str
    stats:    Dict[str, Any] = field(default_factory=dict)

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def labels_found(self) -> List[str]:
        return sorted({e.label.value for e in self.entities})

    def as_dict(self) -> Dict[str, Any]:
        return {
            "input":      self.input,
            "output":     self.output,
            "language":   self.language,
            "entity_count":    self.entity_count,
            "labels_found":    self.labels_found,
            "entities": [
                {
                    "text":     e.text,
                    "label":    e.label.value,
                    "start":    e.start,
                    "end":      e.end,
                    "score":    e.score,
                    "detector": e.detector,
                }
                for e in self.entities
            ],
            "stats": self.stats,
        }


# ---------------------------------------------------------------------------
# mask — single entry point
# ---------------------------------------------------------------------------

def mask(
    text: Union[str, List[str]],
    language: Optional[str] = None,
) -> Union[PipelineResult, List[PipelineResult]]:
    """
    Detect and replace PII in text with anonymized tags (``[PERSON]``, etc.).

    This is the **single entry point** to the NER module. Pass a string
    for single-text processing or a list of strings for batch processing.

    Args:
        text:     Text string or list of text strings to mask.
        language: Language override (``"fr"`` / ``"en"``).
                  Auto-detected if ``None``.

    Returns:
        ``PipelineResult`` if ``text`` is a single string.
        ``List[PipelineResult]`` if ``text`` is a list.

    Simple usage:

        >>> from maskme.ner import mask
        >>> result = mask("Alice habite à Paris.")
        >>> result.output
        '[PERSON] habite à [LOCATION].'

    Batch:

        >>> results = mask(["Alice habite à Paris.", "John lives in London."])
        >>> [r.output for r in results]
        ['[PERSON] habite à [LOCATION].', '[PERSON] lives in [LOCATION].']

    Language hint:

        >>> mask("John lives in London.", language="en").output
        '[PERSON] lives in [LOCATION].'
    """
    if isinstance(text, list):
        return [_process_single(t, language) for t in text]
    return _process_single(text, language)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _process_single(
    text: str,
    language: Optional[str],
) -> PipelineResult:
    start = time.perf_counter()

    if not text or not text.strip():
        return PipelineResult(
            output=text,
            input=text,
            entities=[],
            language=language or "fr",
            stats=_empty_stats(),
        )

    # 1. Language detection
    lang = language or detect_language(text, default="fr")

    # 2. Entity detection
    from maskme.ner.detectors.spacy_detector import SpacyDetector
    detector = SpacyDetector()
    if not SpacyDetector.is_available(lang):
        logger.warning(
            "No spaCy model available for '%s'. "
            "Install: python -m spacy download %s_core_news_lg",
            lang, lang,
        )
        raw_entities = []
        detectors_run: List[str] = []
    else:
        raw_entities = detector.detect(text, language=lang)
        raw_entities = [e for e in raw_entities if len(e.text.strip()) >= _MIN_ENTITY_LENGTH]
        detectors_run = [detector.name]

    # 3. Span resolution
    resolved = resolve_spans(raw_entities)

    # 4. Masking (tag replacement)
    output = _replace_spans(text, resolved)

    elapsed = (time.perf_counter() - start) * 1000

    return PipelineResult(
        output=output,
        input=text,
        entities=resolved,
        language=lang,
        stats={
            "n_entities_raw":      len(raw_entities),
            "n_entities_resolved": len(resolved),
            "detectors_run":       detectors_run,
            "processing_ms":       round(elapsed, 2),
        },
    )


def _empty_stats() -> Dict[str, Any]:
    return {
        "n_entities_raw": 0,
        "n_entities_resolved": 0,
        "detectors_run": [],
        "processing_ms": 0.0,
    }


def _replace_spans(text: str, entities: List[Entity]) -> str:
    """Replace each entity span with its tag (``[PERSON]``, ``[DATE]``, ...)."""
    if not entities:
        return text
    chars = list(text)
    for e in sorted(entities, key=lambda x: x.start, reverse=True):
        tag = f"[{e.label.value}]"
        chars[e.start:e.end] = list(tag)
    return "".join(chars)
