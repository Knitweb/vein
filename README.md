# vein — Smart Contract Procedure Engine

The vein (Ader) through which Pulse's logic flows. Deterministic, verifiable smart contract stored procedures as Proof-of-Useful-Work (PoUW) jobs.

## Architecture

```
Pulse (Hartslag)  →  triggers, clock, state-machine events
   ↓
Vein (Ader)  →  channels logic & data, executes smart contract procedures
   ↓
Settlement  →  verifiable, deterministic results settle in the ledger
```

## Design

**vein** provides:

- **SmartContractProcedureJob** — specification for calling a stored procedure on a contract
- **ExecutionContext** — deterministic sandbox for pure procedure execution
- **Expression evaluator** — support for simple logic, arithmetic, conditionals (MVP)
- **Bytecode format** — extensible path to EVM/Solidity compatibility
- **Fabric integration** — contracts as weaved records in the Knitweb P2P graph
- **PoUW settlement** — uniform (deterministic) verification policy for reward settlement

## Modules

```
src/knitweb_vein/
  __init__.py
  contract.py          — SmartContractProcedureJob, ContractProof, execute/verify
  executor.py          — ExecutionContext, expression evaluator, contract resolution
  items.py             — SmartContractRecord, ProcedureSpec (Fabric weaveable)
```

## Example

```python
from knitweb_vein import SmartContractProcedureJob, execute, verify

# Define a contract (stored in Fabric, weaved via Pulse)
contract = {
    "kind": "smart-contract",
    "name": "SettlementVault",
    "originator": pub_key,
    "procedures": {
        "transfer": {
            "name": "transfer",
            "params": {"from": "str", "to": "str", "amount": "int"},
            "body": {
                "type": "dict",
                "fields": {
                    "sender": {"type": "identity", "input": "from"},
                    "recipient": {"type": "identity", "input": "to"},
                    "value": {"type": "identity", "input": "amount"},
                }
            },
            "returns": "dict",
        }
    },
}

# Create a job (spider's work specification)
job = SmartContractProcedureJob(
    contract_asset=contract,
    procedure_name="transfer",
    arguments={"from": "alice", "to": "bob", "amount": 100},
    originator_pub=pub_key,
)

# Execute (Pulse triggers this; spider does the work)
proof = execute(job, private_key)

# Verify (sampled re-execution for settlement)
is_valid = verify(job, proof)
assert is_valid
```

## Integration with Knitweb

- **Pulse**: imports vein; registers "smart-contract-procedure" job class in PoUW
- **Molgang**: invokes contracts via the P2P settlement layer
- **Ledgerfield**: uses contracts for DAO voting, treaty settlement procedures
- **FinField**: deterministic on-chain oracle callbacks

## Future Extensions

- **EVM bytecode**: execute Solidity contracts deterministically
- **Cross-chain oracle**: verify on-chain procedure calls
- **Result attestation**: swarm-encoded result distribution for large outputs
- **Native gates**: ZK-circuit compilation for procedures
