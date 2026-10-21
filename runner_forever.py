import os
import sys
import time
import random
import datetime
import traceback
from daily_pipeline import run_pipeline

# ==========================================
# RUNNER FOREVER: CONTINUOUS AUTOMATION
# ==========================================
# Runs round after round, generating unique videos indefinitely.
# Automatically rotates languages, picks fresh puzzles/tricks via Pollinations AI,
# logs results, and handles retries if network or API has a temporary hiccup.

LANGUAGES = ["python", "javascript"]
DEFAULT_INTERVAL_HOURS = 24  # Run once every 24 hours (or pass --interval in seconds)

def run_loop(interval_sec: float, max_rounds: int = None):
    round_num = 1
    print("\n" + "=" * 60)
    print("♾️  COD-CHLO: RUNNER FOREVER STARTED")
    print(f"⏰ Interval between videos: {interval_sec} seconds ({interval_sec/3600:.1f} hours)")
    print(f"🌐 Languages: {', '.join(LANGUAGES)}")
    print(f"🧠 Topics: Senior Tricks & Coding Puzzles via Pollinations AI")
    print("=" * 60 + "\n")

    while True:
        lang = random.choice(LANGUAGES)
        mode = "puzzle" if round_num % 2 == 0 else "trick"
        print(f"\n[🔄 ROUND {round_num}] Starting generation ({lang.upper()} - {mode.upper()})...")

        success = False
        attempts = 0
        while not success and attempts < 3:
            attempts += 1
            try:
                video_path, caption_path = run_pipeline(language=lang, voice="adam", mode=mode)
                print(f"[✅ ROUND {round_num} COMPLETE] Video: {video_path}")
                success = True
            except Exception as e:
                print(f"[!] Error on attempt {attempts}: {e}")
                traceback.print_exc()
                if attempts < 3:
                    print("[*] Retrying in 30 seconds with fallback model...")
                    time.sleep(30)
                else:
                    print(f"[-] Round {round_num} failed after 3 attempts. Moving to next interval.")

        if max_rounds and round_num >= max_rounds:
            print(f"\n[🏁] Reached requested limit of {max_rounds} rounds. Exiting.")
            break

        round_num += 1
        next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval_sec)
        print(f"\n[💤 Sleeping for {interval_sec}s. Next generation scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}]")
        time.sleep(interval_sec)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cod-Chlo Runner Forever")
    parser.add_argument("--interval", type=float, default=86400, help="Interval between runs in seconds (default: 86400 = 24h)")
    parser.add_argument("--rounds", type=int, default=None, help="Number of rounds to run (default: infinite)")
    args = parser.parse_args()

    run_loop(interval_sec=args.interval, max_rounds=args.rounds)
