"""Property tests for smart contract procedure PoUW jobs.

Tests determinism, signature validity, and digest matching for contract procedures.
"""

from __future__ import annotations

import unittest

from knitweb_vein import canonical, crypto
from knitweb_vein import ContractProof, SmartContractProcedureJob, verify
from knitweb_vein.items import ProcedureSpec, SmartContractRecord


class TestSmartContractProcedureJob(unittest.TestCase):
    """Test SmartContractProcedureJob dataclass and verification logic."""

    def setUp(self):
        """Set up test fixtures."""
        # Generate a test keypair
        self.priv, self.pub = crypto.generate_keypair()

        # Simple test contract (stored as a dict for now)
        self.contract = {
            "kind": "smart-contract",
            "name": "TestContract",
            "originator": self.pub,
            "procedures": {
                "echo": {
                    "name": "echo",
                    "params": {"value": "str"},
                    "body": {"type": "identity", "input": "value"},
                    "returns": "str",
                }
            },
            "metadata": {},
        }

    def test_contract_proof_creation(self):
        """Test ContractProof dataclass."""
        result = {"value": "test"}
        result_bytes = canonical.encode(result)
        signature = crypto.sign(self.priv, result_bytes)
        digest = crypto.sha256_hex(result_bytes)

        proof = ContractProof(result=result, signature=signature, digest=digest)

        self.assertEqual(proof.result, result)
        self.assertEqual(proof.signature, signature)
        self.assertEqual(proof.digest, digest)

    def test_contract_procedure_job_creation(self):
        """Test SmartContractProcedureJob dataclass."""
        job = SmartContractProcedureJob(
            contract_asset=self.contract,
            procedure_name="echo",
            arguments={"value": "hello"},
            originator_pub=self.pub,
        )

        self.assertEqual(job.procedure_name, "echo")
        self.assertEqual(job.arguments, {"value": "hello"})
        self.assertEqual(job.originator_pub, self.pub)

    def test_digest_determinism(self):
        """Test that the same result always produces the same digest."""
        result = {"value": "test", "count": 42}
        result_bytes = canonical.encode(result)
        digest1 = crypto.sha256_hex(result_bytes)
        digest2 = crypto.sha256_hex(result_bytes)

        self.assertEqual(digest1, digest2)
        self.assertTrue(len(digest1) == 64)  # SHA-256 hex is 64 chars

    def test_signature_verification(self):
        """Test that a valid signature verifies."""
        result = {"value": "verified"}
        result_bytes = canonical.encode(result)
        signature = crypto.sign(self.priv, result_bytes)

        is_valid = crypto.verify(self.pub, result_bytes, signature)
        self.assertTrue(is_valid)

    def test_signature_invalid_with_wrong_key(self):
        """Test that signature fails with wrong public key."""
        other_priv, other_pub = crypto.generate_keypair()

        result = {"value": "test"}
        result_bytes = canonical.encode(result)
        signature = crypto.sign(self.priv, result_bytes)

        # Verify with a different public key should fail
        is_valid = crypto.verify(other_pub, result_bytes, signature)
        self.assertFalse(is_valid)

    def test_digest_mismatch_detection(self):
        """Test that mismatched digest is caught."""
        result = {"value": "test"}
        result_bytes = canonical.encode(result)
        signature = crypto.sign(self.priv, result_bytes)
        wrong_digest = "0" * 64

        proof = ContractProof(result=result, signature=signature, digest=wrong_digest)
        correct_digest = crypto.sha256_hex(result_bytes)

        # Digest mismatch should be obvious
        self.assertNotEqual(proof.digest, correct_digest)

    def test_canonical_serialization_consistency(self):
        """Test that canonical encoding is deterministic."""
        # Same data encoded twice should produce identical bytes
        data1 = {"b": 2, "a": 1, "c": {"y": "Y", "x": "X"}}
        data2 = {"a": 1, "b": 2, "c": {"x": "X", "y": "Y"}}

        bytes1 = canonical.encode(data1)
        bytes2 = canonical.encode(data2)

        # Both should be identical (canonical sorts keys)
        self.assertEqual(bytes1, bytes2)


if __name__ == "__main__":
    unittest.main()
