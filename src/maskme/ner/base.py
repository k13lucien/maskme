"""
maskme.ner.base
~~~~~~~~~~~~~~~~~~~~~~~~~
Formal contracts for the unstructured data anonymization layer.

Two building blocks:

    Entity   — a detected PII span within a text, produced by any detector.
    Detector — a Protocol that every detector module must satisfy.

Design principles:
    - Detectors are stateless functions wrapped in a class.
    - Each detector is responsible only for finding entities — never for
      masking them. Masking is handled exclusively by masker.py.
    - Multiple detectors can run on the same text; pipeline.py resolves
      overlapping spans.

Adding a new detector (e.g. DictionaryDetector):
    1. Create  ner/detectors/dictionary_detector.py
    2. Implement a class that satisfies the Detector Protocol
    3. Register it in ner/__init__.py under DETECTORS
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class EntityLabel(str, Enum):
    """
    Standardised entity label set shared across all detectors.

    Using an enum prevents label drift between detectors (e.g. one
    returning "PERSON" and another returning "PER").  All detectors
    must map their internal labels to these values.

    Labels are grouped by category:
        Identity     — who the person is
        Contact      — how to reach them
        Location     — where they are
        Temporal     — when something happened
        Medical      — clinical and health information
        Financial    — monetary and account data
        Technical    — system and network identifiers
        Organisation — institutions and companies
    """

    # Identity
    PERSON      = "PERSON" 

    # Contact
    EMAIL       = "EMAIL"
    PHONE       = "PHONE"
    ADDRESS     = "ADDRESS"

    # Location
    LOCATION    = "LOCATION"     # City, region, country
    POSTAL_CODE = "POSTAL_CODE"

    # Temporal
    DATE        = "DATE"
    TIME        = "TIME"
    DATETIME    = "DATETIME"

    # Medical
    MEDICAL_ID  = "MEDICAL_ID"   # NIP, IPP, dossier number
    DOSAGE      = "DOSAGE"       # e.g. "500mg", "2cp/j"
    MEDICAL_CODE = "MEDICAL_CODE" # ICD-10, CIM-10 codes

    # Financial
    NIR         = "NIR"          # Numéro de Sécurité Sociale
    IBAN        = "IBAN"
    CREDIT_CARD = "CREDIT_CARD"

    # Technical
    IP_ADDRESS  = "IP_ADDRESS"
    URL         = "URL"

    # Organisation
    ORGANISATION = "ORGANISATION"

    # Catch-all for domain-specific patterns not covered above
    CUSTOM      = "CUSTOM"


# ---------------------------------------------------------------------------
# Entity dataclass
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    """
    A single detected PII span within a text.

    Attributes:
        text:       The exact substring that was detected.
        label:      Standardised entity label (EntityLabel).
        start:      Character offset of the start of the span (inclusive).
        end:        Character offset of the end of the span (exclusive).
                    text == source_text[start:end] must always hold.
        score:      Confidence score in [0.0, 1.0].
                    Regex detections are always 1.0 (deterministic).
                    NER detections carry the model's confidence.
        detector:   Name of the detector that produced this entity,
                    for traceability and conflict resolution.
        metadata:   Arbitrary extra data (e.g. regex group name,
                    normalised value, spaCy entity type).
    """

    text:     str
    label:    EntityLabel
    start:    int
    end:      int
    score:    float               = 1.0
    detector: str                 = ""
    metadata: Dict[str, Any]      = field(default_factory=dict)

    def overlaps(self, other: "Entity") -> bool:
        """Return True if this entity's span overlaps with another's."""
        return self.start < other.end and other.start < self.end

    def contains(self, other: "Entity") -> bool:
        """Return True if this entity's span fully contains another's."""
        return self.start <= other.start and self.end >= other.end

    def __len__(self) -> int:
        """Return the character length of the detected span."""
        return self.end - self.start

    def __repr__(self) -> str:
        return (
            f"Entity(text={self.text!r}, label={self.label.value}, "
            f"start={self.start}, end={self.end}, score={self.score:.2f}, "
            f"detector={self.detector!r})"
        )


# ---------------------------------------------------------------------------
# Detector Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class Detector(Protocol):
    """
    Protocol that every entity detector must satisfy.

    A detector receives a text string and returns a list of Entity objects.
    It must never modify the text or apply any masking.

    The name attribute is used by the pipeline for logging, priority
    resolution, and conflict reporting.

    Example implementation skeleton:

        class MyDetector:
            name     = "my_detector"
            priority = 50   # higher = wins span conflicts

            def detect(
                self,
                text: str,
                language: str = "fr",
                **kwargs,
            ) -> List[Entity]:
                entities = []
                # ... find spans ...
                return entities
    """

    #: Stable identifier used in registry keys and entity.detector field.
    name: str

    #: Priority for span conflict resolution (higher wins).
    #: Regex detectors default to 100 (deterministic, most reliable).
    #: spaCy detectors default to 50 (contextual but probabilistic).
    #: Domain detectors default to 80 (curated but narrower scope).
    priority: int

    def detect(
        self,
        text: str,
        language: str = "fr",
        **kwargs: Any,
    ) -> List[Entity]:
        """
        Detect PII entities in a text string.

        Args:
            text:     The raw text to analyse.
            language: ISO 639-1 language code ("fr" or "en").
                      Detectors may use this to apply language-specific
                      patterns or load the appropriate NLP model.
            **kwargs: Detector-specific parameters.

        Returns:
            List of Entity objects found in the text.
            Must never return overlapping spans from the same detector.
            Returns an empty list if no entities are found.
        """
        ...


# ---------------------------------------------------------------------------
# Span resolution strategy
# ---------------------------------------------------------------------------

def resolve_spans(entities: List[Entity]) -> List[Entity]:
    """
    Resolve overlapping entity spans from multiple detectors.

    Resolution rules (applied in order):
        1. Longer span wins over shorter span (more context = more precise).
        2. Higher detector priority wins when spans have equal length.
        3. Higher confidence score breaks remaining ties.

    The result is a set of non-overlapping entities sorted by start offset,
    ready to be passed to masker.py for text reconstruction.

    Args:
        entities: Raw entity list, potentially with overlapping spans.

    Returns:
        Deduplicated, non-overlapping list of Entity objects sorted by
        their start position in the source text.
    """
    if not entities:
        return []

    # Sort by start position, then by length descending, then by priority desc
    sorted_entities = sorted(
        entities,
        key=lambda e: (e.start, -(e.end - e.start), -e.score),
    )

    resolved: List[Entity] = []
    for candidate in sorted_entities:
        if not resolved:
            resolved.append(candidate)
            continue

        last = resolved[-1]
        if not candidate.overlaps(last):
            resolved.append(candidate)
        else:
            # Conflict: keep the one with higher priority, then length, then score
            incumbent_score = (
                last.end - last.start,
                getattr(last, "priority", 50),
                last.score,
            )
            challenger_score = (
                candidate.end - candidate.start,
                getattr(candidate, "priority", 50),
                candidate.score,
            )
            if challenger_score > incumbent_score:
                resolved[-1] = candidate

    return sorted(resolved, key=lambda e: e.start)