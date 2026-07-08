"""Smart contract record schema for the Fabric.

Contracts are typed records in the Fabric, defining named procedures that can be
called as PoUW jobs. Each procedure is a pure expression that deterministically
maps inputs to outputs.

Design:
  - SmartContractRecord: metadata (name, originator, procedures)
  - ProcedureSpec: name, parameter schema, body (expression or bytecode ref)
  - Body can be: expression (dict), bytecode CID, or native gate reference
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core import canonical

__all__ = ["SmartContractRecord", "ProcedureSpec"]


@dataclass(frozen=True)
class ProcedureSpec:
    """A stored procedure definition."""

    name: str
    """Procedure name (e.g., 'transfer', 'vote', 'settle')."""

    params: dict[str, str]
    """Parameter schema: {param_name: type} where type in ('str', 'int', 'bool', 'list', 'dict')."""

    body: dict | str
    """Procedure logic: either a dict expression or a CID reference to bytecode."""

    returns: str = "any"
    """Expected return type (e.g., 'int', 'dict', 'bool')."""

    def to_record(self) -> dict:
        """Canonical record representation."""
        return {
            "name": self.name,
            "params": self.params,
            "body": self.body if isinstance(self.body, str) else canonical.cid(self.body),
            "returns": self.returns,
        }


@dataclass(frozen=True)
class SmartContractRecord:
    """A contract record stored in the Fabric."""

    name: str
    """Human-readable contract name."""

    originator: str
    """The originator's verified public key."""

    procedures: dict[str, ProcedureSpec] = field(default_factory=dict)
    """Named procedures this contract exposes."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Optional metadata (network, deployment address, version, etc.)."""

    def to_record(self) -> dict:
        """Canonical Fabric record (all canonical-serializable types)."""
        return {
            "kind": "smart-contract",
            "name": self.name,
            "originator": self.originator,
            "procedures": {
                pname: pspec.to_record() for pname, pspec in self.procedures.items()
            },
            "metadata": self.metadata,
        }

    def cid(self) -> str:
        """Content address of this contract."""
        return canonical.cid(self.to_record())

    def weave(self, web: Any) -> str:
        """Weave this contract into the Fabric and return its CID."""
        return web.weave(self.to_record())
