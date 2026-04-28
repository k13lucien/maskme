from . import hashing
from . import redaction

# Registry of available strategies
STRATEGIES = {
    "hash": hashing.apply,
    "redact": redaction.apply,
}