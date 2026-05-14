Anonymization Strategies
========================

MaskMe provides six built-in strategies. This reference describes each one technically, with parameters and examples.

Keep
----

**Description**: Leaves the value unchanged.

**When to use**:
- Non-sensitive fields (categories, aggregates)
- Public information (country, product type)
- Fields needed for analysis

**Signature**:

.. code-block:: python

   apply(value: Any, **kwargs) -> Any

**Parameters**: None (accepts **kwargs for interface consistency)

**Returns**: The value unchanged

**Examples**:

.. code-block:: python

   from maskme.strategies import noop

   noop.apply("US")  # → "US"
   noop.apply(42)    # → 42

**Privacy guarantee**: None (data is unchanged)

Drop
----

**Description**: Signals the engine to remove the field entirely.

**When to use**:
- Internal identifiers (user_id, record_id)
- Sensitive fields not needed in output
- Redundant information

**Signature**:

.. code-block:: python

   apply(value: Any, **kwargs) -> str

**Parameters**: None

**Returns**: ``"__DROP__"`` (special sentinel; engine removes the field)

**Examples**:

.. code-block:: python

   from maskme.strategies import drop

   drop.apply(12345)  # → "__DROP__"
   # Engine will remove this field from the record

**Privacy guarantee**: Eliminates the field → zero information leakage for that field

Hash
----

**Description**: Converts a value into a fixed-length cryptographic hash.

**When to use**:
- Email addresses, usernames
- Customer/patient IDs (when consistency matters)
- Need one-way, irreversible transformation

**Signature**:

.. code-block:: python

   apply(value: Any, salt: str = "", algo: str = "sha256", **kwargs) -> str

**Parameters**:

- ``value`` (Any): Value to hash. If None, returns "".
- ``salt`` (str): Optional salt appended before hashing (default: "").
- ``algo`` (str): Hashing algorithm. Supported: "sha256", "sha512", "blake2b", "md5" (default: "sha256").

**Returns**: Hexadecimal digest string

**Behavior**:

- Deterministic: Same input + salt → same output
- Fast to compute, impossible to reverse
- Unsupported algorithm → warning and fallback to sha256

**Examples**:

.. code-block:: python

   from maskme.strategies import hashing

   # Basic hash
   hashing.apply("alice@example.com")
   # → "d6d5d09f12b3f0f1a8a2c1e3b5e7d9f2"

   # Same input, different salt → different hash
   hashing.apply("alice@example.com", salt="salt-1")
   # → "a1b2c3d4e5f6..."
   hashing.apply("alice@example.com", salt="salt-2")
   # → "9z8y7x6w5v4u..."

   # SHA-512 (stronger, longer output)
   hashing.apply("alice@example.com", algo="sha512")
   # → "0e5e7c5b3a2d1f0e..."

**Privacy guarantee**: Cryptographic strength (computational infeasibility to reverse)

**Production considerations**:
- Always use a salt (random, organization-specific)
- Store salt securely; don't hardcode in rules files
- SHA-256 is sufficient for most cases; SHA-512 for extra margin
- Same salt for all records enables record linkage if needed

Redact
------

**Description**: Replaces characters with a placeholder while preserving original length.

**When to use**:
- Phone numbers, credit cards (keep some digits for context)
- Postal codes (keep prefix)
- Any value where length or pattern matters

**Signature**:

.. code-block:: python

   apply(
       value: Any,
       char: str = "*",
       keep_start: int = 0,
       keep_end: int = 0,
       **kwargs
   ) -> str

**Parameters**:

- ``value`` (Any): Value to redact. Converted to str.
- ``char`` (str): Single character used for redaction (default: "*"). Must be exactly one character.
- ``keep_start`` (int): Characters visible at the beginning (default: 0).
- ``keep_end`` (int): Characters visible at the end (default: 0).

**Returns**: Redacted string, same length as input

**Behavior**:

- If ``keep_start + keep_end >= length``, entire value is redacted
- Otherwise: ``[visible_start] + [redacted_part] + [visible_end]``

**Validation**:
- Raises ValueError if char is not exactly one character
- Raises ValueError if keep_start or keep_end are negative

**Examples**:

