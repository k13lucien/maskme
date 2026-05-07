"""
setup.py - Maskme package configuration.
Project layout: src/maskme/
Installation
------------
    pip install -e ".[dev]"           # development (editable)
    pip install -e "."                # editable without extras
"""
from setuptools import setup, find_packages
from pathlib import Path
import re

# Read README
here = Path(__file__).parent
long_description = (here / "README.md").read_text(encoding="utf-8") \
    if (here / "README.md").exists() else ""

# Read version — regex only, no exec()
# exec() would run the relative imports in __init__.py and crash during build.
_init_path = here / "src" / "maskme" / "__init__.py"
_init_text  = _init_path.read_text(encoding="utf-8") if _init_path.exists() else ""
_match      = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', _init_text, re.M)
__version__ = _match.group(1) if _match else "0.1.2"

# Core dependencies
INSTALL_REQUIRES = [
    "numpy>=1.24.0",
    "matplotlib>=3.7.0",
]

# Optional dependencies
EXTRAS_REQUIRE = {
    "full": [
        "ipywidgets>=8.0.0",
    ],
    "jupyter": [
        "jupyter>=1.0.0",
        "ipywidgets>=8.0.0",
        "nbformat>=5.7.0",
    ],
    "dev": [
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-xdist>=3.3.0",
        "black>=23.0.0",
        "isort>=5.12.0",
        "flake8>=6.0.0",
        "mypy>=1.4.0",
        "pre-commit>=3.3.0",
        "ipython>=8.0.0",
    ],
    "docs": [
        "sphinx>=7.0.0",
        "sphinx-rtd-theme>=1.3.0",
        "myst-parser>=2.0.0",
        "nbsphinx>=0.9.0",
    ],
}

# Package setup
setup(
    name="maskme",
    version=__version__,
    author="Lucien Kiemde",
    author_email="",
    maintainer_email="",
    description=(
        "Lightweight, modular Python library for data anonymization and "
        "pseudonymization. Supports 6 masking strategies (hash, redact, noise, "
        "generalize, keep, drop) with differential privacy, dot-notation for "
        "nested fields, streaming I/O for large datasets, and built-in "
        "utility validation via Q-Q plots. Designed for GDPR, HIPAA, and "
        "Law 010 compliance while preserving statistical utility."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/k13lucien/maskme",
    project_urls={
        "Bug Tracker": "https://github.com/k13lucien/maskme/issues",
        "Source Code": "https://github.com/k13lucien/maskme",
    },
    license="MIT",
    # src/ layout
    package_dir={"": "src"},
    packages=find_packages(
        where="src",
        exclude=["tests*", "examples*", "docs*", "benchmarks*"],
    ),
    python_requires=">=3.9",
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    classifiers=[
        "Development Status :: 3 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Information Technology",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Database",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Natural Language :: English",
    ],
    keywords=[
        "anonymization", "pseudonymization", "data privacy",
        "data masking", "PII", "GDPR", "HIPAA",
        "differential privacy", "data utility",
        "hashing", "redaction", "generalization", "noise",
        "data science", "machine learning", "structured data",
        "JSON", "CSV", "JSONL", "streaming",
        "privacy by design", "data protection",
        "Burkina Faso", "Africa",
    ],
    entry_points={},
    zip_safe=False,
)
