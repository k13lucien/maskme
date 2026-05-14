Introduction to MaskMe
======================

The Privacy-Utility Challenge
------------------------------

Organizations today face a fundamental tension: **how to extract value from data while protecting individual privacy**.

**The Problem:**

- Regulations (GDPR, HIPAA, CCPA) demand data minimization and anonymization
- Data scientists need rich, detailed datasets for meaningful analysis
- Traditional anonymization (removing identifiers) is insufficient — re-identification is possible through auxiliary information
- Naive anonymization destroys statistical properties, making data useless for analysis

**Example**: Removing names and IDs from healthcare data might seem safe, but combining age + postal code + diagnosis can re-identify individuals.

**What MaskMe Solves:**

MaskMe provides a principled, flexible framework for data anonymization that:

1. **Balances privacy and utility**: Choose strategies that fit your privacy goals without destroying data value
2. **Works with any format**: CSV, JSON, JSONL — same logic across all
3. **Is transparent**: Measure privacy risk and data loss precisely
4. **Scales effortlessly**: Stream large datasets without loading everything into memory
5. **Is extensible**: Build custom strategies for domain-specific needs

Core Concepts
-------------

Anonymization Strategy
~~~~~~~~~~~~~~~~~~~~~~

A **strategy** is a function that transforms a sensitive value to hide it while (optionally) keeping some utility.

Examples:

- **Hash**: Email → unreadable but consistent fingerprint
- **Redact**: Phone → partially hidden (keep last 4 digits)
- **Drop**: Delete the field entirely
- **Noise**: Age 42 → 40 or 44 (statistical noise, distribution preserved)
- **Generalize**: Postal code → state-level only

Each strategy makes different privacy-utility trade-offs.

Quasi-Identifier
~~~~~~~~~~~~~~~~

A **quasi-identifier** is a combination of non-unique attributes that can identify someone.

Example: Age (28) + State (CA) + Gender (F) might uniquely identify someone in a database, even if names are removed.

Privacy Metrics
~~~~~~~~~~~~~~~

MaskMe measures privacy formally:

- **K-anonymity**: Each person is indistinguishable from at least K-1 others
- **L-diversity**: Sensitive attributes have sufficient variation within groups
- **T-closeness**: Masked data distribution stays close to the original (utility check)

These ensure anonymized data meets formal privacy definitions while preserving utility.

Use Cases
---------

Healthcare
~~~~~~~~~~

**Problem**: Share patient data for research without exposing identity.

**Solution**:
- Hash diagnosis codes (preserve patterns for linkage)
- Generalize dates (year only, not exact visit dates)
- Drop patient IDs
- Keep medication (non-sensitive) and aggregate outcomes

**Result**: Researchers can study treatment efficacy; individual identities are protected.

Finance
~~~~~~~

**Problem**: Analyze fraud patterns without exposing customer data.

**Solution**:
- Hash customer IDs (consistent, but unreadable)
- Redact account numbers (show last 4 digits for support)
- Add noise to transaction amounts (preserve statistical patterns)
- Keep transaction type and merchant (needed for analysis)

**Result**: Fraud models work on realistic data; no personal information is exposed.

E-Commerce
~~~~~~~~~~

**Problem**: Share user behavior data with analytics vendors.

**Solution**:
- Drop user IDs
- Hash IP addresses
- Generalize location (country, not city)
- Keep product categories (needed for recommendations)

**Result**: Vendor can build models; users remain anonymous.

Machine Learning
~~~~~~~~~~~~~~~~

**Problem**: Create privacy-safe training datasets without bias.

**Solution**:
- Hash sensitive attributes (protected class)
- Generalize categorical features
- Drop identifiers
- Add noise to sensitive continuous variables

**Result**: Train models on realistic, anonymized data; meets GDPR and fairness standards.

Design Philosophy
------------------

**Modular**: Each strategy is independent. Mix and match as needed.

**Composable**: Apply different strategies to different fields in the same dataset.

**Observable**: Measure privacy rigorously; don't guess.

**Scalable**: Stream data. Handle datasets larger than RAM.

**Extensible**: Write custom strategies for domain-specific rules.

**Simple**: Learn one mental model; apply everywhere (whether using CLI or Python API).

Next: Head to the :doc:`Getting Started tutorial <../tutorials/getting-started>` to anonymize your first dataset.
