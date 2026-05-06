"""
Unit tests for maskme.strategies.hashing
------------------------------------------
Covers return type, determinism, salt injection, algorithm selection,
unsupported algorithm fallback, and edge-case input values.
"""

import hashlib
import warnings

import pytest

from maskme.strategies.hashing import apply


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _expected(value: str, salt: str = "", algo: str = "sha256") -> str:
    """Compute the expected hex digest independently of the strategy."""
    prepared = f"{value}{salt}".encode("utf-8")
    return hashlib.new(algo, prepared).hexdigest()


# ===========================================================================
# Return value contract
# ===========================================================================


class TestReturnValue:

    def test_returns_string(self):
        """Return type is always str."""
        assert isinstance(apply("alice@example.com"), str)

    def test_returns_non_empty_hex_string(self):
        """A non-None value produces a non-empty hex digest."""
        result = apply("alice@example.com")
        assert len(result) > 0
        # Hex digits only
        assert all(c in "0123456789abcdef" for c in result)

    def test_none_returns_empty_string(self):
        """None input produces an empty string (not None, not a hash of 'None')."""
        assert apply(None) == ""

    def test_sha256_digest_length(self):
        """sha256 always produces a 64-character hex digest."""
        assert len(apply("test")) == 64

    def test_sha512_digest_length(self):
        """sha512 always produces a 128-character hex digest."""
        assert len(apply("test", algo="sha512")) == 128


# ===========================================================================
# Determinism
# ===========================================================================


class TestDeterminism:

    def test_same_value_same_result(self):
        """Hashing the same value twice returns the same digest."""
        assert apply("alice@example.com") == apply("alice@example.com")

    def test_same_value_same_salt_same_result(self):
        """Same value + same salt always produces the same digest."""
        assert apply("alice", salt="secret") == apply("alice", salt="secret")

    def test_different_values_different_results(self):
        """Different values must not collide."""
        assert apply("alice@example.com") != apply("bob@example.com")

    def test_matches_manual_sha256(self):
        """Output matches a manually computed sha256 digest."""
        assert apply("alice@example.com", salt="s") == _expected("alice@example.com", salt="s")


# ===========================================================================
# Salt
# ===========================================================================


class TestSalt:

    def test_salt_changes_digest(self):
        """The same value hashed with different salts must differ."""
        assert apply("alice", salt="salt1") != apply("alice", salt="salt2")

    def test_empty_salt_differs_from_non_empty(self):
        """No salt and an explicit salt must produce different digests."""
        assert apply("alice", salt="") != apply("alice", salt="x")

    def test_salt_is_appended_to_value(self):
        """Digest equals hash of 'value + salt' concatenation."""
        assert apply("alice", salt="secret") == _expected("alice", salt="secret")

    def test_default_salt_is_empty_string(self):
        """Omitting salt is equivalent to salt=''."""
        assert apply("alice") == apply("alice", salt="")


# ===========================================================================
# Algorithm selection
# ===========================================================================


class TestAlgorithmSelection:

    def test_default_is_sha256(self):
        """Omitting algo uses sha256."""
        assert apply("test") == _expected("test", algo="sha256")

    def test_sha512(self):
        assert apply("test", algo="sha512") == _expected("test", algo="sha512")

    def test_md5(self):
        """md5 is supported on all platforms."""
        assert apply("test", algo="md5") == _expected("test", algo="md5")

    def test_sha1(self):
        assert apply("test", algo="sha1") == _expected("test", algo="sha1")

    def test_uppercase_algo_accepted_by_openssl(self):
        """On OpenSSL-backed platforms (Linux), hashlib accepts uppercase algo names.
        'SHA256' produces the same digest as 'sha256' without emitting a warning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = apply("test", algo="SHA256")
        # No warning: OpenSSL normalises the name internally
        assert result == _expected("test", algo="sha256")
        assert len(caught) == 0


# ===========================================================================
# Unsupported algorithm fallback
# ===========================================================================


class TestUnsupportedAlgorithm:

    def test_unsupported_algo_emits_warning(self):
        """An unsupported algorithm triggers a UserWarning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            apply("test", algo="not_an_algo")
        assert len(caught) == 1
        assert issubclass(caught[0].category, UserWarning)
        assert "not_an_algo" in str(caught[0].message)
        assert "sha256" in str(caught[0].message)

    def test_unsupported_algo_falls_back_to_sha256(self):
        """Result of fallback equals a direct sha256 hash of the same input."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = apply("test", algo="not_an_algo")
        assert result == _expected("test", algo="sha256")

    def test_valid_algo_emits_no_warning(self):
        """A valid algorithm must not emit any warnings."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            apply("test", algo="sha256")
        assert len(caught) == 0


# ===========================================================================
# Edge-case input values
# ===========================================================================


class TestEdgeCaseInputs:

    def test_empty_string_is_hashed(self):
        """An empty string is a valid input and produces a non-empty digest."""
        result = apply("")
        assert result == _expected("")
        assert len(result) == 64

    def test_integer_value(self):
        """An integer is converted to string before hashing."""
        assert apply(42) == _expected("42")

    def test_float_value(self):
        assert apply(3.14) == _expected("3.14")

    def test_boolean_true(self):
        assert apply(True) == _expected("True")

    def test_boolean_false(self):
        assert apply(False) == _expected("False")

    def test_unicode_value(self):
        """Unicode characters are handled correctly via utf-8 encoding."""
        assert apply("héllo wörld") == _expected("héllo wörld")

    def test_long_string(self):
        """A very long string is hashed without error."""
        long_val = "a" * 10_000
        result = apply(long_val)
        assert len(result) == 64

    # --- kwargs forwarding ---

    def test_accepts_extra_kwargs(self):
        """Extra kwargs forwarded by the engine are accepted without raising."""
        result = apply("alice", salt="s", algo="sha256", foo="bar")
        assert result == _expected("alice", salt="s")