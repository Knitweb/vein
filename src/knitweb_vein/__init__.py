"""knitweb-vein: Smart contract procedure execution engine.

The vein (Ader) through which Knitweb's logic flows. Deterministic, verifiable stored procedures
as units of useful work (PoUW jobs) for distributed settlement.

Design: contracts and procedures are pure expressions, sandboxed, and re-executable
for verification. Results are signed and canonical-serialized for settlement.

Vein depends on knitweb-knitfield (the PoUW registry + settlement policy) but is otherwise
standalone — no Pulse or Heart installation required.
"""

from __future__ import annotations

__version__ = "0.1.1"

from .contract import (
    ContractProof,
    SmartContractProcedureJob,
    execute,
    verify,
)
from .executor import (
    ContractExecutionError,
    ExecutionContext,
    execute_procedure,
    resolve_contract,
)
from .items import (
    ProcedureSpec,
    SmartContractRecord,
)

__all__ = [
    # Job types
    "SmartContractProcedureJob",
    "ContractProof",
    # Execution
    "execute",
    "verify",
    "ExecutionContext",
    "execute_procedure",
    "resolve_contract",
    "ContractExecutionError",
    # Fabric items
    "SmartContractRecord",
    "ProcedureSpec",
]
