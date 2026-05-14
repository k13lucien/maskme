Architecture: The Anonymization Engine
======================================

Understanding MaskMe's design helps you use it effectively and extend it for custom needs.

Design Principles
-----------------

**Modularity**: Each component (engine, strategies, I/O handlers, analytics) is independent.

**Composability**: Mix strategies, formats, and analytics as needed.

**Simplicity**: One mental model works for CLI, Python API, and custom extensions.

**Streaming**: Process data record-by-record to handle datasets larger than RAM.

**Observability**: Measure privacy formally; don't guess.

**Extensibility**: Add custom strategies or I/O handlers without modifying core code.

High-Level Overview
--------------------

.. code-block:: text

   Input Data (CSV/JSON/JSONL)
          ↓
   I/O Handler (parse records)
          ↓
   Engine (apply rules + strategies)
          ↓
   Output Data (CSV/JSON/JSONL)
          ↓
   Analytics (measure privacy)

The Engine: Core Anonymization Logic
-------------------------------------

The ``MaskMe`` engine is the heart of MaskMe. It:

1. Receives a rules dict (e.g., ``{"email": "hash", "id": "drop"}``)
2. For each record, resolves strategies and applies transformations
3. Streams output record-by-record (memory efficient)

**Workflow for a single record**:

.. code-block:: text

   Input Record: {"id": 1, "email": "alice@example.com", "name": "Alice"}

   For each rule in rules dict:
     ├─ Rule: "id" → "drop"
     │  └─ Apply drop strategy → "__DROP__"
     │     (Signal: remove this field)
     │
     ├─ Rule: "email" → "hash"
     │  └─ Apply hash strategy → "d6d5d09f12b3f0f1a..."
     │     (Update record)
     │
     └─ Rule: "name" → "keep"
        └─ Apply keep strategy → "Alice"
           (No change)

   Output Record: {"email": "d6d5d09f12b3f0f1a...", "name": "Alice"}

**Key insight**: Rules operate on **paths** (e.g., ``user.email`` for nested dicts).

Path Resolution
~~~~~~~~~~~~~~~

MaskMe uses dot notation for nested fields:

.. code-block:: python

   record = {
       "user": {
           "profile": {
               "email": "alice@example.com"
           }
       }
   }

   # Rule path: "user.profile.email"
   # MaskMe navigates: record["user"]["profile"]["email"]

This is handled by the ``navigation`` module (``get_nested``, ``set_nested``, ``delete_nested``).

Strategy Resolution
~~~~~~~~~~~~~~~~~~~

Rules can be:

**Simple (string strategy name)**:

.. code-block:: json

   "email": "hash"

**Parameterized (dict with strategy + params)**:

.. code-block:: json

   "email": {
     "strategy": "hash",
     "algo": "sha512",
     "salt": "my-salt"
   }

The engine resolves this and calls:

.. code-block:: python

   strategies["hash"](value, algo="sha512", salt="my-salt")

**Registry Pattern**:

Strategies are stored in a dict ``STRATEGIES``:

.. code-block:: python

   STRATEGIES = {
       "hash": hashing.apply,
       "redact": redaction.apply,
       "keep": noop.apply,
       "drop": drop.apply,
       "noise": noise.apply,
       "generalize": generalization.apply,
   }

This makes it easy to:
- Look up strategies by name
- Register custom strategies (add to the dict)
- Mock strategies for testing

I/O Handlers: Format Abstraction
--------------------------------

MaskMe works with multiple formats (CSV, JSON, JSONL) using a consistent abstraction.

**I/O Handler Interface**:

.. code-block:: python

   class FormatHandler(ABC):
       def read(self, file_path: str) -> Generator[Dict]:
           """Read file, yield records as dicts."""
           
       def write(self, records: Iterable[Dict], file_path: str):
           """Write records to file."""

**Implementations**:

