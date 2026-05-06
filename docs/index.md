# MaskMe: Data Privacy & Anonymization Framework

Welcome to **MaskMe**, a professional framework designed for secure data anonymization and privacy risk analysis.

MaskMe allows Data Engineers and Researchers to transform sensitive datasets into privacy-compliant versions while maintaining data utility for statistical analysis.

## Core Features
*   **Plug-and-play Strategies**: 6 built-in anonymization methods.
*   **Agnostic I/O**: Support for CSV, JSON, and JSONL.
*   **Extensible Registry**: Easily add your own custom strategies.
*   **CI/CD Ready**: Integrated with GitHub Actions for automated quality assurance.

## Installation
```bash
pip install maskme
```

## Quick Start

```bash
# Anonymize a CSV file using a config file
maskme mask input.csv --config rules.yaml --output clean_data.csv
```

---

### 2. Architecture du Moteur (`docs/engine.md`)

# Architecture: The Anonymization Engine

The MaskMe engine is built on a **Registry Pattern**, ensuring a strict separation between the orchestration logic and the transformation rules.

## The Transformation Lifecycle

1.  **Registry Lookup**: The engine identifies the requested strategy alias (e.g., `hash`) from the configuration.
2.  **Configuration Injection**: Parameters (like `salt`) are dynamically injected into the strategy instance.
3.  **Streaming Pipeline**: Data is processed record-by-record to ensure a low memory footprint, even with large datasets.

## Design Principles
*   **Extensibility**: New strategies can be registered without modifying the core engine.
*   **Immutability**: The engine never modifies the source data; it always produces a new stream or file.
*   **Type Safety**: Leveraging Python type hints and Pydantic (upcoming) for configuration validation.