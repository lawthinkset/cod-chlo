import os
import sys
import json
import time
import random
import datetime
import subprocess
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
REELS_DIR = BASE_DIR / "reels"
REELS_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR = BASE_DIR / "raw_record"
RAW_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = BASE_DIR / "history.json"

# ==========================================
# 1. HISTORY & REPETITION PREVENTION
# ==========================================
def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_to_history(topic_entry):
    history = load_history()
    history.append(topic_entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# ==========================================
# 2. AI TOPIC & PUZZLE GENERATOR (POLLINATIONS GEMINI)
# ==========================================
def generate_daily_topic(language: str = "python", mode: str = "auto") -> dict:
    """
    mode: 'trick', 'puzzle', or 'auto' (alternates between senior tricks and coding brainteasers)
    """
    api_key = os.environ.get("POLLINATIONS_API_KEY")
    if not api_key:
        raise ValueError("POLLINATIONS_API_KEY environment variable is not set!")

    history = load_history()
    past_topics = [h.get("topic_id", "") for h in history[-40:] if h.get("topic_id")]

    # Alternate between tricks and coding puzzles/brainteasers
    if mode == "auto":
        mode = random.choice(["trick", "puzzle"])

    avoid_clause = ""
    if past_topics:
        avoid_clause = f"Do NOT repeat any of these previously covered topics: {', '.join(past_topics)}."

    if mode == "puzzle":
        prompt = f"""You are a senior software engineer creating a viral 25-30 second coding PUZZLE / BRAINTEASER for programmers on Instagram and Facebook.
Target Language: {language.upper()}.
{avoid_clause}

CRITICAL RULES:
1. Topic: A clever coding puzzle, counter-intuitive language quirk, or algorithmic brainteaser (e.g. mutable default arguments, float precision quirks, Python 'is' vs '==', tuple immutability trap, or short puzzle).
2. Bad code (The Trap): 2 to 3 lines showing the trap / puzzle that fools 90% of developers.
3. Good code (The Fix/Explanation): 2 to 3 lines showing the correct, bug-free pro pattern.
4. Title: Catchy puzzle hook (e.g. 'Can You Solve This Python Trap? 🧠', '90% Of Devs Get This Wrong!').
5. Voiceover script: 35 to 45 words. Punchy, confident, engaging.
   - Start with a direct challenge hook.
   - Explain why the trap fails and how the fix works.
   - End with: 'Save this for your next interview and follow for daily coding puzzles.'
6. Output raw JSON only.
"""
    else:
        prompt = f"""You are a senior software engineer creating a high-signal 25-30 second coding PRO TIP for programmers on Instagram and Facebook.
Target Language: {language.upper()}.
{avoid_clause}

CRITICAL RULES:
1. Topic: Practical, production-grade idiomatic trick (e.g. pathlib, dataclasses, contextlib, modern dict methods, itertools, walrus operator, zip strict, typing).
2. Bad code: 2 to 3 lines showing the clunky, redundant, or outdated idiom.
3. Good code: 2 to 3 lines showing the clean, idiomatic senior solution.
4. Title: Punchy headline under 7 words (e.g. 'Stop Using Nested Loops in Python! 🚀').
5. Voiceover script: 35 to 45 words. Authoritative, natural, conversational.
   - Call out the clunky habit.
   - Explain the pro alternative clearly without reading punctuation marks.
   - End with: 'Save this for your next project and follow for daily coding tips.'
6. Output raw JSON only.
"""

    prompt += f"""
Output ONLY valid JSON with no markdown wrapping:
{{
  "topic_id": "unique_slug",
  "title": "Clean Headline",
  "category": "{mode}",
  "language": "{language.lower()}",
  "file_name": "example.py",
  "bad_label": "❌ The Trap / Clunky Way",
  "bad_code": "code lines",
  "good_label": "✅ The Pro Way",
  "good_code": "code lines",
  "script_narration": "Narration text here",
  "caption": "Professional caption with 5 relevant hashtags"
}}
"""

    url = "https://gen.pollinations.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    models_to_try = ["google/gemini-2.5-flash-lite", "google/gemini-3.8-flash", "google/gemini-3.5-flash-lite"]
    last_err = None

    for model in models_to_try:
        print(f"[*] Querying Gemini ({model}) for fresh {mode.upper()}...")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a senior principal engineer. Return ONLY raw JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=45)
            if res.ok:
                raw = res.json()["choices"][0]["message"]["content"]
                clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                data = json.loads(clean)
                print(f"[+] Generated topic ({mode}): {data.get('title')}")
                return data
            else:
                last_err = f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            last_err = str(e)
            print(f"[-] Attempt failed: {e}. Trying fallback model...")

    raise RuntimeError(f"Failed to generate topic with Gemini: {last_err}")

