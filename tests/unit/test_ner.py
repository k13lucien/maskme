"""
Unit tests for maskme.ner — Entity, EntityLabel, resolve_spans, PipelineResult,
_replace_spans, mask(), language detection, and SpacyDetector graceful degradation.

All tests run without spaCy or langdetect installed.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from maskme.ner import Entity, EntityLabel, PipelineResult, resolve_spans
from maskme.ner.detectors.spacy_detector import SpacyDetector
from maskme.ner.language import SUPPORTED_LANGUAGES, detect, detect_segments, is_english, is_french
from maskme.ner.pipeline import _empty_stats, _replace_spans, mask


# ===================================================================
# Entity
# ===================================================================

class TestEntityOverlaps:
    """Entity.overlaps() — span intersection detection."""

    def test_partial_overlap(self):
        a = Entity("Alice", EntityLabel.PERSON, 0, 5)
        b = Entity("lice", EntityLabel.PERSON, 1, 5)
        assert a.overlaps(b)
        assert b.overlaps(a)

    def test_identical_span(self):
        a = Entity("Alice", EntityLabel.PERSON, 0, 5)
        b = Entity("Alice", EntityLabel.PERSON, 0, 5)
        assert a.overlaps(b)

    def test_contains(self):
        a = Entity("Alice Martin", EntityLabel.PERSON, 0, 12)
        b = Entity("Alice", EntityLabel.PERSON, 0, 5)
        assert a.overlaps(b)
        assert b.overlaps(a)

    def test_adjacent_no_overlap(self):
        a = Entity("Alice", EntityLabel.PERSON, 0, 5)
        b = Entity("habite", EntityLabel.CUSTOM, 5, 11)
        assert not a.overlaps(b)
        assert not b.overlaps(a)

    def test_disjoint(self):
        a = Entity("Alice", EntityLabel.PERSON, 0, 5)
        b = Entity("Paris", EntityLabel.LOCATION, 15, 20)
        assert not a.overlaps(b)


class TestEntityContains:
    """Entity.contains() — full containment check."""

    def test_fully_contains(self):
        a = Entity("Alice Martin", EntityLabel.PERSON, 0, 12)
        b = Entity("Alice", EntityLabel.PERSON, 0, 5)
        assert a.contains(b)
        assert not b.contains(a)

    def test_equal_spans(self):
        a = Entity("Alice", EntityLabel.PERSON, 0, 5)
        b = Entity("Alice", EntityLabel.PERSON, 0, 5)
        assert a.contains(b)
        assert b.contains(a)

    def test_disjoint(self):
        a = Entity("Alice", EntityLabel.PERSON, 0, 5)
        b = Entity("Paris", EntityLabel.LOCATION, 15, 20)
        assert not a.contains(b)

    def test_partial_overlap_not_contained(self):
        a = Entity("Alice", EntityLabel.PERSON, 0, 5)
        b = Entity("lice Mart", EntityLabel.PERSON, 1, 9)
        assert not a.contains(b)
        assert not b.contains(a)


class TestEntityLen:
    """Entity.__len__() — span character length."""

    def test_length(self):
        e = Entity("Alice", EntityLabel.PERSON, 0, 5)
        assert len(e) == 5

    def test_length_single_char(self):
        e = Entity("A", EntityLabel.PERSON, 0, 1)
        assert len(e) == 1

    def test_length_empty(self):
        e = Entity("", EntityLabel.CUSTOM, 0, 0)
        assert len(e) == 0


class TestEntityRepr:
    """Entity.__repr__() — debug representation."""

    def test_repr_contains_fields(self):
        e = Entity("Alice", EntityLabel.PERSON, 0, 5, score=0.99, detector="spacy")
        r = repr(e)
        assert "Alice" in r
        assert "PERSON" in r
        assert "0" in r
        assert "5" in r
        assert "0.99" in r
        assert "spacy" in r


# ===================================================================
# EntityLabel
# ===================================================================

class TestEntityLabelValues:
    """EntityLabel enum — all values are uppercase strings."""

    def test_all_values_are_strings(self):
        for label in EntityLabel:
            assert isinstance(label.value, str)

    def test_all_values_uppercase(self):
        for label in EntityLabel:
            assert label.value == label.value.upper()

    def test_expected_count(self):
        assert len(EntityLabel) >= 10

    def test_key_members_exist(self):
        assert EntityLabel.PERSON.value == "PERSON"
        assert EntityLabel.EMAIL.value == "EMAIL"
        assert EntityLabel.PHONE.value == "PHONE"
        assert EntityLabel.LOCATION.value == "LOCATION"
        assert EntityLabel.DATE.value == "DATE"
        assert EntityLabel.ORGANISATION.value == "ORGANISATION"
        assert EntityLabel.IP_ADDRESS.value == "IP_ADDRESS"


# ===================================================================
# resolve_spans
# ===================================================================

def _entity(text, label, start, end, priority=50, score=1.0, detector=""):
    e = Entity(
        text=text,
        label=label,
        start=start,
        end=end,
        score=score,
        detector=detector,
        metadata={"priority": priority},
    )
    e.priority = priority
    return e


class TestResolveSpansEmpty:
    """resolve_spans() with empty input."""

    def test_empty_list(self):
        assert resolve_spans([]) == []


class TestResolveSpansNoOverlap:
    """Non-overlapping entities pass through unchanged."""

    def test_two_disjoint(self):
        a = _entity("Alice", EntityLabel.PERSON, 0, 5)
        b = _entity("Paris", EntityLabel.LOCATION, 15, 20)
        result = resolve_spans([a, b])
        assert result == [a, b]

    def test_sorted_by_start(self):
        a = _entity("Paris", EntityLabel.LOCATION, 15, 20)
        b = _entity("Alice", EntityLabel.PERSON, 0, 5)
        result = resolve_spans([a, b])
        assert result == [b, a]


class TestResolveSpansLongerWins:
    """When two spans overlap, the longer one wins."""

    def test_longer_span_kept(self):
        short = _entity("Alice", EntityLabel.PERSON, 0, 5, priority=50)
        long  = _entity("Alice Martin", EntityLabel.PERSON, 0, 12, priority=50)
        result = resolve_spans([short, long])
        assert result == [long]

    def test_equal_length_higher_priority_wins(self):
        low  = _entity("Alice", EntityLabel.PERSON, 0, 5, priority=30)
        high = _entity("Alice", EntityLabel.PERSON, 0, 5, priority=80)
        result = resolve_spans([low, high])
        assert result == [high]

    def test_equal_length_equal_priority_higher_score_wins(self):
        low  = _entity("Alice", EntityLabel.PERSON, 0, 5, priority=50, score=0.7)
        high = _entity("Alice", EntityLabel.PERSON, 0, 5, priority=50, score=0.95)
        result = resolve_spans([low, high])
        assert result == [high]


class TestResolveSpansContained:
    """When one span contains another, the outer wins."""

    def test_outer_kept(self):
        inner = _entity("lice", EntityLabel.PERSON, 1, 5)
        outer = _entity("Alice", EntityLabel.PERSON, 0, 5)
        result = resolve_spans([inner, outer])
        assert result == [outer]


class TestResolveSpansChain:
    """Chained overlapping spans resolve correctly."""

    def test_three_way_chain(self):
        a = _entity("Alice", EntityLabel.PERSON, 0, 5, priority=50)
        b = _entity("Alice Martin", EntityLabel.PERSON, 0, 12, priority=50)
        c = _entity("Martin", EntityLabel.PERSON, 5, 11, priority=50)
        result = resolve_spans([a, b, c])
        assert result == [b]


class TestResolveSpansAdjacent:
    """Adjacent spans (end == start) do not conflict."""

    def test_adjacent_both_kept(self):
        a = _entity("Alice", EntityLabel.PERSON, 0, 5)
        b = _entity("habite", EntityLabel.CUSTOM, 5, 11)
        result = resolve_spans([a, b])
        assert result == [a, b]


# ===================================================================
# PipelineResult
# ===================================================================

class TestPipelineResultProperties:
    """PipelineResult computed properties."""

    def test_entity_count(self):
        r = PipelineResult(
            output="[PERSON]",
            input="Alice",
            entities=[Entity("Alice", EntityLabel.PERSON, 0, 5)],
            language="fr",
        )
        assert r.entity_count == 1

    def test_entity_count_empty(self):
        r = PipelineResult(output="", input="", entities=[], language="fr")
        assert r.entity_count == 0

    def test_labels_found(self):
        r = PipelineResult(
            output="[PERSON] habite à [LOCATION].",
            input="Alice habite à Paris.",
            entities=[
                Entity("Alice", EntityLabel.PERSON, 0, 5),
                Entity("Paris", EntityLabel.LOCATION, 15, 20),
            ],
            language="fr",
        )
        assert r.labels_found == ["LOCATION", "PERSON"]

    def test_labels_found_deduplicates(self):
        r = PipelineResult(
            output="[PERSON] et [PERSON]",
            input="Alice et Bob",
            entities=[
                Entity("Alice", EntityLabel.PERSON, 0, 5),
                Entity("Bob", EntityLabel.PERSON, 8, 11),
            ],
            language="fr",
        )
        assert r.labels_found == ["PERSON"]


class TestPipelineResultAsDict:
    """PipelineResult.as_dict() serialization."""

    def test_expected_keys(self):
        r = PipelineResult(output="[PERSON]", input="Alice", entities=[], language="fr")
        d = r.as_dict()
        assert set(d.keys()) == {"input", "output", "language", "entity_count",
                                  "labels_found", "entities", "stats"}

    def test_entities_as_dicts(self):
        e = Entity("Alice", EntityLabel.PERSON, 0, 5, score=0.99, detector="spacy")
        r = PipelineResult(output="[PERSON]", input="Alice", entities=[e], language="fr")
        d = r.as_dict()
        assert len(d["entities"]) == 1
        ent = d["entities"][0]
        assert ent["text"] == "Alice"
        assert ent["label"] == "PERSON"
        assert ent["start"] == 0
        assert ent["end"] == 5
        assert ent["score"] == 0.99
        assert ent["detector"] == "spacy"


# ===================================================================
# _replace_spans
# ===================================================================

class TestReplaceSpansEmpty:
    """No entities → text unchanged."""

    def test_no_entities(self):
        assert _replace_spans("Alice habite à Paris.", []) == "Alice habite à Paris."

    def test_empty_text(self):
        assert _replace_spans("", []) == ""


class TestReplaceSpansSingle:
    """Single entity replaced by its tag."""

    def test_single_person(self):
        entities = [Entity("Alice", EntityLabel.PERSON, 0, 5)]
        assert _replace_spans("Alice", entities) == "[PERSON]"

    def test_single_location(self):
        entities = [Entity("Paris", EntityLabel.LOCATION, 15, 20)]
        assert _replace_spans("Alice habite à Paris.", entities) == "Alice habite à [LOCATION]."


class TestReplaceSpansMultiple:
    """Multiple non-overlapping entities all replaced."""

    def test_two_labels(self):
        entities = [
            Entity("Alice", EntityLabel.PERSON, 0, 5),
            Entity("Paris", EntityLabel.LOCATION, 15, 20),
        ]
        result = _replace_spans("Alice habite à Paris.", entities)
        assert result == "[PERSON] habite à [LOCATION]."

    def test_adjacent_entities(self):
        entities = [
            Entity("Alice", EntityLabel.PERSON, 0, 5),
            Entity("Martin", EntityLabel.PERSON, 6, 12),
        ]
        result = _replace_spans("Alice Martin", entities)
        assert result == "[PERSON] [PERSON]"


class TestReplaceSpansPosition:
    """Entity at start, end, and middle of text."""

    def test_start(self):
        entities = [Entity("Alice", EntityLabel.PERSON, 0, 5)]
        assert _replace_spans("Alice habite.", entities) == "[PERSON] habite."

    def test_end(self):
        entities = [Entity("Paris", EntityLabel.LOCATION, 11, 16)]
        assert _replace_spans("J'habite à Paris.", entities) == "J'habite à [LOCATION]."

    def test_surrounded(self):
        entities = [Entity("Paris", EntityLabel.LOCATION, 2, 7)]
        assert _replace_spans("À Paris il fait beau.", entities) == "À [LOCATION] il fait beau."


# ===================================================================
# mask() — single entry point
# ===================================================================

class TestMaskSingle:
    """mask() with a single string."""

    def test_returns_pipeline_result(self):
        result = mask("Alice habite à Paris.")
        assert isinstance(result, PipelineResult)

    def test_input_preserved(self):
        result = mask("Alice habite à Paris.")
        assert result.input == "Alice habite à Paris."

    def test_output_equals_input_when_no_spacy(self):
        result = mask("Alice habite à Paris.")
        assert result.output == "Alice habite à Paris."

    def test_language_default_fr(self):
        result = mask("Alice habite à Paris.")
        assert result.language == "fr"

    def test_language_override(self):
        result = mask("John lives in London.", language="en")
        assert result.language == "en"


class TestMaskEmpty:
    """mask() with empty or whitespace-only text."""

    @pytest.mark.parametrize("text", ["", "   ", "\n\t"])
    def test_empty_text_returns_empty_result(self, text):
        result = mask(text)
        assert result.input == text
        assert result.output == text
        assert result.entity_count == 0

    def test_empty_stats(self):
        result = mask("")
        assert result.stats["n_entities_raw"] == 0
        assert result.stats["n_entities_resolved"] == 0
        assert result.stats["detectors_run"] == []
        assert result.stats["processing_ms"] == 0.0


class TestMaskBatch:
    """mask() with a list of strings."""

    def test_returns_list(self):
        results = mask(["Alice habite à Paris.", "John lives in London."])
        assert isinstance(results, list)
        assert len(results) == 2

    def test_each_is_pipeline_result(self):
        results = mask(["a", "b"])
        for r in results:
            assert isinstance(r, PipelineResult)

    def test_empty_list(self):
        assert mask([]) == []


class TestMaskStats:
    """mask() stats structure."""

    def test_stats_keys(self):
        result = mask("Alice habite à Paris.")
        expected_keys = {"n_entities_raw", "n_entities_resolved",
                         "detectors_run", "processing_ms"}
        assert set(result.stats.keys()) == expected_keys

    def test_no_spacy_detectors_run_empty(self):
        result = mask("Alice habite à Paris.")
        assert result.stats["detectors_run"] == []

    def test_processing_ms_is_float(self):
        result = mask("Alice habite à Paris.")
        assert isinstance(result.stats["processing_ms"], float)


# ===================================================================
# language — detect (without langdetect)
# ===================================================================

class TestDetectFallback:
    """detect() without langdetect always returns the default."""

    def test_returns_default_fr(self):
        assert detect("Le patient présente une fièvre.") == "fr"

    def test_returns_default_en(self):
        assert detect("The patient has a fever.", default="en") == "en"

    def test_supported_languages(self):
        assert "fr" in SUPPORTED_LANGUAGES
        assert "en" in SUPPORTED_LANGUAGES


class TestDetectShortText:
    """detect() with text shorter than min_chars returns default."""

    def test_short_text_fallback(self):
        assert detect("abc") == "fr"

    def test_short_text_custom_default(self):
        assert detect("abc", default="en") == "en"


class TestDetectEmpty:
    """detect() with empty text returns default."""

    def test_empty_string(self):
        assert detect("") == "fr"

    def test_whitespace(self):
        assert detect("   ") == "fr"


class TestDetectSegments:
    """detect_segments() without langdetect returns default."""

    def test_fallback_without_langdetect(self):
        assert detect_segments("Long text ") == "fr"

    def test_custom_default(self):
        assert detect_segments("Long text " * 50, default="en") == "en"

    def test_short_text_fallback(self):
        assert detect_segments("abc") == "fr"


class TestIsFrenchIsEnglish:
    """is_french() / is_english() without langdetect."""

    def test_is_french_default(self):
        assert is_french("Le patient présente une fièvre.")

    def test_is_english_default(self):
        assert not is_english("Le patient présente une fièvre.")

    def test_is_english_with_default_en(self):
        assert is_english("The patient has a fever.", default="en")


# ===================================================================
# SpacyDetector (without spaCy)
# ===================================================================

class TestSpacyDetectorUnavailable:
    """SpacyDetector graceful degradation when spaCy is not installed."""

    def test_is_available_fr(self):
        assert not SpacyDetector.is_available("fr")

    def test_is_available_en(self):
        assert not SpacyDetector.is_available("en")

    def test_detect_returns_empty(self):
        detector = SpacyDetector()
        assert detector.detect("Alice habite à Paris.") == []

    def test_detect_empty_text(self):
        detector = SpacyDetector()
        assert detector.detect("") == []

    def test_available_models(self):
        models = SpacyDetector.available_models()
        assert models == {"fr": None, "en": None}


# ===================================================================
# Detector Protocol
# ===================================================================

class TestSpacyDetectorProtocol:
    """SpacyDetector satisfies the Detector Protocol."""

    def test_is_detector(self):
        from maskme.ner import Detector
        assert isinstance(SpacyDetector(), Detector)

    def test_has_required_attributes(self):
        d = SpacyDetector()
        assert hasattr(d, "name")
        assert hasattr(d, "priority")
        assert hasattr(d, "detect")
        assert isinstance(d.name, str)
        assert isinstance(d.priority, (int, float))
