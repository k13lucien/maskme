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

**Description**: Adds Gaussian noise to numeric values.

**When to use**:
- Numeric fields: ages, salaries, amounts, measurements
- Preserve statistical distributions while hiding individual values
- Differential privacy requirements

**Signature**:

.. code-block:: python

   apply(
       value: Any,
       sigma: Optional[float] = None,
       min_val: Optional[float] = None,
       max_val: Optional[float] = None,
       precision: Optional[int] = None,
       seed: Optional[Any] = None,
       epsilon: Optional[float] = None,
       sensitivity: Optional[float] = None,
       delta: float = 1e-5,
       **kwargs
   ) -> Union[float, int, Any]

**Parameters**:

- ``sigma`` (float): Standard deviation for direct Gaussian noise. Mutually exclusive with epsilon/sensitivity. Defaults to 1.0 if neither mode specified.
- ``min_val`` / ``max_val`` (float): Clipping bounds. Result clipped to [min_val, max_val].
- ``precision`` (int): Decimal places to round to (0 = return int).
- ``seed`` (Optional[Any]): Seed for reproducible noise generation. Combined with sigma and value for consistency.

**Differential Privacy Parameters** (mutually exclusive with sigma):

- ``epsilon`` (float): Privacy budget ε. Smaller = stronger privacy. Must be > 0. Requires sensitivity.
- ``sensitivity`` (float): L2-sensitivity Δf (max output change per person). Must be > 0. Requires epsilon.
- ``delta`` (float): Probability of privacy breach δ. Must be in (0, 1). Defaults to 1e-5.

**Returns**: Noised numeric value (float or int if precision=0), or original value if non-numeric

**Behavior — Direct Mode** (using sigma):

.. math::

   x' = x + \mathcal{N}(0, \sigma^2)

Quick noise for exploratory analysis without formal privacy guarantees.

**Behavior — Differential Privacy Mode** (using epsilon + sensitivity):

.. math::

   \sigma = \text{sensitivity} \times \sqrt{2 \ln(1.25 / \delta)} / \epsilon

   x' = x + \mathcal{N}(0, \sigma^2)

Guarantees (ε, δ)-differential privacy per Dwork & Roth (2014).

**Examples**:

.. code-block:: python

   from maskme.strategies import noise

   # Direct Gaussian noise (simple case)
   noise.apply(42, sigma=5)  # → ~42 (varies each call)

   # Reproducible noise with seed
   noise.apply(42, sigma=5, seed="my-seed")  # Same seed = same noise

   # Differential privacy mode (strong guarantee)
   noise.apply(
       42,
       epsilon=0.5,       # Privacy budget
       sensitivity=10,    # Max change per person
       delta=1e-5         # 0.001% breach probability
   )
   # → ~42 (calibrated noise with formal guarantee)

   # Clipping + rounding to integer
   noise.apply(
       28,
       sigma=3,
       min_val=0,
       max_val=100,
       precision=0
   )
   # → 27 (noise applied, clipped to [0,100], rounded to int)

   # Rounding to 2 decimals
   noise.apply(
       28.5,
       sigma=1.5,
       precision=2
   )
   # → 29.24

**Privacy guarantee**:
- **Direct sigma**: No formal guarantee (heuristic noise)
- **Differential Privacy** (epsilon + sensitivity): Formal (ε, δ)-DP guarantee (GDPR-friendly)

**When to use each**:

- **Direct sigma**: Quick anonymization, exploratory analysis, understood by analysts
- **Differential Privacy**: Regulatory requirements, formal privacy guarantees needed

Generalization
---------------

**Description**: Coarsens data to broader categories.

**When to use**:
- Dates (2024-03-15 → 2024 or 2024-03)
- Locations (city → state/region)
- Ages (28 → 25-30 or 20-30 bracket)
- Any hierarchical categorization

**Signature**:

.. code-block:: python

   apply(
       value: Any,
       step: Optional[Union[int, float]] = None,
       bins: Optional[List[float]] = None,
       depth: int = 1,
       method: str = "range",
       default: str = "Others",
       **kwargs
   ) -> Optional[str]

**Parameters**:

- ``step`` (Union[int, float]): Fixed step size for numeric values (e.g., 10 for age brackets). Mutually exclusive with bins.
- ``bins`` (List[float]): Custom boundary list for numeric values (e.g., [0, 18, 65]). Mutually exclusive with step.
- ``depth`` (int): For location strings (comma-separated). Number of leading parts to drop (default: 1).
- ``method`` (str): Generalization strategy:

  - ``"range"``: Numeric interval (e.g., "20-30") — default for numeric
  - ``"floor"``: Numeric floor only (e.g., "20")
  - ``"date_year"``: Year only (e.g., "2024")
  - ``"date_month"``: Year and month (e.g., "2024-03")

- ``default`` (str): Fallback value when generalization fails (default: "Others").

**Returns**: Generalized string, or None if input is None

**Behavior — Numeric with step**:

Step divides numeric values into fixed intervals.

**Examples — Numeric Generalization**:

.. code-block:: python

   from maskme.strategies import generalization

   # Age bracket with step=10
   generalization.apply(27, step=10, method="range")
   # → "20-30"

   generalization.apply(27, step=10, method="floor")
   # → "20"

   # Custom age brackets with bins
   generalization.apply(27, bins=[0, 18, 30, 50, 100], method="range")
   # → "18-30"

   generalization.apply(12, bins=[0, 18, 30, 50, 100], method="range")
   # → "0-18"

   # Out of range
   generalization.apply(10, bins=[18, 30, 50, 100], method="range")
   # → "<18"

   generalization.apply(85, bins=[0, 18, 65], method="range")
   # → ">=65"

**Behavior — Date Generalization**:

Reduces date precision to year or year+month.

**Examples — Date Generalization**:

.. code-block:: python

   # Year only
   generalization.apply("2024-03-15", method="date_year")
   # → "2024"

   # Year and month
   generalization.apply("2024-03-15", method="date_month")
   # → "2024-03"

   # Also works with datetime objects
   from datetime import datetime
   dt = datetime(2024, 3, 15)
   generalization.apply(dt, method="date_year")
   # → "2024"

**Behavior — Location Generalization**:

Removes leading parts from comma-separated location strings (most specific → less specific).

**Examples — Location Generalization**:

.. code-block:: python

   # Remove 1 part (city → region)
   generalization.apply("Ouagadougou, Kadiogo, Centre", depth=1)
   # → "Kadiogo, Centre"

   # Remove 2 parts (city+region → country)
   generalization.apply("Ouagadougou, Kadiogo, Centre", depth=2)
   # → "Centre"

**Privacy guarantee**: K-anonymity-like (groups become indistinguishable)

**Utility trade-off**: Coarsening reduces utility but preserves categorical/aggregate analysis

**Common patterns**:

.. code-block:: python

   # Healthcare: age + year generalization
   "age": {"strategy": "generalize", "step": 5, "method": "range"},
   "visit_date": {"strategy": "generalize", "method": "date_year"},

   # E-Commerce: postal code simplification
   "postal_code": {"strategy": "generalize", "bins": [0, 10000, 20000, 30000, 100000], "method": "floor"},

   # Public health: location generalization
   "location": {"strategy": "generalize", "depth": 1}

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