# ==========================================
# 3. VOICEOVER & WORD-LEVEL WHISPER TIMINGS
# ==========================================
def generate_voiceover_and_words(text: str, audio_path: Path, voice: str = "adam") -> list:
    api_key = os.environ.get("POLLINATIONS_API_KEY")
    words_data = []

    # 1. ElevenLabs Adam Voice via Pollinations
    if api_key and voice.lower() == "adam":
        try:
            print("[*] Generating voiceover using ElevenLabs 'Adam' via Pollinations...")
            speech_url = "https://gen.pollinations.ai/v1/audio/speech"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "elevenlabs/eleven-flash-v2.5",
                "input": text,
                "voice": "adam"
            }
            res = requests.post(speech_url, headers=headers, json=payload, timeout=45)
            if res.ok:
                with open(audio_path, "wb") as f:
                    f.write(res.content)
                print(f"[+] Audio generated ({len(res.content)} bytes).")

                # Transcribe with Whisper to get word-level timestamps
                print("[*] Extracting word timestamps with OpenAI Whisper...")
                transcribe_url = "https://gen.pollinations.ai/v1/audio/transcriptions"
                trans_headers = {"Authorization": f"Bearer {api_key}"}
                with open(audio_path, "rb") as af:
                    files = {"file": ("audio.mp3", af, "audio/mpeg")}
                    data = {
                        "model": "openai/whisper-large-v3",
                        "response_format": "verbose_json",
                        "timestamp_granularities[]": "word"
                    }
                    t_res = requests.post(transcribe_url, headers=trans_headers, files=files, data=data, timeout=45)

                if t_res.ok:
                    rj = t_res.json()
                    raw_words = rj.get("words", [])
                    if raw_words:
                        for w in raw_words:
                            clean_w = w.get("word", "").strip()
                            if clean_w:
                                words_data.append({
                                    "word": clean_w,
                                    "start": float(w.get("start", 0)),
                                    "end": float(w.get("end", 0))
                                })
                        print(f"[+] Extracted {len(words_data)} word timestamps.")
                        return words_data
        except Exception as e:
            print(f"[-] ElevenLabs Adam attempt failed: {e}. Falling back to edge-tts.")

    # 2. Fallback: Edge-TTS
    print("[*] Using edge-tts fallback...")
    vtt_temp = BASE_DIR / "temp_fallback.vtt"
    cmd = [
        "edge-tts",
        "--text", text,
        "--voice", "en-US-ChristopherNeural",
        "--write-media", str(audio_path),
        "--write-subtitles", str(vtt_temp)
    ]
    subprocess.run(cmd, check=True)

    if vtt_temp.exists():
        with open(vtt_temp, "r", encoding="utf-8") as vf:
            lines = vf.readlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if "-->" in line:
                s_str, e_str = line.split("-->")
                def parse_t(t_val):
                    parts = t_val.strip().replace(',', '.').split(':')
                    if len(parts) == 3: return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
                    return float(parts[0])*60 + float(parts[1])
                start_t = parse_t(s_str)
                end_t = parse_t(e_str)
                i += 1
                txt = lines[i].strip() if i < len(lines) else ""
                words_list = txt.split()
                if words_list:
                    step = (end_t - start_t) / len(words_list)
                    for idx, w in enumerate(words_list):
                        words_data.append({
                            "word": w,
                            "start": round(start_t + (idx * step), 2),
                            "end": round(start_t + ((idx + 1) * step), 2)
                        })
            i += 1

    return words_data

