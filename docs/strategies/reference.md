# Anonymization Strategies

MaskMe provides six primary strategies to address different privacy requirements.

### 1. Hash Strategy (`hash`)
*   **Logic**: Irreversible pseudonymization using cryptographic hashing.
*   **Formula**: $$y = H(x + \text{salt})$$
*   **Best for**: Unique identifiers (IDs, Usernames).

### 2. Noise Strategy (`noise`)
*   **Logic**: Adds a random value within a specified range to numerical data.
*   **Formula**: $$y = x + \epsilon, \text{where } \epsilon \in [-\text{range}, +\text{range}]$$
*   **Best for**: Salaries, ages, or sensor metrics.

### 3. Redaction Strategy (`redact`)
*   **Logic**: Replaces the entire value with a static placeholder.
*   **Example**: `John Doe` $\rightarrow$ `[REDACTED]`
*   **Best for**: Names, emails, or physical addresses.

### 4. Generalization Strategy (`generalize`)
*   **Logic**: Reduces the precision of data by mapping values to intervals.
*   **Example**: `Age: 23` $\rightarrow$ `Age: 20-30`
*   **Best for**: Birth years or geographic locations to increase **k-anonymity**.

### 5. Masking Strategy (`mask`)
*   **Logic**: Hides parts of a string while keeping some characters visible for context.
*   **Example**: `4500-1234-5678` $\rightarrow$ `****-****-5678`
*   **Best for**: Credit card numbers or phone numbers.

### 6. Drop Strategy (`drop`)
*   **Logic**: Entirely removes the column from the output dataset.
*   **Best for**: High-risk identifiers that are not needed for analysis (e.g., SSN).