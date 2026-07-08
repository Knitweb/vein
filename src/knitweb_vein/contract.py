"""Smart contract stored procedures as PoUW jobs — deterministic execution + verification.

A SmartContractProcedureJob invokes a procedure defined in a contract (stored as a
Fabric record) with deterministic execution so verifiers can re-run and confirm the
result. This mirrors SynapticCompileJob's pattern: resolve the contract asset, execute
the procedure, sign the result, and verify by re-execution.

Design:
  - Contracts are OriginTrail assets or Fabric records with a canonical bytecode form
  - Procedures are named entry points (methods) with typed arguments
  - Execution is deterministic (no randomness, no wall-clock, no external I/O)
  - Proof is the result + signature + digest; verification re-runs the job
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import canonical, crypto

__all__ = [
    "SmartContractProcedureJob",
    "ContractProof",
    "execute",
    "verify",
    "VERIFICATION_POLICY",
]


@dataclass(frozen=True)
class SmartContractProcedureJob:
    """A unit of useful work: call a stored procedure on a contract."""

    contract_asset: dict
    """The contract spec (OriginTrail asset ref or Fabric record dict)."""

    procedure_name: str
    """Name of the procedure to invoke (e.g., 'transfer', 'vote', 'settle')."""

    arguments: dict[str, Any]
    """Typed arguments to pass to the procedure (must be canonical-serializable)."""

    originator_pub: str
    """The verified originator whose signature must appear on the result."""


@dataclass(frozen=True)
class ContractProof:
    """Result of executing a smart contract stored procedure."""

    result: dict
    """The procedure's return value (canonical dict: str/int/list/bool only)."""

    signature: str
    """Originator signature over the result."""

    digest: str
    """Content digest of the result (SHA-256 of canonical result)."""


def execute(job: SmartContractProcedureJob, originator_priv: str) -> ContractProof:
    """Execute the stored procedure: resolve contract → call procedure → sign result.

    Args:
        job: The procedure job specification.
        originator_priv: Private key to sign the result.

    Returns:
        ContractProof with the result, signature, and digest.

    This is the spider's work phase. Determinism is guaranteed by:
      1. Contract resolution is content-addressed (same asset CID → same bytecode)
      2. Procedure execution is pure (no I/O, no RNG, no wall-clock)
      3. Result is canonical (str/int/list/bool only → identical bytes)
    """
    # Import here to avoid circular dependency
    from .contract_executor import execute_procedure, resolve_contract

    # Resolve the contract from Fabric/OriginTrail
    contract = resolve_contract(job.contract_asset)

    # Execute the procedure deterministically
    result = execute_procedure(contract, job.procedure_name, job.arguments)

    # Ensure result is canonical (dict form)
    if not isinstance(result, dict):
        result = {"value": result}

    # Sign the canonical result
    result_bytes = canonical.encode(result)
    signature = crypto.sign(originator_priv, result_bytes)
    digest = crypto.sha256_hex(result_bytes)

    return ContractProof(
        result=result, signature=signature, digest=digest
    )


def verify(job: SmartContractProcedureJob, proof: ContractProof) -> bool:
    """Verify the stored procedure result: re-execute and confirm proof.

    Args:
        job: The procedure job specification.
        proof: The claimed proof.

    Returns:
        True if the proof is valid and can be settled; False if fraudulent.

    Checks (all deterministic/boolean):
      1. Claimed digest matches claimed result
      2. Re-executing the job produces byte-identical result (determinism verified)
      3. Originator signature is valid over the result
    """
    # Import here to avoid circular dependency
    from .contract_executor import execute_procedure, resolve_contract

    # Check 1: digest matches result
    result_bytes = canonical.encode(proof.result)
    if crypto.sha256_hex(result_bytes) != proof.digest:
        return False

    # Check 2: re-execute and compare (byte-identical = determinism verified)
    try:
        contract = resolve_contract(job.contract_asset)
        reexecuted = execute_procedure(contract, job.procedure_name, job.arguments)
        if not isinstance(reexecuted, dict):
            reexecuted = {"value": reexecuted}
        reexecuted_bytes = canonical.encode(reexecuted)
        if reexecuted_bytes != result_bytes:
            return False
    except Exception:
        # Execution error = fraud
        return False

    # Check 3: signature is valid
    return crypto.verify(job.originator_pub, result_bytes, proof.signature)


# Registration: smart contract procedures settle via uniform (deterministic) verification
VERIFICATION_POLICY = "uniform"

# Job class will be registered when this module is imported (in __init__.py or at first use)
# register_job_class("smart-contract-procedure", VERIFICATION_POLICY)
