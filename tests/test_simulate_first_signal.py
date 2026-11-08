import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_first_signal_simulation_holds_every_expectation():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "simulate_first_signal.py")], cwd=str(ROOT),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-500:]
    assert "19/19 expectations hold" in r.stdout and "[SIMULATION]" in r.stdout
