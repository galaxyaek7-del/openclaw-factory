"""Guard for scripts/start_factory_supervised.ps1 (F2): it must not start a second server."""
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "start_factory_supervised.ps1"


class StartScriptGuard(unittest.TestCase):
    def setUp(self):
        self.text = SCRIPT.read_text(encoding="utf-8")

    def test_server_guard_is_a_real_tcp_connect(self):
        # Get-NetTCPConnection -State Listen returned nothing for a live listener on this
        # machine (2026-11-05), so the old guard would have started a duplicate server.
        self.assertIn("System.Net.Sockets.TcpClient", self.text)
        self.assertNotIn("-State Listen", self.text.replace("# ", "#").split("function Start-Supervised")[0]
                         .replace("Get-NetTCPConnection -State Listen is", ""), "no live use of the cmdlet")

    def test_loop_guard_and_dry_run_exist(self):
        self.assertIn("factory_loop" + chr(92) + ".js", self.text)
        self.assertIn("[switch]$DryRun", self.text)


if __name__ == "__main__":
    unittest.main()
