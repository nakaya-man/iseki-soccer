"""
X(旧Twitter)収集スクリプト
- config/sources.json の "type": "x_api" になっている情報源(例: Fabrizio Romano)の
  最新投稿をX API v2で取得する
- リツイート・リプライは除外し、本人の投稿のみを対象にする
- collect.py が生成する data/pending_summarize.json に追記する形で保存する

必要な環境変数:
  X_BEARER_TOKEN  … X Developer Portal(pay-per-use)で発行したBearerトークン

注意:
  X APIは2026年から完全従量課金(1件読み取り約0.005ドル)。
  1アカウント・1日1回の取得であれば月々のコストはごく小さい(概算は運用ドキュメント参照)。
"""
import json
import os
import hashlib
import requests
from datetime import datetime, timezone

SOURCES_PATH = "config/sources.json"
PENDING_PATH = "data/pending_summarize.json"
RAW_ITEMS_PATH = "data/raw_items.json"
USER_ID_CACHE_PATH = "data/x_user_id_cache.json"

X_API_BASE = "https://api.x.com/2"

TRANSFER_KEYWORDS = [
    "here we go", "deal", "signing", "signs", "loan", "medical",
    "agreement", "transfer", "fee", "official", "joins", "confirmed",
    "移籍", "完全移籍", "レンタル移籍", "加入", "退団", "契約", "合意", "オファー"
]


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_id(link, title):
    return hashlib.sha1((link + title).encode("utf-8")).hexdigest()[:12]


def get_user_id(username, headers, cache):
    if username in cache:
        return cache[username]
    resp = requests.get(f"{X_API_BASE}/users/by/username/{username}", headers=headers)
    resp.raise_for_status()
    user_id = resp.json()["data"]["id"]
    cache[username] = user_id
    return user_id


def fetch_recent_posts(user_id, headers, max_results=10):
    params = {
        "max_results": max_results,
        "exclude": "retweets,replies",
        "tweet.fields": "created_at,text",
    }
    resp = requests.get(f"{X_API_BASE}/users/{user_id}/tweets", headers=headers, params=params)
    resp.raise_for_status()
    return resp.json().get("data", [])


def main():
    token = os.environ.get("X_BEARER_TOKEN")
    sources = [s for s in load_json(SOURCES_PATH, []) if s.get("type") == "x_api"]

    if not token:
        print("X_BEARER_TOKEN が設定されていないため、Xの収集をスキップします")
        return
    if not sources:
        print("X APIタイプの情報源が設定されていません")
        return

    headers = {"Authorization": f"Bearer {token}"}
    user_id_cache = load_json(USER_ID_CACHE_PATH, {})

    pending = load_json(PENDING_PATH, [])
    existing_items = load_json(RAW_ITEMS_PATH, [])
    existing_ids = {item["id"] for item in existing_items}

    new_items = []

    for source in sources:
        try:
            user_id = get_user_id(source["username"], headers, user_id_cache)
            posts = fetch_recent_posts(user_id, headers)
        except requests.HTTPError as e:
            print(f"取得に失敗しました({source['name']}): {e}")
            continue

        for post in posts:
            text = post.get("text", "")
            if not any(k in text.lower() for k in TRANSFER_KEYWORDS):
                continue

            link = f"https://x.com/{source['username']}/status/{post['id']}"
            item_id = make_id(link, text[:50])
            if item_id in existing_ids:
                continue

            new_items.append({
                "id": item_id,
                "title": text[:80],
                "summary_raw": text,
                "link": link,
                "published": post.get("created_at", datetime.now(timezone.utc).isoformat()),
                "source_name": source["name"],
                "source_tier": source["tier"],
                "league": source["league"],
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })
            existing_ids.add(item_id)

    save_json(USER_ID_CACHE_PATH, user_id_cache)
    save_json(PENDING_PATH, pending + new_items)
    save_json(RAW_ITEMS_PATH, existing_items + new_items)

    print(f"X収集完了: 新着 {len(new_items)} 件")


if __name__ == "__main__":
    main()
