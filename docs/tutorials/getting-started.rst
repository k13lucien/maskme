Getting Started with MaskMe
============================

This tutorial guides you through your first data anonymization project using MaskMe. You will learn the complete workflow: from data preparation to executing the masking pipeline and verifying results.

Estimated time: 10 minutes

What You'll Learn
-----------------

- How to install MaskMe in your environment.
- How to prepare a sample dataset with sensitive fields.
- How to define anonymization rules for different data types.
- How to execute the masking pipeline via the command line.
- How to analyze and verify the transformed data.

Before You Start
----------------

Ensure you have:

- Python 3.8+ installed.
- pip or poetry for package management.
- A text editor (VS Code, nano, vim, etc.).

1. Installation
---------------

Install MaskMe from PyPI:

.. code-block:: bash

   pip install maskme

Verify the installation:

.. code-block:: bash

   maskme --help

2. Prepare Sample Data
----------------------

Create a file named ``customers.csv`` with customer data containing sensitive fields:

.. code-block:: none

   id,full_name,email,age,credit_card,phone
   1,John Doe,john.doe@example.com,28,1234-5678-9012-3456,555-0123
   2,Jane Smith,jane.smith@work.com,34,9876-5432-1098-7654,555-0456
   3,Bob Wilson,bob@provider.net,45,5555-4444-3333-2222,555-0789

This dataset contains:

- **id**: Identifier (kept as-is).
- **full_name**: Personal name (sensitive).
- **email**: Email address (sensitive).
- **age**: Age information (sensitive).
- **credit_card**: Payment card (highly sensitive).
- **phone**: Phone number (sensitive).

3. Create Your Masking Rules
----------------------------

Define how each field should be anonymized. Create a file named ``rules.json``:

.. code-block:: json

   {
     "id": "noop",
     "full_name": "redact",
     "email": "hash",
     "age": {
       "strategy": "noise",
       "std_dev": 2
     },
     "credit_card": "drop",
     "phone": "generalize"
   }

Strategy Breakdown
~~~~~~~~~~~~~~~~~~

- **id** (noop): Keep original value.
- **full_name** (redact): Replace with a placeholder (e.g., [REDACTED]).
- **email** (hash): One-way cryptographic hash.
- **age** (noise): Add random variation.
- **credit_card** (drop): Remove completely from the output.
- **phone** (generalize): Coarsen to a less specific value.

4. Run the Masking Pipeline
---------------------------

Execute the anonymization with the following command:

.. code-block:: bash

   maskme --rules rules.json \
           --input customers.csv \
           --output anonymous_customers.csv \
           --salt "my-secret-salt"

5. Verify the Results
---------------------

Inspect the transformed dataset:

.. code-block:: bash

   cat anonymous_customers.csv

Expected output:

- **id** remains unchanged.
- **full_name** shows redacted placeholders.
- **email** is hashed (irreversible).
- **age** values are slightly shifted.
- **credit_card** is removed.
- **phone** field is generalized or redacted.

Troubleshooting
---------------

**Issue: command not found**
Ensure MaskMe is installed in your current Python environment.

**Issue: FileNotFoundError**
Verify that ``rules.json`` and your input file exist in the current directory.

**Issue: Unknown strategy**
Check the names in your rules. Valid strategies are: ``hash``, ``redact``, ``noise``, ``generalize``, ``drop``, and ``noop``.

Next Steps
----------

You have successfully anonymized your first dataset. Now explore:

* :doc:`../how-to/custom-strategy` — Build your own anonymization logic.
* :doc:`../reference/strategies` — Detailed strategy documentation.
* :doc:`../reference/api` — Python API for programmatic access.
* :doc:`../explanation/architecture` — Understand the engine design.
