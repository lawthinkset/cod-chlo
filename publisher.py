import os
import time
import requests
from pathlib import Path

# ==========================================
# AUTO PUBLISHER FOR INSTAGRAM & FACEBOOK
# ==========================================

def publish_to_telegram(video_path: Path, caption: str):
    """Sends the generated video directly to your Telegram bot for 1-tap mobile review."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    print(f"[*] Sending generated reel to Telegram chat {chat_id}...")
    with open(video_path, "rb") as vf:
        res = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption[:1024]},
            files={"video": vf},
            timeout=120
        )
    if res.ok:
        print("[+] Sent successfully to Telegram!")
    else:
        print(f"[-] Telegram upload failed: {res.text}")

def publish_to_meta_graph_api(video_public_url: str, caption: str):
    """
    Publishes to Instagram Reels via official Meta Graph API:
    Requires: INSTAGRAM_ACCOUNT_ID and META_ACCESS_TOKEN
    """
    ig_user_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
    access_token = os.environ.get("META_ACCESS_TOKEN")
    if not ig_user_id or not access_token:
        print("[*] META_ACCESS_TOKEN or INSTAGRAM_ACCOUNT_ID not found in env.")
        return False

    init_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media"
    init_payload = {
        "media_type": "REELS",
        "video_url": video_public_url,
        "caption": caption,
        "access_token": access_token
    }
    r = requests.post(init_url, data=init_payload)
    if not r.ok:
        print(f"[-] Container creation failed: {r.text}")
        return False
    container_id = r.json().get("id")
    print(f"[+] Reel container created: {container_id}. Waiting for processing...")

    status_url = f"https://graph.facebook.com/v19.0/{container_id}"
    for _ in range(30):
        time.sleep(5)
        st_res = requests.get(status_url, params={"fields": "status_code", "access_token": access_token})
        status_code = st_res.json().get("status_code")
        print(f"[*] Processing status: {status_code}")
        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            print("[-] Reel processing error.")
            return False

    pub_url = f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish"
    pub_res = requests.post(pub_url, data={"creation_id": container_id, "access_token": access_token})
    if pub_res.ok:
        post_id = pub_res.json().get("id")
        print(f"[🎉 PUBLISHED!] Reel is live on Instagram! Post ID: {post_id}")
        return True
    else:
        print(f"[-] Publish failed: {pub_res.text}")
        return False
