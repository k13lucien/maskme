from . import hashing
from . import redaction
from . import noise
from . import generalization
from . import noop
from . import drop

# Registry of available strategies
STRATEGIES = {
    "hash": hashing.apply,
    "redact": redaction.apply,
    "noise": noise.apply,
    "generalize": generalization.apply,
    "keep": noop.apply,
    "drop": drop.apply,
}