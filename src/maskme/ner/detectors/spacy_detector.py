"""
maskme.ner.detectors.spacy_detector
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
spaCy-based Named Entity Recognition detector for French and English.

Detects contextual entities that regex cannot find — names, organisations,
and locations — by leveraging spaCy's statistical NER models.

Supported models:
    French  : fr_core_news_lg  (or fr_core_news_md as fallback)
    English : en_core_web_lg   (or en_core_web_md as fallback)

Installation:
    pip install spacy
    python -m spacy download fr_core_news_lg
    python -m spacy download en_core_web_lg

Design decisions:
    - Models are loaded lazily (on first use per language) to avoid
      paying the startup cost when spaCy detection is not needed.
    - If a model is unavailable, a warning is logged and an empty list
      is returned.
    - Priority is 50 (lower priority spans lose to higher priority
      ones during conflict resolution in resolve_spans()).
    - spaCy labels are mapped to the shared EntityLabel enum to ensure
      consistency across all detectors.

spaCy label mapping:
    FR (fr_core_news_lg) : PER → PERSON, LOC → LOCATION, ORG → ORGANISATION,
                           MISC → skipped, DATE/TIME → DATE/TIME
    EN (en_core_web_lg)  : PERSON → PERSON, GPE/LOC/FAC → LOCATION,
                           ORG → ORGANISATION, DATE → DATE, TIME → TIME,
                           others → skipped
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from maskme.ner.base import Detector, Entity, EntityLabel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# spaCy availability check
# ---------------------------------------------------------------------------

_SPACY_AVAILABLE = False
try:
    import spacy
    _SPACY_AVAILABLE = True
except ImportError:
    logger.warning(
        "spaCy is not installed. The spaCy detector will return no entities. "
        "Install it with: pip install spacy"
    )

# ---------------------------------------------------------------------------
# Label mappings — spaCy internal → EntityLabel
# ---------------------------------------------------------------------------

# French model labels (fr_core_news_lg / fr_core_news_md)
_FR_LABEL_MAP: Dict[str, Optional[EntityLabel]] = {
    "PER":   EntityLabel.PERSON,
    "LOC":   EntityLabel.LOCATION,
    "ORG":   EntityLabel.ORGANISATION,
    "DATE":  EntityLabel.DATE,
    "TIME":  EntityLabel.TIME,
    "MISC":  None,
}

# English model labels (en_core_web_lg / en_core_web_md)
_EN_LABEL_MAP: Dict[str, Optional[EntityLabel]] = {
    "PERSON":   EntityLabel.PERSON,
    "GPE":      EntityLabel.LOCATION,   # Geopolitical entity
    "LOC":      EntityLabel.LOCATION,
    "FAC":      EntityLabel.LOCATION,   # Facility (hospital, airport)
    "ORG":      EntityLabel.ORGANISATION,
    "DATE":     EntityLabel.DATE,
    "TIME":     EntityLabel.TIME,
    "CARDINAL": None,   # raw numbers — skip
    "MONEY":    None,   # handled by regex
    "PERCENT":  None,
    "ORDINAL":  None,
    "QUANTITY": None,
    "NORP":     None,   # nationalities/political groups — too broad
    "LANGUAGE": None,
    "LAW":      None,
    "PRODUCT":  None,
    "EVENT":    None,
    "WORK_OF_ART": None,
}

# ---------------------------------------------------------------------------
# Model registry — lazy loading
# ---------------------------------------------------------------------------

# Preferred model names per language, with smaller fallbacks
_MODEL_PREFERENCE: Dict[str, List[str]] = {
    "fr": ["fr_core_news_lg", "fr_core_news_md", "fr_core_news_sm"],
    "en": ["en_core_web_lg",  "en_core_web_md",  "en_core_web_sm"],
}

# Cache: language → loaded spaCy nlp object (or None if unavailable)
_MODEL_CACHE: Dict[str, Any] = {}


def _load_model(language: str) -> Optional[Any]:
    """
    Load and cache a spaCy model for the given language.

    Tries models in order of preference (lg → md → sm) and caches the
    first successfully loaded model. Returns None if none are available.
    """
    if language in _MODEL_CACHE:
        return _MODEL_CACHE[language]

    if not _SPACY_AVAILABLE:
        _MODEL_CACHE[language] = None
        return None

    for model_name in _MODEL_PREFERENCE.get(language, []):
        try:
            nlp = spacy.load(
                model_name,
                # Load only the NER component — skip tagger, parser, etc.
                # for significantly faster processing.
                exclude=["tagger", "parser", "lemmatizer",
                         "attribute_ruler", "morphologizer"],
            )
            logger.info("spaCy model loaded: %s", model_name)
            _MODEL_CACHE[language] = nlp
            return nlp
        except OSError:
            logger.debug("spaCy model '%s' not found, trying next.", model_name)

    logger.warning(
        "No spaCy model available for language '%s'. "
        "Install one with: python -m spacy download %s",
        language,
        _MODEL_PREFERENCE.get(language, [""])[0],
    )
    _MODEL_CACHE[language] = None
    return None


# ---------------------------------------------------------------------------
# Detector class
# ---------------------------------------------------------------------------

class SpacyDetector:
    """
    Named Entity Recognition detector using spaCy's statistical models.

    Detects contextual PII: names, organisations, locations, and temporal
    expressions that require linguistic context to identify reliably.

    Does NOT detect structured patterns (email, phone, ID numbers) —
    the legacy RegexDetector has been removed; consider adding a custom
    detector if you need structured pattern matching.
    """

    name     = "spacy"
    priority = 50   # contextual, probabilistic — lower = less precedence

    def detect(
        self,
        text: str,
        language: str = "fr",
        min_confidence: float = 0.0,
        **kwargs: Any,
    ) -> List[Entity]:
        """
        Run spaCy NER on a text and return detected entities.

        Args:
            text:           The text to analyse.
            language:       ISO 639-1 code ("fr" or "en").
            min_confidence: Minimum confidence threshold. spaCy does not
                            expose per-entity scores in standard NER, so
                            this parameter is reserved for future use with
                            spacy-transformers models that do provide scores.
            **kwargs:       Ignored (forwarded by the pipeline runner).

        Returns:
            List of Entity objects. Returns an empty list if spaCy is
            unavailable, no model is installed, or no entities are found.
        """
        if not text or not text.strip():
            return []

        nlp = _load_model(language)
        if nlp is None:
            return []

        label_map = _FR_LABEL_MAP if language == "fr" else _EN_LABEL_MAP

        try:
            doc = nlp(text)
        except Exception as exc:
            logger.warning("spaCy processing failed: %s", exc)
            return []

        entities = []
        for ent in doc.ents:
            entity_label = label_map.get(ent.label_)

            # Skip labels mapped to None (too noisy or not useful)
            if entity_label is None:
                continue

            # Skip single-character spans (usually tokenisation artefacts)
            if len(ent.text.strip()) < 2:
                continue

            entities.append(
                Entity(
                    text=ent.text,
                    label=entity_label,
                    start=ent.start_char,
                    end=ent.end_char,
                    score=1.0,   # spaCy standard NER has no per-entity score
                    detector=self.name,
                    metadata={
                        "spacy_label": ent.label_,
                        "spacy_kb_id": ent.kb_id_ or "",
                    },
                )
            )

        return entities

    @staticmethod
    def is_available(language: str = "fr") -> bool:
        """
        Check whether a spaCy model is available for the given language.

        Useful for graceful degradation checks before running the pipeline.

        Args:
            language: ISO 639-1 code ("fr" or "en").

        Returns:
            True if spaCy is installed and a model is available.
        """
        return _load_model(language) is not None

    @staticmethod
    def available_models() -> Dict[str, Optional[str]]:
        """
        Return the name of the loaded model for each supported language,
        or None if no model is available.

        Returns:
            {"fr": "fr_core_news_lg", "en": None} — example output.
        """
        result = {}
        for lang in ("fr", "en"):
            nlp = _load_model(lang)
            result[lang] = nlp.meta.get("name") if nlp is not None else None
        return result