- **CSVHandler**: Reads CSV → dicts, writes dicts → CSV
- **JSONHandler**: Reads JSON list → dicts, writes dicts → JSON array
- **JSONLHandler**: Reads JSONL (one record per line) → dicts, writes JSONL

**Key design**: All handlers return/accept records as dicts. The engine doesn't care about format.

**Example**:

.. code-block:: text

   customers.csv (CSV format)
        ↓
   CSVHandler.read() → [{"id": 1, "name": "Alice"}, ...]
        ↓
   Engine.mask(records) → [{"name": "Alice"}, ...]  (anonymized)
        ↓
   CSVHandler.write(records) → customers_masked.csv

The engine logic is identical whether you use CSV, JSON, or JSONL.

Streaming Architecture
~~~~~~~~~~~~~~~~~~~~~~

Both I/O handlers and the engine stream data:

.. code-block:: python

   # CSVHandler.read() is a generator
   for record in handler.read("large_file.csv"):  # One record at a time
       # Process record
       pass

   # Engine.mask() is a generator
   for anonymized_record in masker.mask(records):  # One at a time
       # Write or process
       pass

**Benefit**: Handle multi-GB files without loading everything into RAM.

The CLI: User-Friendly Interface
--------------------------------

The CLI wraps the engine and I/O handlers:

.. code-block:: bash

   maskme --rules rules.json --input data.csv --output masked.csv

**Steps**:

1. **Parse rules**: Load and validate ``rules.json``
2. **Detect format**: Infer CSV/JSON/JSONL from file extensions
3. **Get handlers**: Instantiate appropriate I/O handler
4. **Initialize engine**: Create MaskMe with rules
5. **Stream**: Read records → mask → write records

**Pseudo-code**:

.. code-block:: python

   def main(rules_path, input_path, output_path):
       rules = load_rules(rules_path)
       fmt = detect_format(input_path, output_path)
       
       handler = get_handler(fmt)
       masker = MaskMe(rules)
       
       input_records = handler.read(input_path)
       masked_records = masker.mask(input_records)
       handler.write(masked_records, output_path)

Analytics Module
----------------

After anonymization, measure privacy:

**Metrics computed**:

- **K-anonymity**: Minimum group size for quasi-identifiers
- **L-diversity**: Diversity of sensitive attributes within groups
- **T-closeness**: Distance between masked and original distributions
- **Information loss**: Aggregate utility metrics

**Architecture**:

.. code-block:: python

   # Metric classes (compute.py)
   class KAnonymity:
       def compute(records, quasi_identifiers) -> int
   
   class LDiversity:
       def compute(records, quasi_identifiers, sensitive) -> float

   # Results aggregation (base.py)
   class AnalyticResult:
       name: str
       passed: bool
       details: Dict
       charts: List[Chart]

   # Reporting (report.py)
   def generate(results, output_path, dataset_info):
       # Generates HTML report with charts and summaries

**Usage flow**:

.. code-block:: text

   Original Records + Masked Records
          ↓
   Compute K-anonymity, L-diversity, etc.
          ↓
   Create AnalyticResult objects
          ↓
   Generate HTML report
          ↓
   Privacy report (human-readable)

Design Patterns Used
---------------------

**Registry Pattern**:

Strategies are registered in a dict, enabling:
- Dynamic strategy lookup
- Easy custom strategy registration
- Dependency injection for testing

**Strategy Pattern**:

Each strategy is a callable with the same interface:

.. code-block:: python

   def apply(value, **kwargs) -> Any

This enables:
- Uniform treatment across strategies
- Easy swapping/composition
- Clear contracts

**Factory Pattern**:

``get_handler(format_name)`` returns the appropriate handler:

.. code-block:: python

   def get_handler(fmt: str) -> FormatHandler:
       handler_class = IO_HANDLERS[fmt]
       return handler_class()

**Generator Pattern**:

Readers and the engine use generators for memory efficiency:

