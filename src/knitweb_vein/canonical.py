"""Minimal canonical encoding for Vein (vendored).

CBOR encoding for canonical dict serialization. Used for deterministic hashing of contract results.
Standalone so Vein doesn't depend on Pulse's full canonical stack.
"""

from __future__ import annotations

import cbor2

__all__ = ["encode"]


def encode(value: object) -> bytes:
    """Encode a value as canonical CBOR bytes.

    Args:
        value: Anything serializable (str, int, bool, list, dict)

    Returns:
        Canonical CBOR bytes

    Raises:
        TypeError: If value contains non-canonical types (e.g., float, None, custom objects)
    """
    # Validate no floats or Nones
    _validate_canonical_type(value)
    # CBOR2 with default=canonical_compat
    return cbor2.dumps(value, canonical=True)


def _validate_canonical_type(obj: object) -> None:
    """Raise TypeError if obj is not canonical-serializable."""
    if obj is None or isinstance(obj, bool):
        return
    if isinstance(obj, (str, int)):
        return
    if isinstance(obj, list):
        for item in obj:
            _validate_canonical_type(item)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"dict keys must be strings, got {type(k).__name__}")
            _validate_canonical_type(v)
        return
    raise TypeError(f"non-canonical type: {type(obj).__name__}")
