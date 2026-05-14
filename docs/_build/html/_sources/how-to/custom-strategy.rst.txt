How to Create a Custom Strategy
================================

MaskMe is extensible. If none of the built-in strategies fit your needs, you can create a custom strategy in minutes.

When to Create a Custom Strategy
---------------------------------

- Domain-specific transformations (medical codes, financial formats)
- Industry-specific rules (NACE codes, zip code hierarchies)
- Multi-field dependencies (redact based on another field's value)
- Compliance rules (e.g., mask if classification is "confidential")

Example: You need to anonymize medical diagnoses using a custom grouping hierarchy instead of hashing.

Anatomy of a Strategy
---------------------

Every MaskMe strategy is a simple Python function:

.. code-block:: python

   def apply(value, **kwargs):
       """
       Transform a value.
       
       Args:
           value: The value to transform
           **kwargs: Optional parameters (strategy-specific)
       
       Returns:
           Transformed value, or "__DROP__" to remove the field
       """
       # Your transformation logic
       return transformed_value

**Signature requirements**:

1. Function name: ``apply``
2. First parameter: ``value`` (the data to transform)
3. Accepts ``**kwargs`` (for consistency with other strategies)
4. Returns: transformed value (any type) or the special string ``"__DROP__"``

Example 1: Simple Redaction with Domain Logic
----------------------------------------------

Let's say you have medical diagnosis codes (ICD-10) and want to keep only the first character (broader category).

**File: custom_strategies/icd_generalize.py**

.. code-block:: python

   """
   Custom strategy: Generalize ICD-10 codes to their first character.
   
   ICD-10: J10.01 (Influenza A) → J (Diseases of respiratory system)
   """

   def apply(value, **kwargs):
       """
       Keep first character of ICD-10 code.
       
       Args:
           value: ICD-10 code (e.g., "J10.01")
       
       Returns:
           First character (e.g., "J")
       """
       if value is None:
           return ""
       
       str_val = str(value).strip()
       return str_val[0] if str_val else ""


**Usage in rules.json**:

.. code-block:: json

   {
     "diagnosis": "icd_generalize"
   }

**Using with Python API**:

.. code-block:: python

   from maskme.core.engine import MaskMe

   # Import your custom strategy
   from custom_strategies import icd_generalize

   # Register it in the engine's strategy registry
   masker = MaskMe(rules={
       "diagnosis": "icd_generalize"
   })
   masker.strategies["icd_generalize"] = icd_generalize.apply

   # Now use it
   masked_records = list(masker.mask(records))

Example 2: Conditional Redaction
---------------------------------

Suppose you want to redact sensitive data only if it's marked as "confidential":

**File: custom_strategies/conditional_redact.py**

.. code-block:: python

   """
   Custom strategy: Redact if marked confidential, otherwise hash.
   """

   import hashlib
   from maskme.strategies import redaction

   def apply(value, is_confidential=False, **kwargs):
       """
       Redact if confidential, else hash.
       
       Args:
           value: Value to transform
           is_confidential: Boolean flag (passed from rules)
       
       Returns:
           Redacted value or hash
       """
       if value is None:
           return ""
       
       if is_confidential:
           # Redact completely
           return redaction.apply(value, char="*")
       else:
           # Hash instead (less destructive)
           return hashlib.sha256(str(value).encode()).hexdigest()


**Usage in rules.json**:

.. code-block:: json

   {
     "email": {"strategy": "conditional_redact", "is_confidential": true},
     "phone": {"strategy": "conditional_redact", "is_confidential": false}
   }

Example 3: Domain-Specific Transformation (PII Masking)
-------------------------------------------------------

A realistic example: anonymize personal names using a lookup table of fake names.

**File: custom_strategies/fake_names.py**

.. code-block:: python

   """
   Custom strategy: Replace names with fake names (consistent).
   
   Same real name → same fake name (deterministic for record linkage).
   """

   import hashlib

   # Simple lookup table (in production, use a larger database)
   FAKE_NAMES = [
       "Alex", "Jordan", "Casey", "Morgan", "Riley",
       "Taylor", "Quinn", "Dakota", "Bailey", "Avery"
   ]

   def apply(value, salt="", **kwargs):
       """
       Replace name with consistent fake name.
       
       Args:
           value: Real name (e.g., "Alice Johnson")
           salt: Salt for consistency
       
       Returns:
           Fake name (same input → same output)
       """
       if value is None:
           return ""
       
       # Create deterministic hash to pick from list
       hash_input = f"{value}{salt}".encode()
       hash_value = int(hashlib.sha256(hash_input).hexdigest(), 16)
       fake_index = hash_value % len(FAKE_NAMES)
       
       return FAKE_NAMES[fake_index]


**Usage**:

.. code-block:: python

   from maskme.core.engine import MaskMe
   from custom_strategies import fake_names

   masker = MaskMe(rules={
       "name": {"strategy": "fake_names", "salt": "my-org-salt"}
   })
   masker.strategies["fake_names"] = fake_names.apply

   # "Alice Johnson" → "Alex" (always)
   # "Bob Smith" → "Jordan" (always)
   # Different real names, same fake → consistency for linking

Example 4: Field-Dependent Masking
----------------------------------

Mask a field differently based on another field's value:

**File: custom_strategies/field_aware.py**

.. code-block:: python

   """
   Custom strategy: Mask differently based on record classification.
   
   Example: Salary anonymization
     - If classification="public": hash
     - If classification="internal": noise
     - If classification="confidential": drop
   """

   import hashlib
   import random

   def apply(value, record=None, salt="", **kwargs):
       """
       Classification-aware masking.
       
       Args:
           value: Salary to mask
           record: Full record (for context), optional
           salt: Salt for hashing
       
       Returns:
           Masked value or "__DROP__"
       """
       if value is None:
           return ""
       
       # This is a simplified example. In practice, the engine would need
       # to pass the full record context (not currently built-in).
       # See advanced patterns below.
       
       classification = record.get("classification", "internal") if record else "internal"
       
       if classification == "public":
           return hashlib.sha256(f"{value}{salt}".encode()).hexdigest()[:8]
       elif classification == "internal":
           # Add ~5% noise
           noised = float(value) * (1 + random.uniform(-0.05, 0.05))
           return f"{noised:.0f}"
       else:  # confidential
           return "__DROP__"

Registering Your Custom Strategy
---------------------------------

**Option 1: Register in Python Code**

.. code-block:: python

   from maskme.core.engine import MaskMe
   from custom_strategies import my_strategy

   masker = MaskMe(rules=my_rules)
   masker.strategies["my_custom_strategy"] = my_strategy.apply

**Option 2: Create a Module and Import**

If you have multiple custom strategies:

**File: my_company/anonymization/strategies.py**

.. code-block:: python

   """
   My company's custom strategies.
   """

   def medical_code_generalize(value, **kwargs):
       return str(value)[0] if value else ""

   def pii_mask(value, **kwargs):
       # ... implementation
       pass

**Then use**:

.. code-block:: python

   from maskme.core.engine import MaskMe
   from my_company.anonymization import strategies

   masker = MaskMe(rules=my_rules)
   masker.strategies["medical"] = strategies.medical_code_generalize
   masker.strategies["pii"] = strategies.pii_mask

Testing Your Custom Strategy
-----------------------------

Always test before using in production:

.. code-block:: python

   from custom_strategies import my_strategy

   # Test basic cases
   assert my_strategy.apply("test") == "expected"
   assert my_strategy.apply(None) == ""
   assert my_strategy.apply(123) == "123"  # Type conversion

   # Test edge cases
   assert my_strategy.apply("") == "expected"
   assert my_strategy.apply("   ") == "expected"

   # Test with parameters
   result = my_strategy.apply("test", param1="value")
   assert result == "expected"

   # Test determinism (if required)
   value1 = my_strategy.apply("consistent-input", salt="my-salt")
   value2 = my_strategy.apply("consistent-input", salt="my-salt")
   assert value1 == value2

Full Example: End-to-End
------------------------

**Scenario**: Anonymize student test scores. Keep the score but round to nearest 5, hash student ID.

**File: custom_strategies/education.py**

.. code-block:: python

   """
   Custom strategies for education datasets.
   """

   import hashlib

   def round_score(value, **kwargs):
       """Round score to nearest 5."""
       if value is None:
           return None
       
       score = float(value)
       return round(score / 5) * 5

   def hash_student_id(value, salt="", **kwargs):
       """Hash student ID for anonymity."""
       if value is None:
           return ""
       
       input_str = f"{value}{salt}".encode()
       return hashlib.sha256(input_str).hexdigest()[:8]

**Usage**:

.. code-block:: python

   import csv
   from maskme.core.engine import MaskMe
   from custom_strategies.education import round_score, hash_student_id

   # Set up engine
   masker = MaskMe(rules={
       "student_id": "hash_student_id",
       "name": "drop",
       "score": "round_score",
       "class": "keep"
   })

   masker.strategies["hash_student_id"] = hash_student_id
   masker.strategies["round_score"] = round_score

   # Load and process data
   with open("scores.csv") as f:
       records = list(csv.DictReader(f))

   masked = list(masker.mask(records))

   # Save
   with open("scores_masked.csv", "w") as f:
       writer = csv.DictWriter(f, fieldnames=masked[0].keys())
       writer.writeheader()
       writer.writerows(masked)

**Input** (scores.csv):

.. code-block:: csv

   student_id,name,score,class
   S001,Alice,87,Math
   S002,Bob,92,Math
   S003,Carol,78,Science

**Output** (scores_masked.csv):

.. code-block:: csv

   student_id,score,class
   a1b2c3d4,85,Math
   e5f6g7h8,90,Math
   i9j0k1l2,80,Science

Advanced: Strategy Composition
-------------------------------

Combine multiple custom strategies:

.. code-block:: python

   def hash_then_redact(value, salt="", keep_end=4, **kwargs):
       """Hash then show last N characters."""
       hashed = hashlib.sha256(f"{value}{salt}".encode()).hexdigest()
       length = len(hashed)
       if keep_end >= length:
           return hashed
       redacted_part = "*" * (length - keep_end)
       return redacted_part + hashed[-keep_end:]

**Result**:

.. code-block:: text

   "alice@example.com"
   → hashed: "d6d5d09f12b3f0f1a8a2c1e3b5e7d9f2"
   → redacted: "****************************7d9f2"

Best Practices
---------------

1. **Keep it simple**: One transformation per strategy
2. **Document parameters**: What does each kwarg do?
3. **Handle None**: Always check for None input
4. **Be deterministic**: Same input → same output (unless randomness is intentional)
5. **Validate inputs**: Raise clear errors for invalid parameters
6. **Test edge cases**: Empty strings, None, wrong types
7. **Document privacy**: What privacy guarantee does this provide?
8. **Avoid data leakage**: Don't accidentally include sensitive data in error messages

Next Steps
----------

- Need a more complex strategy? See :doc:`../reference/api` for the full engine API
- Want to measure privacy of your custom strategy? See analytics modules
- Ready to ship? See :doc:`../tutorials/getting-started` for production patterns
