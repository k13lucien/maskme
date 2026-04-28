from . import hashing
from . import redaction
from . import noise

# Registry of available strategies
STRATEGIES = {
    "hash": hashing.apply,
    "redact": redaction.apply,
    "noise": noise.apply,
}