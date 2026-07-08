"""Minimal crypto primitives for Vein (vendored).

ECDSA sign/verify (secp256k1) + SHA-256 hashing. Used for contract execution proofs.
Standalone so Vein doesn't depend on Pulse's full crypto stack.
"""

from __future__ import annotations

import hashlib
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_string, sigdecode_string

__all__ = ["generate_keypair", "sign", "verify", "sha256_hex"]


def sha256_hex(data: bytes) -> str:
    """SHA-256 hash as hex string."""
    return hashlib.sha256(data).hexdigest()


def generate_keypair() -> tuple[str, str]:
    """Generate a fresh secp256k1 keypair.

    Returns:
        (priv_hex, pub_hex) — 32-byte private key and 64-byte uncompressed-point
        public key (x||y), both hex-encoded. Uses os.urandom via ecdsa's generator.
    """
    sk = SigningKey.generate(curve=SECP256k1)
    priv_hex = sk.to_string().hex()
    pub_hex = sk.get_verifying_key().to_string().hex()
    return priv_hex, pub_hex


def sign(priv_hex: str, message: bytes) -> str:
    """Sign a message with secp256k1 private key (hex).

    Args:
        priv_hex: Private key as hex string
        message: Message bytes to sign

    Returns:
        Signature as hex string (64 bytes = 128 hex chars)
    """
    sk = SigningKey.from_string(bytes.fromhex(priv_hex), curve=SECP256k1, hashfunc=hashlib.sha256)
    sig_bytes = sk.sign_digest(hashlib.sha256(message).digest(), sigencode=sigencode_string)
    return sig_bytes.hex()


def verify(pub_hex: str, message: bytes, signature_hex: str) -> bool:
    """Verify a secp256k1 signature.

    Args:
        pub_hex: Public key as hex string
        message: Original message bytes
        signature_hex: Signature as hex string

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        vk = VerifyingKey.from_string(bytes.fromhex(pub_hex), curve=SECP256k1, hashfunc=hashlib.sha256)
        vk.verify_digest(bytes.fromhex(signature_hex),
                        hashlib.sha256(message).digest(),
                        sigdecode=sigdecode_string)
        return True
    except Exception:
        return False