def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

def group_words_into_lines(words: list, max_words: int = 5) -> list:
    lines = []
    cur = []
    for w in words:
        cur.append(w)
        txt = w["word"].strip()
        has_p = any(txt.endswith(p) for p in [".", "!", "?", ","])
        if len(cur) >= max_words or (has_p and len(cur) >= 3):
            lines.append({
                "start": cur[0]["start"],
                "end": cur[-1]["end"],
                "words": cur
            })
            cur = []
    if cur:
        lines.append({
            "start": cur[0]["start"],
            "end": cur[-1]["end"],
            "words": cur
        })
    return lines

# ==========================================
# 4. REALISTIC VS CODE HTML TEMPLATE
# ==========================================
def build_html_template(data: dict, total_duration: float, subtitle_lines: list, html_path: Path):
    subtitles_json = json.dumps(subtitle_lines)
    data_json = json.dumps(data)

    typing_start_sec = max(5.0, total_duration * 0.33)
    typing_duration_sec = 2.5

    file_name = data.get("file_name", "main.py")
    title_text = data.get("title", "Coding Pro Tip")
    category = data.get("category", "trick").upper()
    badge_label = "🧠 CODING PUZZLE" if category == "PUZZLE" else "💡 SENIOR PRO TIP"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js"></script>