.. code-block:: python

   from maskme.strategies import redaction

   # Complete redaction
   redaction.apply("secret-password")
   # → "****-*---------"  (length preserved)

   # Last 4 digits (credit card pattern)
   redaction.apply("4532-1234-5678-9012", keep_end=4)
   # → "****-****-****-9012"

   # First and last
   redaction.apply("alice@example.com", keep_start=1, keep_end=3)
   # → "a*****m.com"

   # Custom redaction character
   redaction.apply("555-1234", char="X", keep_end=4)
   # → "XXX-1234"

**Privacy guarantee**: Pattern-preserving obfuscation (some information visible; weak privacy on its own)

**Use with caution**:
- Visible characters (first/last 4 digits) may leak information
- Combine with other strategies (e.g., hash + redact) for stronger privacy
- For credit cards, PCI-DSS recommends showing only last 4 digits + redacting the rest

Noise
-----

**Description**: Adds statistical noise to numeric values.

**When to use**:
- Numeric fields: ages, salaries, amounts, measurements
- Preserve statistical distributions while hiding individual values
- Differential privacy requirements

**Signature**:

.. code-block:: python

   apply(
       value: Any,
       sigma: Optional[float] = None,
       scale: Optional[float] = None,
       epsilon: Optional[float] = None,
       delta: Optional[float] = None,
       sensitivity: Optional[float] = None,
       min_val: Optional[float] = None,
       max_val: Optional[float] = None,
       precision: Optional[int] = None,
       **kwargs
   ) -> float

**Parameters (Laplace Noise)**:

- ``scale`` (float): Laplace distribution scale parameter. Noise ~ Laplace(0, scale).

**Parameters (Differential Privacy — Gaussian)**:

- ``epsilon`` (float): Privacy budget. Smaller = more private. Must be > 0.
- ``delta`` (float): Probability of failure. Typically 1e-5. Must be in (0, 1).
- ``sensitivity`` (float): Maximum change in output when one individual's data changes. Must be > 0.

**Optional Parameters (both modes)**:

- ``min_val`` / ``max_val`` (float): Clipping bounds. Result is clipped to [min_val, max_val].
- ``precision`` (int): Decimal places to round to (default: no rounding).

**Returns**: Noised value (float)

**Behavior — Laplace Noise**:

.. math::

   x' = x + \text{Laplace}(0, \text{scale})

Each value gets independent random noise. Good for exploratory analysis.

**Behavior — Differential Privacy (Gaussian)**:

.. math::

   \sigma = \text{sensitivity} \times \sqrt{2 \ln(1.25 / \delta)} / \epsilon

   x' = x + \mathcal{N}(0, \sigma^2)

Noise calibrated to guarantee (ε, δ)-differential privacy.

**Examples**:

.. code-block:: python

   from maskme.strategies import noise

   # Laplace noise (simple case)
   noise.apply(42, scale=5)  # → ~42 (varies each call)

   # Differential privacy (strong guarantee)
   noise.apply(
       42,
       epsilon=0.5,      # Moderate privacy
       delta=1e-5,       # 0.001% breach probability
       sensitivity=10    # Max change per person
   )
   # → ~42 (calibrated noise)

   # Clipping + precision
   noise.apply(
       28,
       scale=3,
       min_val=0,
       max_val=100,
       precision=1
   )
   # → 27.3 (noise applied, clipped, rounded to 1 decimal)

**Privacy guarantee**:
- **Laplace**: No formal guarantee (heuristic noise)
- **Differential Privacy**: Formal (ε, δ)-DP guarantee (GDPR-friendly)

**When to choose each**:

- **Laplace**: Quick exploratory analysis, understood by analysts
- **Differential Privacy**: Regulatory requirements, strong privacy guarantees needed

Generalization
---------------

**Description**: Coarsens data to broader categories.

**When to use**:
- Dates (2024-03-15 → 2024)
- Locations (city → state)
- Ages (28 → [25, 35])
- Any hierarchical categorization

**Signature**:

.. code-block:: python

   apply(
       value: Any,
       method: str = "keep_prefix",
       level: Optional[str] = None,
       ranges: Optional[List[List[float]]] = None,
       prefix_length: Optional[int] = None,
       **kwargs
   ) -> Any

