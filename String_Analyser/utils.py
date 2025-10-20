import hashlib
from collections import Counter


def compute_sha256(value: str) -> str:
    """Compute SHA-256 hash for the string."""
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def is_palindrome(value: str) -> bool:
    """Check if string reads the same forward and backward (case-insensitive)."""
    normalized = ''.join(filter(str.isalnum, value.lower()))
    return normalized == normalized[::-1]


def analyze_string(value: str) -> dict:
    """Compute all required string properties."""
    length = len(value)
    palindrome = is_palindrome(value)
    unique_chars = len(set(value))
    word_count = len(value.split())
    sha256_hash = compute_sha256(value)
    char_freq = dict(Counter(value))

    return {
        "length": length,
        "is_palindrome": palindrome,
        "unique_characters": unique_chars,
        "word_count": word_count,
        "sha256_hash": sha256_hash,
        "character_frequency_map": char_freq,
    }
