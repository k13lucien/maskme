Architecture: The Anonymization Engine
======================================

The MaskMe engine is built on a **Registry Pattern**, ensuring a strict separation between the orchestration logic and the transformation rules.

The Transformation Lifecycle
----------------------------

1.  **Registry Lookup**: The engine identifies the requested strategy alias (e.g., ``hash``) from the configuration.
2.  **Configuration Injection**: Parameters (like ``salt``) are dynamically injected into the strategy instance.
3.  **Streaming Pipeline**: Data is processed record-by-record to ensure a low memory footprint, even with large datasets.

Design Principles
-----------------
*   **Extensibility**: New strategies can be registered without modifying the core engine.
*   **Immutability**: The engine never modifies the source data; it always produces a new stream or file.
*   **Type Safety**: Leveraging Python type hints for configuration validation.
