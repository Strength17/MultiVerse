"""
verify_offline_stt.py  --  STEP 1. Run this BEFORE anything else.

Turn Wi-Fi/Ethernet fully OFF (or Airplane Mode) first -- not just "no signal
nearby," actually disable the adapter in Windows. Then run this script and
speak a few sentences, including a couple of Bible book names. Ctrl+C to stop.

What a PASS looks like:
  - "OK: no network reachable" printed at the top
  - live [hyp] lines appear almost instantly as you talk
  - [FINAL] lines appear at each pause, matching what you said

If it produces no text, or errors on compile_constraints_async, while
genuinely offline: this machine's dictation engine is NOT running on-device
for the WinRT DICTATION topic constraint, and the rest of this bundle should
not be wired in on that assumption -- re-check Windows Settings >
Time & language > Speech > Offline speech recognition for your language pack.
"""

import asyncio
import socket
import sys
import time


def _network_reachable() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=1.5)
        return True
    except OSError:
        return False


async def main():
    print("=" * 60)
    print("MultiVerse -- Windows offline STT verification")
    print("=" * 60)

    if _network_reachable():
        print("!! WARNING: network is still reachable from this machine.")
        print("   Disable Wi-Fi/Ethernet (or Airplane Mode) for this test")
        print("   to actually prove anything. Continuing in 5s anyway...")
        time.sleep(5)
    else:
        print("OK: no network reachable. This is a genuine offline test.")

    try:
        import winrt.windows.media.speechrecognition as speech
    except ImportError:
        print("\nFAILED: winrt speech module not installed.")
        print("Run: pip install -r requirements_winrt.txt --break-system-packages")
        print("  (includes winrt-Windows.Globalization)")
        sys.exit(1)

    recognizer = speech.SpeechRecognizer()
    print(f"Recognizer language: {recognizer.current_language.display_name}")

    recognizer.constraints.append(
        speech.SpeechRecognitionTopicConstraint(
            speech.SpeechRecognitionScenario.DICTATION, "dictation"
        )
    )
    print("Compiling constraints...")
    t0 = time.time()
    compilation = await recognizer.compile_constraints_async()
    print(f"Compiled in {time.time() - t0:.2f}s -- status: {compilation.status}")

    if compilation.status != speech.SpeechRecognitionResultStatus.SUCCESS:
        print("FAILED to compile. This engine is not usable on this machine.")
        sys.exit(1)

    last_final_at = time.time()

    def on_hypothesis(sender, args):
        print(f"  [hyp]  {args.hypothesis.text}", end="\r")

    def on_result(sender, args):
        nonlocal last_final_at
        gap = time.time() - last_final_at
        last_final_at = time.time()
        print(f"\n[FINAL +{gap:.2f}s since last]  {args.result.text}")

    recognizer.add_hypothesis_generated(on_hypothesis)
    recognizer.continuous_recognition_session.add_result_generated(on_result)

    await recognizer.continuous_recognition_session.start_async()
    print("\nListening -- speak naturally, try a book name like 'Deuteronomy'.")
    print("Ctrl+C to stop.\n")

    try:
        while True:
            await asyncio.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        await recognizer.continuous_recognition_session.stop_async()
        print("\nStopped. If you saw [FINAL] lines above while offline, proceed to STEP 2.")


if __name__ == "__main__":
    asyncio.run(main())
