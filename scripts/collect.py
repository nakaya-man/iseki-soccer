"""
情報収集スクリプト
- config/sources.json に登録された情報源(RSS)を巡回
- 移籍関連キーワードを含む記事だけを抽出
- 既に取り込み済みの記事は無視(重複排除)
- 新着記事を data/pending_summarize.json に書き出す(AI要約の入力になる)
"""
import feedparser
import json
import os
import hashlib
from datetime import datetime, timezone

SOURCES_PATH = "config/sources.json"
RAW_ITEMS_PATH = "data/raw_items.json"
PENDING_PATH = "data/pending_summarize.json"

# 移籍関連と判定するキーワード(英語ソース向け。ソース追加時に増やしていく)
TRANSFER_KEYWORDS = [
    "transfer", "signs", "signing", "loan", "move to", "deal agreed",
    "here we go", "medical", "completes move", "confirmed", "unveiled",
    "joins", "agreement", "fee"
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


def is_transfer_related(title, summary):
    text = f"{title} {summary}".lower()
    return any(keyword in text for keyword in TRANSFER_KEYWORDS)


def make_id(link, title):
    return hashlib.sha1((link + title).encode("utf-8")).hexdigest()[:12]


def main():
    sources = [s for s in load_json(SOURCES_PATH, []) if s.get("type", "rss") == "rss"]
    existing_items = load_json(RAW_ITEMS_PATH, [])
    existing_ids = {item["id"] for item in existing_items}

    new_items = []

    for source in sources:
        feed = feedparser.parse(source["rss_url"])
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))

            if not is_transfer_related(title, summary):
                continue

            link = entry.get("link", "")
            item_id = make_id(link, title)
            if item_id in existing_ids:
                continue

            new_items.append({
                "id": item_id,
                "title": title,
                "summary_raw": summary,
                "link": link,
                "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
                "source_name": source["name"],
                "source_tier": source["tier"],
                "league": source["league"],
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })
            existing_ids.add(item_id)

    save_json(RAW_ITEMS_PATH, existing_items + new_items)
    save_json(PENDING_PATH, new_items)

    print(f"収集完了: 新着 {len(new_items)} 件")


if __name__ == "__main__":
    main()