<style>
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
    body {{
        width: 1080px;
        height: 1920px;
        background: #0d0f17;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        padding: 95px 45px 50px;
        position: relative;
    }}

    .bg-vignette {{
        position: absolute;
        width: 100%;
        height: 100%;
        top: 0;
        left: 0;
        background: radial-gradient(circle at 50% 25%, rgba(30, 35, 55, 0.45) 0%, rgba(13, 15, 23, 0.95) 75%);
        pointer-events: none;
    }}

    .header {{
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        z-index: 10;
        margin-bottom: 35px;
    }}
    .badge {{
        background: rgba(56, 189, 248, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.35);
        color: #38bdf8;
        padding: 8px 24px;
        border-radius: 999px;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 14px;
    }}
    .title {{
        color: #f8fafc;
        font-size: 50px;
        font-weight: 800;
        line-height: 1.25;
        letter-spacing: -0.5px;
        max-width: 950px;
        text-shadow: 0 4px 20px rgba(0,0,0,0.7);
    }}

    .editors-wrapper {{
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 32px;
        z-index: 10;
    }}

    .vscode-container {{
        width: 100%;
        background: #1e1e1e;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 25px 60px rgba(0, 0, 0, 0.65);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        transition: all 0.5s ease;
    }}

    .title-bar {{
        background: #323233;
        height: 48px;
        display: flex;
        align-items: center;
        padding: 0 18px;
        border-bottom: 1px solid #252526;
        user-select: none;
    }}
    .traffic-lights {{
        display: flex;
        gap: 9px;
    }}
    .dot {{
        width: 14px;
        height: 14px;
        border-radius: 50%;
    }}
    .dot.red {{ background: #ff5f56; }}
    .dot.yellow {{ background: #ffbd2e; }}
    .dot.green {{ background: #27c93f; }}

    .window-title {{
        flex: 1;
        text-align: center;
        color: #cccccc;
        font-size: 17px;
        font-weight: 500;
        letter-spacing: 0.3px;
    }}

    .editor-layout {{
        display: flex;
        min-height: 320px;
        background: #1e1e1e;
    }}

    .activity-bar {{
        width: 58px;
        background: #333333;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding-top: 14px;
        gap: 20px;
        border-right: 1px solid #252526;
    }}
    .activity-icon {{
        width: 24px;
        height: 24px;
        opacity: 0.5;
        fill: #ffffff;
    }}
    .activity-icon.active {{
        opacity: 1;
        position: relative;
    }}
    .activity-icon.active::before {{
        content: '';
        position: absolute;
        left: -17px;
        top: 2px;
        width: 3px;
        height: 20px;
        background: #ffffff;
    }}

    .main-editor {{
        flex: 1;
        display: flex;
        flex-direction: column;
        background: #1e1e1e;
        overflow: hidden;
    }}

    .tabs-bar {{
        background: #252526;
        height: 42px;
        display: flex;
        align-items: center;
        border-bottom: 1px solid #1e1e1e;
    }}
    .tab {{
        background: #1e1e1e;
        color: #ffffff;
        height: 100%;
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0 18px;
        font-size: 18px;
        font-family: "Consolas", monospace;
        border-top: 2px solid #007acc;
        border-right: 1px solid #252526;
    }}
    .tab .py-icon {{
        color: #38bdf8;
        font-weight: 800;
        font-size: 16px;
    }}
    .tab .close-btn {{
        margin-left: 8px;
        color: #858585;
        font-size: 15px;
    }}

    .breadcrumbs {{
        background: #1e1e1e;
        height: 30px;
        display: flex;
        align-items: center;
        padding: 0 20px;
        font-size: 15px;
        color: #8c8c8c;
        gap: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }}
    .breadcrumbs span.active {{
        color: #cccccc;
    }}

    .code-content {{
        padding: 22px 18px;
        font-family: "Consolas", "Fira Code", monospace;
        font-size: 28px;
        line-height: 1.6;
        color: #d4d4d4;
        flex: 1;
    }}
    .code-line {{
        display: flex;
        align-items: center;
        min-height: 44px;
        padding: 0 6px;
        border-radius: 4px;
    }}
    .code-line.active-line {{
        background: rgba(255, 255, 255, 0.05);
    }}
    .line-num {{
        width: 44px;
        color: #6e7681;
        user-select: none;
        font-size: 22px;
        text-align: right;
        margin-right: 24px;
    }}
    .line-text {{
        flex: 1;
        white-space: pre;
    }}

    .typing-cursor {{
        display: inline-block;
        width: 12px;
        height: 28px;
        background: #38bdf8;
        vertical-align: middle;
        margin-left: 2px;
        border-radius: 2px;
        animation: blink 0.65s infinite;
    }}
    @keyframes blink {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0; }}
    }}

    .status-bar {{
        background: #007acc;
        height: 34px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 16px;
        color: #ffffff;
        font-size: 15px;
        font-weight: 500;
    }}
    .status-left, .status-right {{
        display: flex;
        align-items: center;
        gap: 14px;
    }}

    #bad-editor.dimmed {{
        opacity: 0.38;
        filter: grayscale(40%);
        transform: scale(0.98);
    }}

    #good-editor {{
        opacity: 0;
        transform: translateY(25px);
        border: 1.5px solid rgba(56, 189, 248, 0.6);
        box-shadow: 0 25px 60px rgba(0, 0, 0, 0.75), 0 0 35px rgba(56, 189, 248, 0.15);
    }}
    #good-editor.visible {{
        opacity: 1;
        transform: translateY(0);
    }}

    /* Safe Zone Single-Line Highlighter Subtitles */
    .caption-container {{
        position: absolute;
        bottom: 540px; /* Safe zone above Reels bottom controls */
        left: 50%;
        transform: translateX(-50%);
        width: 960px;
        text-align: center;
        z-index: 100;
        display: flex;
        justify-content: center;
        pointer-events: none;
        min-height: 90px;
    }}

    .caption-line {{
        background: rgba(15, 18, 28, 0.88);
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(12px);
        padding: 14px 28px;
        border-radius: 16px;
        font-size: 38px;
        font-weight: 700;
        letter-spacing: -0.3px;
        line-height: 1.4;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
        display: inline-flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: center;
        transition: opacity 0.2s ease;
    }}

    .sub-word {{
        color: rgba(255, 255, 255, 0.5);
        padding: 2px 6px;
        border-radius: 6px;
        transition: all 0.1s ease;
    }}
    .sub-word.passed {{
        color: #ffffff;
    }}
    .sub-word.active {{
        color: #09090b;
        background: #facc15; /* Clean yellow highlighter marker */
        font-weight: 800;
        transform: scale(1.05);
        box-shadow: 0 0 16px rgba(250, 204, 21, 0.4);
    }}
