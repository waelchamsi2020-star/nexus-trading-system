"""Fresh interpreters must not depend on caller import order."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# Vulture review: unittest/pytest discovers and executes this TestCase by module inspection.
class RegistrationOrder(unittest.TestCase):
    def test_each_public_module_can_be_imported_first(self):
        for module in ('local_models', 'specialists', 'extended_models', 'confluence_registry', 'strategies'):
            with self.subTest(module=module):
                command = [sys.executable, '-c',
                           (f'import nexus.{module}; from nexus.strategies import REGISTRY; '
                           'assert len(REGISTRY)==58; '
                           'assert all(m.get("contract",{}).get("rule_version")==m["version"] for m in REGISTRY.values())')]
                result = subprocess.run(command, env=dict(os.environ, PYTHONPATH=str(ROOT/'src')),
                                        check=False, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
