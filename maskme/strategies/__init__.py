from . import hashing

# Registry of available strategies
STRATEGIES = {
    "hash": hashing.apply
}