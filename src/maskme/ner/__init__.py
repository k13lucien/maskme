"""
maskme.ner
~~~~~~~~~~~~~~~~~~~~
Unstructured text anonymization for MaskMe.

Detects and masks PII in free text (medical reports, legal documents,
emails, etc.) using spaCy NER, with support for French and English.

The :func:`mask` function is the **single entry point**:

    >>> from maskme.ner import mask
    >>> result = mask("Alice habite à Paris.")
    >>> result.output
    '[PERSON] habite à [LOCATION].'

Batch:

    >>> results = mask(["Alice habite à Paris.", "John lives in London."])
    >>> [r.output for r in results]
    ['[PERSON] habite à [LOCATION].', '[PERSON] lives in [LOCATION].']
"""

from __future__ import annotations

from maskme.ner.base import Detector, Entity, EntityLabel, resolve_spans
from maskme.ner.detectors.spacy_detector import SpacyDetector
from maskme.ner.pipeline import PipelineResult, mask

__all__ = [
    "mask",
    "PipelineResult",
    "Entity",
    "EntityLabel",
    "Detector",
    "resolve_spans",
]
