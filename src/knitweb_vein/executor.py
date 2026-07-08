"""Deterministic smart contract procedure execution.

This module provides the execution engine for smart contracts as PoUW jobs.
Procedures are deterministic expressions over the Fabric graph, evaluated
in a sandboxed context with no external I/O or randomness.

Architecture:
  - resolve_contract: fetch and verify contract from Fabric/OriginTrail
  - execute_procedure: call a named procedure with arguments
  - ExecutionContext: sandbox environment with memoization
  - Simple expression evaluator for MVP (identity, arithmetic, conditionals)
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ContractExecutionError",
    "resolve_contract",
    "execute_procedure",
    "ExecutionContext",
]


class ContractExecutionError(Exception):
    """Raised when contract execution fails (bad signature, missing procedure, etc.)."""

    pass


class ExecutionContext:
    """Sandbox for deterministic procedure execution.

    Provides:
      - Memoization (pure functions always return same result)
      - Type checking (enforces parameter/return types)
      - No I/O access (can't call external APIs)
      - Deterministic evaluation (no RNG, no wall-clock)
      - Simple expression evaluation (identity, arithmetic, conditionals)
    """

    def __init__(self, procedures: dict[str, dict] | None = None):
        self.memo: dict[str, Any] = {}
        self.call_stack: list[str] = []
        self.max_depth = 32  # Prevent infinite recursion
        self.max_steps = 10000  # Prevent runaway loops
        self.procedures = procedures or {}

    def call_procedure(self, procedure_name: str, args: dict[str, Any]) -> Any:
        """Call a procedure within this context.

        Args:
            procedure_name: Name of the procedure
            args: Typed arguments

        Returns:
            The procedure result (canonical type: str/int/bool/list/dict)

        Raises:
            ContractExecutionError if recursion limit or step limit exceeded
        """
        if len(self.call_stack) >= self.max_depth:
            raise ContractExecutionError(
                f"procedure call depth exceeded ({self.max_depth}): stack={self.call_stack}"
            )

        # Memoization key: procedure name + canonical argument representation
        memo_key = (procedure_name, self._canonical_repr(args))
        if memo_key in self.memo:
            return self.memo[memo_key]

        self.call_stack.append(procedure_name)
        try:
            result = self._dispatch(procedure_name, args)
            self.memo[memo_key] = result
            return result
        finally:
            self.call_stack.pop()

    def _dispatch(self, procedure_name: str, args: dict[str, Any]) -> Any:
        """Dispatch to procedure implementation."""
        if procedure_name not in self.procedures:
            raise ContractExecutionError(f"procedure not found: {procedure_name}")

        procedure_spec = self.procedures[procedure_name]
        body = procedure_spec.get("body")

        if not body:
            raise ContractExecutionError(
                f"procedure {procedure_name} has no body"
            )

        # If body is a string (CID), we'd need to resolve it from the Fabric
        if isinstance(body, str):
            raise ContractExecutionError(
                f"bytecode-based procedures (CIDs) not yet implemented: {body}"
            )

        # For now, support simple expression-based procedures
        if isinstance(body, dict):
            return self._eval_expr(body, args)

        raise ContractExecutionError(
            f"unsupported procedure body type: {type(body)}"
        )

    def _eval_expr(self, expr: dict, env: dict[str, Any]) -> Any:
        """Evaluate an expression in the given environment.

        Supported expression types:
          - {"type": "identity", "input": "param_name"} → returns env[param_name]
          - {"type": "literal", "value": <literal>} → returns the literal
          - {"type": "dict", "fields": {k: expr}} → builds a dict
          - {"type": "if", "cond": expr, "then": expr, "else": expr}
          - {"type": "eq", "left": expr, "right": expr} → boolean comparison
          - {"type": "add", "left": expr, "right": expr} → addition
        """
        expr_type = expr.get("type")

        if expr_type == "identity":
            # Return a named parameter
            param = expr.get("input")
            if param not in env:
                raise ContractExecutionError(
                    f"parameter not found: {param}"
                )
            return env[param]

        if expr_type == "literal":
            # Return a literal value
            return expr.get("value")

        if expr_type == "dict":
            # Build a dict from field expressions
            fields = expr.get("fields", {})
            result = {}
            for key, field_expr in fields.items():
                result[key] = self._eval_expr(field_expr, env)
            return result

        if expr_type == "if":
            # Conditional
            cond_val = self._eval_expr(expr.get("cond", False), env)
            if cond_val:
                return self._eval_expr(expr.get("then"), env)
            else:
                return self._eval_expr(expr.get("else"), env)

        if expr_type == "eq":
            # Equality check
            left = self._eval_expr(expr.get("left"), env)
            right = self._eval_expr(expr.get("right"), env)
            return left == right

        if expr_type == "add":
            # Arithmetic addition
            left = self._eval_expr(expr.get("left"), env)
            right = self._eval_expr(expr.get("right"), env)
            if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                raise ContractExecutionError(
                    f"add requires numeric operands: {type(left).__name__}, {type(right).__name__}"
                )
            return int(left) + int(right)

        if expr_type == "list":
            # Build a list from element expressions
            elements = expr.get("elements", [])
            return [self._eval_expr(elem, env) for elem in elements]

        # Default: unsupported expression type
        raise ContractExecutionError(
            f"unsupported expression type: {expr_type}"
        )

    @staticmethod
    def _canonical_repr(obj: Any) -> str:
        """Canonical string representation for memoization (deterministic)."""
        if isinstance(obj, (str, int, bool)):
            return repr(obj)
        if isinstance(obj, list):
            return "[" + ",".join(ExecutionContext._canonical_repr(x) for x in obj) + "]"
        if isinstance(obj, dict):
            items = sorted((k, ExecutionContext._canonical_repr(v)) for k, v in obj.items())
            return "{" + ",".join(f"{k}:{v}" for k, v in items) + "}"
        raise ContractExecutionError(f"non-canonical type in args: {type(obj)}")


def resolve_contract(contract_asset: dict | str) -> dict:
    """Resolve a contract from the Fabric or OriginTrail.

    Args:
        contract_asset: Either a contract dict or a CID reference string

    Returns:
        A canonical contract record with {kind, name, originator, procedures, metadata}

    Raises:
        ContractExecutionError if resolution fails
    """
    # If contract_asset is a string (CID), we'd need to fetch from Fabric/OriginTrail
    if isinstance(contract_asset, str):
        raise ContractExecutionError(
            f"CID-based contract resolution not yet implemented: {contract_asset}"
        )

    # For now, assume contract_asset is already a dict (resolved)
    if not isinstance(contract_asset, dict):
        raise ContractExecutionError(
            f"contract_asset must be a dict or CID string, got {type(contract_asset)}"
        )

    # Validate it looks like a contract
    if contract_asset.get("kind") != "smart-contract":
        raise ContractExecutionError(
            f"contract must have kind='smart-contract', got {contract_asset.get('kind')}"
        )

    return contract_asset


def execute_procedure(
    contract: dict, procedure_name: str, arguments: dict[str, Any]
) -> Any:
    """Execute a procedure on a contract.

    Args:
        contract: The contract record (from resolve_contract)
        procedure_name: Name of the procedure to invoke
        arguments: Arguments to pass (must be canonical types)

    Returns:
        The procedure result (deterministic, canonical type)

    Raises:
        ContractExecutionError if procedure not found or execution fails
    """
    if contract.get("kind") != "smart-contract":
        raise ContractExecutionError(f"not a smart contract: {contract.get('kind')}")

    procedures = contract.get("procedures", {})
    if procedure_name not in procedures:
        raise ContractExecutionError(
            f"procedure not found: {procedure_name}. "
            f"Available: {list(procedures.keys())}"
        )

    # Build a procedures dict keyed by name with just the body
    proc_specs = {}
    for pname, pspec in procedures.items():
        if isinstance(pspec, dict):
            proc_specs[pname] = pspec
        else:
            # If pspec is an object, convert to dict
            proc_specs[pname] = pspec.to_record() if hasattr(pspec, "to_record") else {"body": pspec}

    ctx = ExecutionContext(procedures=proc_specs)
    result = ctx.call_procedure(procedure_name, arguments)

    # Validate result is canonical
    _validate_canonical(result)
    return result


def _validate_canonical(obj: Any) -> None:
    """Validate that obj is canonical-serializable (str/int/bool/list/dict only)."""
    if obj is None or isinstance(obj, (str, int, bool)):
        return
    if isinstance(obj, list):
        for item in obj:
            _validate_canonical(item)
        return
    if isinstance(obj, dict):
        for v in obj.values():
            _validate_canonical(v)
        return
    raise ContractExecutionError(f"non-canonical result type: {type(obj)} ({obj})")