</style>
</head>
<body>

    <div class="bg-vignette"></div>

    <div class="header">
        <div class="badge">{badge_label}</div>
        <h1 class="title">{title_text}</h1>
    </div>

    <div class="editors-wrapper">
        <div class="vscode-container" id="bad-editor">
            <div class="title-bar">
                <div class="traffic-lights">
                    <span class="dot red"></span>
                    <span class="dot yellow"></span>
                    <span class="dot green"></span>
                </div>
                <div class="window-title">{file_name} — Visual Studio Code</div>
            </div>

            <div class="editor-layout">
                <div class="activity-bar">
                    <svg class="activity-icon active" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14H6v-2h6v2zm4-4H6v-2h10v2zm0-4H6V7h10v2z"/></svg>
                    <svg class="activity-icon" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                    <svg class="activity-icon" viewBox="0 0 24 24"><circle cx="12" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="18" r="3"/><path d="M12 9v3m-4.5 4.5l3-3m4.5 3l-3-3" stroke="#fff" stroke-width="2"/></svg>
                </div>

                <div class="main-editor">
                    <div class="tabs-bar">
                        <div class="tab">
                            <span class="py-icon">🐍</span>
                            <span>{file_name}</span>
                            <span class="close-btn">×</span>
                        </div>
                    </div>
                    <div class="breadcrumbs">
                        <span>src</span> <span>›</span> <span>legacy</span> <span>›</span> <span class="active">{file_name}</span>
                    </div>
                    <div class="code-content" id="bad-code-body"></div>
                </div>
            </div>

            <div class="status-bar">
                <div class="status-left">
                    <span>🔀 main*</span>
                    <span>⊗ 0  ⚠ 0</span>
                </div>
                <div class="status-right">
                    <span>Ln 3, Col 18</span>
                    <span>Spaces: 4</span>
                    <span>UTF-8</span>
                    <span>Python 3.12</span>
                </div>
            </div>
        </div>

        <div class="vscode-container" id="good-editor">
            <div class="title-bar" style="background: #232734;">
                <div class="traffic-lights">
                    <span class="dot red"></span>
                    <span class="dot yellow"></span>
                    <span class="dot green"></span>
                </div>
                <div class="window-title" style="color: #38bdf8; font-weight: 600;">pro_{file_name} — Visual Studio Code</div>
            </div>

            <div class="editor-layout">
                <div class="main-editor">
                    <div class="tabs-bar">
                        <div class="tab" style="border-top-color: #38bdf8;">
                            <span class="py-icon">⚡</span>
                            <span>pro_{file_name}</span>
                            <span class="close-btn">×</span>
                        </div>
                    </div>
                    <div class="breadcrumbs">
                        <span>src</span> <span>›</span> <span>clean_code</span> <span>›</span> <span class="active">pro_{file_name}</span>
                    </div>
                    <div class="code-content" id="good-code-body"></div>
                </div>
            </div>

            <div class="status-bar" style="background: #0284c7;">
                <div class="status-left">
                    <span>🔀 feature/clean-code</span>
                    <span>✓ 0 errors</span>
                </div>
                <div class="status-right">
                    <span>Ln 3, Col 26</span>
                    <span>Spaces: 4</span>
                    <span>UTF-8</span>
                    <span>Python 3.12</span>
                </div>
            </div>
        </div>
    </div>

    <div class="caption-container">
        <div class="caption-line" id="caption-box"></div>
    </div>