**Parameters**:

- ``method`` (str): Generalization method. Supported: "date", "numeric_range", "keep_prefix".
- ``level`` (str): For date method. Options: "year", "month", "day".
- ``ranges`` (List[List[float]]): For numeric_range. List of [min, max] boundaries.
- ``prefix_length`` (int): For keep_prefix. Number of characters to keep.

**Examples — Date Generalization**:

.. code-block:: python

   from maskme.strategies import generalization

   # Year only
   generalization.apply("2024-03-15", method="date", level="year")
   # → "2024"

   # Year and month
   generalization.apply("2024-03-15", method="date", level="month")
   # → "2024-03"

   # Full date (no generalization)
   generalization.apply("2024-03-15", method="date", level="day")
   # → "2024-03-15"

**Examples — Numeric Range**:

.. code-block:: python

   # Age brackets
   ranges = [[0, 18], [18, 30], [30, 50], [50, 100]]
   
   generalization.apply(12, method="numeric_range", ranges=ranges)
   # → [0, 18]
   
   generalization.apply(28, method="numeric_range", ranges=ranges)
   # → [18, 30]

**Examples — Prefix Keeping**:

.. code-block:: python

   # Keep first 2 chars (postal code)
   generalization.apply("12345", method="keep_prefix", prefix_length=2)
   # → "12"

   # Keep first 5 chars (ZIP+4)
   generalization.apply("12345-6789", method="keep_prefix", prefix_length=5)
   # → "12345"

**Privacy guarantee**: K-anonymity-like (groups become indistinguishable)

**Utility trade-off**: Coarsening reduces utility but preserves categorical/aggregate analysis

**Note**: Generalization is often combined with other strategies (e.g., hash + generalize) for multi-layered privacy.

No-op
-----

**Description**: Explicitly does nothing (identical to Keep).

**When to use**:
- Default strategy when you want to be explicit
- Marking fields as "no transformation needed" for code clarity

**Signature**:

.. code-block:: python

   apply(value: Any, **kwargs) -> Any

**Returns**: The value unchanged

**Examples**:

.. code-block:: python

   from maskme.strategies import noop

   noop.apply("public-data")  # → "public-data"

Strategy Selection Guide
-------------------------

Decision tree for choosing strategies:

.. code-block:: text

   Is the field sensitive?
   ├─ NO
   │  └─ keep or noop
   ├─ YES, is it an identifier (user_id, email, etc.)?
   │  ├─ Yes, need record linkage? 
   │  │  └─ Yes → hash (with salt)
   │  │  └─ No → drop
   │  ├─ No, is it numeric?
   │  │  └─ Yes → noise or generalization
   │  │  └─ No, need pattern visible?
   │  │     └─ Yes → redact
   │  │     └─ No → hash or drop
   │  ├─ No, is it categorical?
   │  │  └─ Yes → generalization
   │  │  └─ No → redact or noise

Privacy-Utility Trade-offs
---------------------------

.. list-table::
   :header-rows: 1

   * - Strategy
     - Privacy
     - Utility
     - Best For
   * - Keep
     - None
     - Maximum
     - Non-sensitive fields
   * - Drop
     - Maximum
     - Zero
     - Unnecessary sensitive fields
   * - Hash
     - High
     - Medium
     - Identifiers, linkage
   * - Redact
     - Medium
     - Medium
     - Partial patterns (last 4 digits)
   * - Noise
     - Medium-High
     - Medium-High
     - Numeric, distributions matter
   * - Generalize
     - Medium
     - Medium-High
     - Hierarchical data (dates, locations)

Combining Strategies
--------------------

For sensitive fields, layer strategies:

**Example: Doubly-anonymized email**

.. code-block:: json

   "email": {
     "strategy": "hash",
     "salt": "my-secret-salt"
   }

**Example: Partially-visible, hashed phone**

.. code-block:: json

   "phone": {
     "strategy": "redact",
     "keep_end": 4
   }

**Example: Age bracket with noise**

.. code-block:: json

   "age": {
     "strategy": "noise",
     "scale": 2,
     "precision": 0
   }

You can also apply multiple strategies in sequence via Python API (see how-to guides).
