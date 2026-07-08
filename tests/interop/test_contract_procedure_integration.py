"""Integration tests for smart contract procedures as PoUW jobs.

Tests the full pipeline: contract definition → execution → verification.
"""

from __future__ import annotations

import unittest

from knitweb_vein import canonical, crypto
from knitweb_vein import (
    ContractProof,
    SmartContractProcedureJob,
    execute,
    verify,
)


class TestSmartContractIntegration(unittest.TestCase):
    """Integration tests for contract procedures in the PoUW pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.priv, self.pub = crypto.generate_keypair()

        # Test contract: simple echo procedure
        self.echo_contract = {
            "kind": "smart-contract",
            "name": "EchoContract",
            "originator": self.pub,
            "procedures": {
                "echo": {
                    "name": "echo",
                    "params": {"value": "str"},
                    "body": {
                        "type": "identity",
                        "input": "value",
                    },
                    "returns": "str",
                }
            },
            "metadata": {"version": "1.0"},
        }

        # Test contract: arithmetic procedure
        self.arithmetic_contract = {
            "kind": "smart-contract",
            "name": "ArithmeticContract",
            "originator": self.pub,
            "procedures": {
                "add": {
                    "name": "add",
                    "params": {"a": "int", "b": "int"},
                    "body": {
                        "type": "add",
                        "left": {"type": "identity", "input": "a"},
                        "right": {"type": "identity", "input": "b"},
                    },
                    "returns": "int",
                }
            },
            "metadata": {},
        }

        # Test contract: conditional logic
        self.logic_contract = {
            "kind": "smart-contract",
            "name": "LogicContract",
            "originator": self.pub,
            "procedures": {
                "is_even": {
                    "name": "is_even",
                    "params": {"n": "int"},
                    "body": {
                        "type": "eq",
                        "left": {
                            "type": "add",
                            "left": {"type": "identity", "input": "n"},
                            "right": {"type": "literal", "value": 0},
                        },
                        "right": {"type": "identity", "input": "n"},
                    },
                    "returns": "bool",
                }
            },
            "metadata": {},
        }

    def test_execute_echo_procedure(self):
        """Test executing a simple echo procedure."""
        job = SmartContractProcedureJob(
            contract_asset=self.echo_contract,
            procedure_name="echo",
            arguments={"value": "hello"},
            originator_pub=self.pub,
        )

        proof = execute(job, self.priv)

        # Check result is correct
        self.assertEqual(proof.result, {"value": "hello"})
        # Check digest is valid
        self.assertEqual(len(proof.digest), 64)  # SHA-256 hex
        # Check signature is valid
        result_bytes = canonical.encode(proof.result)
        is_valid = crypto.verify(self.pub, result_bytes, proof.signature)
        self.assertTrue(is_valid)

    def test_execute_arithmetic_procedure(self):
        """Test executing an arithmetic procedure."""
        job = SmartContractProcedureJob(
            contract_asset=self.arithmetic_contract,
            procedure_name="add",
            arguments={"a": 10, "b": 32},
            originator_pub=self.pub,
        )

        proof = execute(job, self.priv)

        # Result should be 10 + 32 = 42
        self.assertEqual(proof.result, {"value": 42})

    def test_verify_valid_proof(self):
        """Test verifying a valid proof."""
        job = SmartContractProcedureJob(
            contract_asset=self.arithmetic_contract,
            procedure_name="add",
            arguments={"a": 10, "b": 32},
            originator_pub=self.pub,
        )

        proof = execute(job, self.priv)
        is_valid = verify(job, proof)

        self.assertTrue(is_valid)

    def test_verify_fails_on_tampered_result(self):
        """Test that verification fails if the result is tampered."""
        job = SmartContractProcedureJob(
            contract_asset=self.arithmetic_contract,
            procedure_name="add",
            arguments={"a": 10, "b": 32},
            originator_pub=self.pub,
        )

        proof = execute(job, self.priv)

        # Tamper with the result
        tampered_result = {"value": 999}
        tampered_proof = ContractProof(
            result=tampered_result,
            signature=proof.signature,
            digest=proof.digest,
        )

        # Verification should fail
        is_valid = verify(job, tampered_proof)
        self.assertFalse(is_valid)

    def test_verify_fails_on_wrong_digest(self):
        """Test that verification fails if digest is wrong."""
        job = SmartContractProcedureJob(
            contract_asset=self.arithmetic_contract,
            procedure_name="add",
            arguments={"a": 10, "b": 32},
            originator_pub=self.pub,
        )

        proof = execute(job, self.priv)

        # Wrong digest
        bad_proof = ContractProof(
            result=proof.result,
            signature=proof.signature,
            digest="0" * 64,
        )

        is_valid = verify(job, bad_proof)
        self.assertFalse(is_valid)

    def test_verify_fails_on_wrong_signature(self):
        """Test that verification fails with an invalid signature."""
        job = SmartContractProcedureJob(
            contract_asset=self.arithmetic_contract,
            procedure_name="add",
            arguments={"a": 10, "b": 32},
            originator_pub=self.pub,
        )

        proof = execute(job, self.priv)

        # Wrong signature
        bad_proof = ContractProof(
            result=proof.result,
            signature="bad" * 20,
            digest=proof.digest,
        )

        is_valid = verify(job, bad_proof)
        self.assertFalse(is_valid)

    def test_deterministic_execution(self):
        """Test that the same job always produces the same result."""
        job = SmartContractProcedureJob(
            contract_asset=self.arithmetic_contract,
            procedure_name="add",
            arguments={"a": 15, "b": 27},
            originator_pub=self.pub,
        )

        # Execute twice
        proof1 = execute(job, self.priv)
        proof2 = execute(job, self.priv)

        # Results should be identical
        self.assertEqual(proof1.result, proof2.result)
        # Digests should be identical
        self.assertEqual(proof1.digest, proof2.digest)

    def test_full_settlement_flow(self):
        """Test the full execute → verify flow."""
        # Multiple jobs, all should verify
        jobs = [
            SmartContractProcedureJob(
                contract_asset=self.arithmetic_contract,
                procedure_name="add",
                arguments={"a": i, "b": i + 1},
                originator_pub=self.pub,
            )
            for i in range(5)
        ]

        for job in jobs:
            proof = execute(job, self.priv)
            is_valid = verify(job, proof)
            self.assertTrue(is_valid, f"Failed to verify job with args {job.arguments}")


if __name__ == "__main__":
    unittest.main()