<script>
    const topicData = {data_json};
    const subtitleLines = {subtitles_json};
    const typingStartSec = {typing_start_sec};
    const typingDurationSec = {typing_duration_sec};

    const badEditor = document.getElementById("bad-editor");
    const goodEditor = document.getElementById("good-editor");
    const badBody = document.getElementById("bad-code-body");
    const goodBody = document.getElementById("good-code-body");
    const captionBox = document.getElementById("caption-box");

    const lang = topicData.language === 'javascript' ? 'javascript' : 'python';
    const prismLang = Prism.languages[lang] || Prism.languages.python;

    function renderCode(text, withCursor = false) {{
        const lines = text.split('\\n');
        return lines.map((line, idx) => {{
            const hl = Prism.highlight(line || ' ', prismLang, lang);
            const isLast = (idx === lines.length - 1);
            const activeCls = (withCursor && isLast) ? ' active-line' : '';
            const cursorHtml = (withCursor && isLast) ? '<span class="typing-cursor"></span>' : '';
            return `<div class="code-line${{activeCls}}"><span class="line-num">${{idx + 1}}</span><span class="line-text">${{hl}}${{cursorHtml}}</span></div>`;
        }}).join('');
    }}

    badBody.innerHTML = renderCode(topicData.bad_code, false);

    const fullGoodCode = topicData.good_code;
    const totalChars = fullGoodCode.length;
    let typingHasStarted = false;

    const startTime = performance.now();

    function update() {{
        const elapsed = (performance.now() - startTime) / 1000;

        if (elapsed >= typingStartSec) {{
            if (!typingHasStarted) {{
                typingHasStarted = true;
                badEditor.classList.add("dimmed");
                goodEditor.classList.add("visible");
            }}

            const rawProgress = Math.min(1.0, (elapsed - typingStartSec) / typingDurationSec);
            const progress = Math.min(1.0, Math.pow(rawProgress, 0.85));
            const revealedChars = Math.floor(progress * totalChars);
            const partialCode = fullGoodCode.slice(0, revealedChars);

            const isTypingActive = progress < 1.0;
            goodBody.innerHTML = renderCode(partialCode, isTypingActive);
        }}

        let activeLine = null;
        for (const line of subtitleLines) {{
            if (elapsed >= line.start && elapsed <= (line.end + 0.35)) {{
                activeLine = line;
                break;
            }}
        }}

        if (activeLine) {{
            captionBox.style.display = "inline-flex";
            const renderedWords = activeLine.words.map(w => {{
                let cls = "sub-word";
                if (elapsed >= w.start && elapsed <= w.end) {{
                    cls += " active";
                }} else if (elapsed > w.end) {{
                    cls += " passed";
                }}
                return `<span class="${{cls}}">${{w.word}}</span>`;
            }}).join('');
            captionBox.innerHTML = renderedWords;
        }} else {{
            captionBox.style.display = "none";
        }}

        requestAnimationFrame(update);
    }}

    requestAnimationFrame(update);
</script>

</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] HTML visual template created at: {html_path}")

