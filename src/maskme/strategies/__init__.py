from . import hashing
from . import redaction
from . import noise
from . import generalization

# Registry of available strategies
STRATEGIES = {
    "hash": hashing.apply,
    "redact": redaction.apply,
    "noise": noise.apply,
    "generalize": generalization.apply,
}