"""
maskme.ner.detectors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Entity detector implementations for the unstructured text pipeline.

Each detector satisfies the Detector Protocol defined in ner/base.py.
To add a new detector, create a new file here and register it in
ner/__init__.py under DETECTORS.

Available detectors:
    SpacyDetector  — contextual NER (names, locations, organisations...)
"""

from maskme.ner.detectors.spacy_detector import SpacyDetector

__all__ = ["SpacyDetector"]