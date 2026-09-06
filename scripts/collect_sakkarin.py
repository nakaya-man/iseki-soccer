"""
さっかりん(soccer.phew.homeip.net)収集スクリプト
- サイト自体の「まとめ方」はコピーせず、各移籍情報に付いている
  「公式発表」等のリンク先URLだけを抽出する
- 収集した項目は summarize.py が後で日本語要約する

注意:
  このサイトは古い形式のHTMLで作られており、構造が変わりやすい。
  動かない場合はログを見て scripts/collect_sakkarin.py の
  セレクタ部分を調整する必要がある。
"""
import json
import os
import re
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

SOURCE_URL = "http://soccer.phew.homeip.net/transfer_news/"
PENDING_PATH = "data/pending_summarize.json"
RAW_ITEMS_PATH = "data/raw_items.json"

# サイト自体のドメイン(内部リンクは除外し、外部=出典リンクだけを拾う)
INTERNAL_HOST = "soccer.phew.homeip.net"


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


def main():
    try:
        resp = requests.get(SOURCE_URL, timeout=20)
        resp.encoding = resp.apparent_encoding  # Shift-JIS等を自動判定
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"さっかりんの取得に失敗しました: {e}")
        return

    existing_items = load_json(RAW_ITEMS_PATH, [])
    existing_ids = {item["id"] for item in existing_items}
    pending = load_json(PENDING_PATH, [])

    new_items = []

    # 選手個別ページへのリンク(/players/info.php)を手がかりに、
    # その近くにある外部リンク(公式発表・報道記事)を出典として拾う
    player_links = soup.find_all("a", href=re.compile(r"/players/info\.php"))

    for player_link in player_links:
        player_name = player_link.get_text(strip=True)
        if not player_name:
            continue

        # 同じ行(親要素)の中から、外部サイトへのリンクを探す
        container = player_link.find_parent(["tr", "td", "li", "div"]) or player_link.parent
        if not container:
            continue

        source_link = None
        for a in container.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and INTERNAL_HOST not in href:
                source_link = a
                break

        if not source_link:
            continue

        link = source_link["href"]
        source_name = source_link.get_text(strip=True) or "さっかりん経由"
        title = f"{player_name} 関連の移籍情報"

        item_id = make_id(link, title)
        if item_id in existing_ids:
            continue

        new_items.append({
            "id": item_id,
            "title": title,
            "summary_raw": container.get_text(" ", strip=True)[:300],
            "link": link,
            "published": datetime.now(timezone.utc).isoformat(),
            "source_name": f"{source_name}(さっかりん経由)",
            "source_tier": "major",
            "league": "Jleague",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        })
        existing_ids.add(item_id)

    save_json(RAW_ITEMS_PATH, existing_items + new_items)
    save_json(PENDING_PATH, pending + new_items)

    print(f"さっかりん経由 収集完了: 新着 {len(new_items)} 件")


if __name__ == "__main__":
    main()