# ==========================================
# 5. SCREEN RECORDING & FFmpeg ASSEMBLY
# ==========================================
def record_screen(html_path: Path, duration_sec: float, raw_video_path: Path):
    print(f"[*] Recording 1080x1920 video via headless Chromium for {duration_sec:.1f}s...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--font-render-hinting=none", "--enable-font-antialiasing"]
        )
        context = browser.new_context(
            record_video_dir=str(RAW_DIR),
            record_video_size={"width": 1080, "height": 1920},
            viewport={"width": 1080, "height": 1920}
        )
        page = context.new_page()
        page.goto(html_path.resolve().as_uri())

        page.wait_for_timeout(int((duration_sec + 1.2) * 1000))

        context.close()
        browser.close()

    recorded_files = list(RAW_DIR.glob("*.webm"))
    if not recorded_files:
        raise RuntimeError("No recorded video found in Playwright directory.")
    latest_video = max(recorded_files, key=os.path.getctime)
    if raw_video_path.exists():
        raw_video_path.unlink()
    os.rename(latest_video, raw_video_path)
    print(f"[+] Screen recording finished: {raw_video_path}")

def merge_final_video(raw_video: Path, audio_path: Path, output_mp4: Path):
    print("[*] Merging video + audio into final MP4 with FFmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_mp4)
    ]
    subprocess.run(cmd, check=True)
    print(f"[🎉 SUCCESS] Final Reel ready at: {output_mp4}")

# ==========================================
# 6. PIPELINE ORCHESTRATION
# ==========================================
def run_pipeline(language: str = "python", voice: str = "adam", mode: str = "auto"):
    today_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\n==========================================")
    print(f"🚀 RUNNING COD-CHLO PIPELINE ({language.upper()}) - {today_str}")
    print(f"🎤 Voice: {voice.upper()} | Mode: {mode.upper()} | Subtitles: Single-Line Karaoke")
    print(f"==========================================")

    # 1. Generate Topic / Puzzle
    topic_data = generate_daily_topic(language=language, mode=mode)
    topic_id = topic_data.get("topic_id", "daily_tip")

    # Paths
    audio_path = BASE_DIR / "temp_narration.mp3"
    html_path = BASE_DIR / "temp_index.html"
    raw_video = BASE_DIR / "temp_raw_video.webm"
    final_mp4 = REELS_DIR / f"reel_{today_str}_{topic_id}.mp4"
    caption_txt = REELS_DIR / f"reel_{today_str}_{topic_id}_caption.txt"

    # 2. Voiceover & Word-level timestamps
    words = generate_voiceover_and_words(topic_data["script_narration"], audio_path, voice=voice)
    duration = get_audio_duration(audio_path)
    print(f"[*] Voiceover duration: {duration:.2f} seconds | Word cues: {len(words)}")

    # 3. Group words into single-line subtitle phrases
    subtitle_lines = group_words_into_lines(words, max_words=5)

    # 4. Build Clean HTML
    build_html_template(topic_data, duration, subtitle_lines, html_path)

    # 5. Record Screen
    record_screen(html_path, duration, raw_video)

    # 6. Composite Final Reel
    merge_final_video(raw_video, audio_path, final_mp4)

    # 7. Save Caption and Log to History
    with open(caption_txt, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {topic_data.get('title')}\n\n")
        f.write(f"{topic_data.get('caption')}\n")

    save_to_history({
        "timestamp": datetime.datetime.now().isoformat(),
        "topic_id": topic_id,
        "title": topic_data.get("title"),
        "category": topic_data.get("category", "trick"),
        "language": topic_data.get("language"),
        "voice": voice,
        "video_path": str(final_mp4),
        "caption_path": str(caption_txt)
    })

    print(f"\n[✅ ALL DONE!]")
    print(f"📁 Video:   {final_mp4}")
    print(f"📝 Caption: {caption_txt}")
    return final_mp4, caption_txt

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cod-Chlo Reel Generator")
    parser.add_argument("--lang", default="python", help="Programming language (e.g. python, javascript)")
    parser.add_argument("--voice", default="adam", help="Voice model (e.g. adam, christopher)")
    parser.add_argument("--mode", default="auto", choices=["auto", "trick", "puzzle"], help="Content mode: trick, puzzle, or auto")
    args = parser.parse_args()

    run_pipeline(language=args.lang, voice=args.voice, mode=args.mode)
