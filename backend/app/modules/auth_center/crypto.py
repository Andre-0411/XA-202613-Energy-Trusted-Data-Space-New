"""Simulated National Cryptography (国密) Utilities.

This module provides simulated SM2/SM3/SM4 cryptographic operations for development
and testing purposes. In production, use proper cryptographic libraries.
"""
import base64
import hashlib
import secrets
from typing import Tuple


def generate_sm2_keypair() -> Tuple[str, str]:
    """Generate simulated SM2 keypair.

    Returns:
        Tuple of (private_key, public_key) as base64-encoded strings.
    """
    # Generate 32 bytes of random data for private key
    private_bytes = secrets.token_bytes(32)
    # Generate 64 bytes of random data for public key
    public_bytes = secrets.token_bytes(64)

    private_key = base64.b64encode(private_bytes).decode("utf-8")
    public_key = base64.b64encode(public_bytes).decode("utf-8")

    return private_key, public_key


def sm2_sign(data: str, private_key: str) -> str:
    """Simulate SM2 signature generation.

    Args:
        data: The data to sign.
        private_key: The private key (base64 encoded).

    Returns:
        Simulated signature string prefixed with "SM2_SIG:".
    """
    # Create a hash of the data + private key for simulation
    combined = f"{data}:{private_key}".encode("utf-8")
    hash_value = hashlib.sha256(combined).hexdigest()
    return f"SM2_SIG:{hash_value}"


def sm2_verify(data: str, signature: str, public_key: str) -> bool:
    """Verify a simulated SM2 signature.

    Args:
        data: The original data.
        signature: The signature to verify.
        public_key: The public key (base64 encoded).

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signature.startswith("SM2_SIG:"):
        return False

    # Recreate the expected signature
    expected_sig = sm2_sign(data, public_key)
    return signature == expected_sig


def sm3_hash(data: str) -> str:
    """Simulate SM3 hash generation.

    SM3 is China's national standard hash function. This is simulated using
    SHA-256 for development purposes.

    Args:
        data: The data to hash.

    Returns:
        SHA-256 hash prefixed with "SM3:".
    """
    hash_value = hashlib.sha256(data.encode("utf-8")).hexdigest()
    return f"SM3:{hash_value}"


def sm4_encrypt(data: str, key: str) -> str:
    """Simulate SM4 encryption.

    SM4 is China's national standard block cipher. This is simulated using
    base64 encoding and reversal for development purposes.

    Args:
        data: The plaintext data to encrypt.
        key: The encryption key (base64 encoded).

    Returns:
        Simulated ciphertext (base64 encoded + reversed).
    """
    # Combine data with key hash for simulation
    combined = f"{data}:{key}".encode("utf-8")
    encrypted = base64.b64encode(combined).decode("utf-8")
    # Reverse to simulate encryption
    return encrypted[::-1]


def sm4_decrypt(data: str, key: str) -> str:
    """Simulate SM4 decryption.

    Args:
        data: The ciphertext to decrypt.
        key: The decryption key (base64 encoded).

    Returns:
        The decrypted plaintext.

    Raises:
        ValueError: If decryption fails.
    """
    try:
        # Reverse the "encryption"
        reversed_data = data[::-1]
        decrypted = base64.b64decode(reversed_data.encode("utf-8")).decode("utf-8")
        # Extract original data (format: "data:key")
        if ":" in decrypted:
            return decrypted.rsplit(":", 1)[0]
        return decrypted
    except Exception:
        raise ValueError("Decryption failed: invalid ciphertext or key")