.. code-block:: python

   def read(file) -> Generator[Dict]:
       for line in file:
           yield parse(line)

   def mask(records) -> Generator[Dict]:
       for record in records:
           yield process(record)

Extension Points
----------------

To extend MaskMe:

**1. Add a Custom Strategy**:

.. code-block:: python

   def my_strategy(value, **kwargs):
       return transform(value)

   masker.strategies["my_strategy"] = my_strategy

**2. Add a Custom I/O Handler**:

.. code-block:: python

   class MyFormatHandler(FormatHandler):
       def read(self, file_path):
           # Yield dicts
       
       def write(self, records, file_path):
           # Write dicts

   IO_HANDLERS["myformat"] = MyFormatHandler

**3. Add a Custom Analytic**:

.. code-block:: python

   class MyAnalytic:
       def compute(self, records):
           return AnalyticResult(...)

**4. Subclass the Engine**:

.. code-block:: python

   class MyMaskMe(MaskMe):
       def _process_record(self, record):
           # Custom pre/post-processing
           return super()._process_record(record)

Data Flow Diagrams
------------------

**CLI Flow**:

.. code-block:: text

   User Input (rules.json, data.csv)
            ↓
   CLI Parser
            ↓
   Load Rules & Detect Format
            ↓
   I/O Handler: Read CSV
            ↓
   Engine: Apply Strategies (streaming)
            ↓
   I/O Handler: Write CSV
            ↓
   Progress Logging
            ↓
   Output (masked.csv)

**Python API Flow**:

.. code-block:: text

   User Code
            ↓
   Load Data (any way)
            ↓
   Create MaskMe(rules)
            ↓
   Call masker.mask(records)
            ↓
   Process Anonymized Records
            ↓
   User handles I/O

**Analytics Flow**:

.. code-block:: text

   Original + Masked Records
            ↓
   Compute Metrics (K-anon, L-div, etc.)
            ↓
   AnalyticResult Objects
            ↓
   Generate Report (HTML)
            ↓
   Privacy Report

Performance Characteristics
----------------------------

**Time Complexity**:

- Per record: O(number of rules) with O(1) average strategy execution
- Total: O(n × m) where n = records, m = rules

**Space Complexity**:

- Streaming: O(1) per record (constant memory during processing)
- Rules + strategies: O(m) where m = number of rules
- Output buffering: O(k) where k = write buffer size (typically small)

**Large-file handling**:

- MaskMe handles multi-GB files efficiently
- No need to load entire dataset into RAM
- Bottleneck is typically I/O, not processing

Deployment Considerations
-------------------------

**CLI Deployment**:

- Package as entry point (poetry, setuptools)
- Use environment variables for sensitive config (salt, API keys)
- Log progress for long-running jobs
- Add dry-run flag (``--limit``) for testing

**Python API Deployment**:

- Import as library in data pipelines
- Handle errors gracefully (invalid rules, bad data)
- Use async/threading for parallelization (outside MaskMe)
- Cache rules to avoid reloading

**Analytics Deployment**:

- Run separately after anonymization
- Store HTML reports for audit trails
- Alert if privacy metrics fail thresholds
- Version reports with anonymization batch

Security Considerations
-----------------------

**Salt Management**:

- Salt should be random and organization-specific
- Store in secure configuration (not in rules files)
- Different salts for different datasets (optional)
- Rotate salts periodically (new salt = new anonymization)

**Error Messages**:

- Don't leak sensitive data in error messages
- Validate rules before processing
- Log errors securely (no PII in logs)

**Input Validation**:

- Validate rules structure
- Check file permissions before reading/writing
- Validate CSV/JSON structure early

**Access Control**:

- Limit who can write custom strategies
- Audit rules file changes
- Require approval for rule changes

Next Steps
----------

- :doc:`../tutorials/getting-started` — Learn by example
- :doc:`../reference/strategies` — Understand each strategy in detail
- :doc:`../how-to/custom-strategy` — Extend MaskMe with custom logic
