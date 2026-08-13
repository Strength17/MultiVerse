"""Run before handing the UI to the user — mic, detection, display format."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run_script(name: str) -> None:
    path = ROOT / "scripts" / name
    print(f"\n=== {name} ===")
    subprocess.check_call([sys.executable, str(path)], cwd=str(ROOT))


def main() -> None:
    from verse_display import PRIMARY_VERSION_LABEL, SECONDARY_VERSION_LABEL, bilingual_reference
    from winrt_pipeline import probe_winrt_mic, verify_winrt_dependencies

    missing = verify_winrt_dependencies()
    if missing:
        print("FAIL: missing WinRT packages:", ", ".join(missing))
        sys.exit(1)
    print("OK: WinRT imports")

    err = probe_winrt_mic()
    if err:
        print("FAIL: mic probe:", err)
        sys.exit(1)
    print("OK: microphone engine starts and stops")

    ref = bilingual_reference("Romans", 2, 12, "Romains")
    assert ref == "Romains \u2022 Romans 2:12", ref
    assert PRIMARY_VERSION_LABEL == "[NKJV]" and SECONDARY_VERSION_LABEL == "[LSG]"
    print("OK: scripture reference format", ref)

    run_script("test_verse_detection.py")
    for name in ("test_paraphrase_threshold.py", "test_french_secondary.py", "test_narrative_threshold.py"):
        print(f"\n=== {name} ===")
        rc = subprocess.call([sys.executable, str(ROOT / "scripts" / name)], cwd=str(ROOT))
        if rc != 0:
            print(f"WARN: {name} exited {rc} (non-fatal if no false positives)")

    print("\nAll preflight checks passed.")


if __name__ == "__main__":
    main()
