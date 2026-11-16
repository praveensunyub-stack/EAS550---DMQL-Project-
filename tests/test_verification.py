"""Check that evidence detects changed content even at unchanged row counts."""
import copy
from decimal import Decimal
import unittest
from src.verify_ingestion import table_fingerprint


class FingerprintTests(unittest.TestCase):
    def test_measure_change_with_same_keys_changes_content_hash(self):
        first = [{"id": "a", "cost": Decimal("1.00")}, {"id": "b", "cost": Decimal("2.00")}]
        second = copy.deepcopy(first)
        # Even the total remains equal; the full row comparison must detect it.
        second[0]["cost"], second[1]["cost"] = second[1]["cost"], second[0]["cost"]
        a = table_fingerprint(first, ("id", "cost"))
        b = table_fingerprint(second, ("id", "cost"))
        self.assertEqual(a["row_count"], b["row_count"])
        self.assertEqual(a["key_sha256"], b["key_sha256"])
        self.assertNotEqual(a["content_sha256"], b["content_sha256"])

    def test_row_order_does_not_change_hash(self):
        rows = [{"id": "b", "text": "a|b"}, {"id": "a", "text": None}]
        self.assertEqual(table_fingerprint(rows, ("id", "text")), table_fingerprint(rows[::-1], ("id", "text")))

    def test_key_change_preserving_count_is_detected(self):
        self.assertNotEqual(table_fingerprint([{"id": "a"}], ("id",))["key_sha256"],
                            table_fingerprint([{"id": "b"}], ("id",))["key_sha256"])


if __name__ == "__main__":
    unittest.main()
