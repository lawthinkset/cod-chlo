# 🚀 Cod-Chlo: Autonomous Daily Code Reels & Shorts Pipeline

[![Daily Code Reel Generator](https://github.com/lawthinkset/cod-chlo/actions/workflows/daily_reel.yml/badge.svg)](https://github.com/lawthinkset/cod-chlo/actions/workflows/daily_reel.yml)

An autonomous system designed to **run continuously forever**, producing high-retention 9:16 vertical videos for Instagram Reels, Facebook Reels, YouTube Shorts, and TikTok.

Every round, it dynamically generates a fresh programming trick or coding puzzle, creates natural AI voiceover narration, types code inside an authentic VS Code editor, and syncs clean single-line karaoke highlighter subtitles positioned safely above mobile controls.

---

## ⚡ Key Features

* **♾️ Runs Forever**: Automatic topic rotation between Python and JavaScript, alternating between senior pro tricks and coding brainteasers / puzzles.
* **🧠 Pollinations AI Brain**: Uses Gemini models to select unique, high-signal topics and construct bug-free code snippets.
* **🛡️ Zero Repetition**: Stores past topics in `history.json` and feeds them back into Gemini to prevent duplicates across rounds.
* **🎙️ ElevenLabs 'Adam' Voice**: Natural, authoritative speech generated via the Pollinations audio endpoint.
* **💬 Single-Line Highlighter Subtitles**: Real-time karaoke highlighter powered by OpenAI Whisper word timestamps. Subtitles sit at `bottom: 540px` to guarantee zero cropping from Instagram / Facebook UI elements.
* **💻 Authentic VS Code UI**: Official Dark+ theme, activity bar, breadcrumbs, line numbers, active line highlight, and fast, snappy typing (~2.5s).
* **📱 Multi-Platform Publisher**: Built-in support for Meta Graph API (Instagram / Facebook Reels) and Telegram notification bots.

---

## 📂 Project Architecture

```
cod-chlo/
├── .github/workflows/
│   └── daily_reel.yml     # Automated cloud runner (runs daily via cron)
├── daily_pipeline.py      # Core video generation pipeline
├── runner_forever.py      # Infinite runner daemon for round-after-round generation
├── publisher.py           # Meta Graph API & Telegram bot uploader
├── history.json           # Permanent database of covered topics
├── run_forever.bat        # 1-click batch launcher for continuous execution
├── requirements.txt       # Python dependencies
└── reels/                 # Destination for final .mp4 and caption.txt files
```

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

Ensure `ffmpeg` is installed and available on your system `PATH`.

### 2. Configure Environment
Set your Pollinations API key in your environment or `.env` file:
```bash
export POLLINATIONS_API_KEY="sk_your_key_here"
```

### 3. Generate a Single Video
```bash
python daily_pipeline.py --lang python --mode auto
```
Options:
* `--lang`: `python` or `javascript`
* `--mode`: `trick` (idiomatic code), `puzzle` (coding brainteaser), or `auto` (alternates each round)
* `--voice`: `adam` (default) or `christopher`

### 4. Run Continuously Forever
To have the script run endlessly, producing 1 video every 24 hours:
```bash
python runner_forever.py --interval 86400
```
Or double-click `run_forever.bat`.

---

## ☁️ Running via GitHub Actions

This repository includes a scheduled GitHub Actions workflow in `.github/workflows/daily_reel.yml`.

1. Go to your repository settings on GitHub: **Settings > Secrets and variables > Actions**.
2. Add your `POLLINATIONS_API_KEY` under **Repository secrets**.
3. The workflow will automatically run every day at `09:00 UTC` and upload the finished video as an artifact, or you can trigger it manually with **Run workflow**.

---

## 📜 License
MIT License
