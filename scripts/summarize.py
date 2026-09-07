"""
AI要約スクリプト
- data/pending_summarize.json の新着記事を Claude (Haiku) で日本語要約
- ソースの格付け(公式/大手/個人)とAIの確信度から信頼度タグを決定
- 確信度が低い記事は自動公開せず、確認待ちキュー(review_queue.json)に回す
- 問題ない記事だけ data/articles.json (サイトが実際に表示するデータ)に追加
"""
import json
import os
from anthropic import Anthropic

PENDING_PATH = "data/pending_summarize.json"
ARTICLES_PATH = "data/articles.json"
REVIEW_QUEUE_PATH = "data/review_queue.json"

# ソース側の表現から「確定」とみなせるキーワード
CONFIRMED_KEYWORDS = [
    "here we go", "confirmed", "official", "completes move",
    "medical completed", "signs for", "unveiled"
]

SYSTEM_PROMPT = """あなたはサッカー移籍情報の事実抽出アシスタントです。
入力される記事やSNS投稿(英語または日本語)の見出し・本文から、「誰が」「どこから」「どこへ」
移籍する話なのかという事実情報だけを抽出してください。文章の要約や言い換えは不要です。

ルール:
- 移籍金・契約年数などの数値は原文の値をそのまま使う(不明な場合は空文字のまま)
- 選手名・クラブ名は日本語表記が定着しているものは日本語に、不明なものは英語表記のまま書く
- 移籍元・移籍先それぞれのクラブが所属するリーグを、次のコードの中から選んで from_league / to_league に入れる:
  PL(プレミアリーグ), LaLiga(ラ・リーガ), SerieA(セリエA), Bundesliga(ブンデスリーガ),
  Ligue1(リーグ・アン), Portugal(プリメイラ・リーガ), Netherlands(エールディヴィジ),
  Scotland(スコティッシュプレミア), MLS, Jleague(Jリーグ)
  上記のどれにも該当しない、または分からない場合は空文字のままにする(無理に当てはめない)
- 移籍の話ではない、または「誰が・どこから・どこへ」が読み取れない場合は confidence を "low" にする
- 出力は次のJSON形式のみ。説明文・前置き・コードブロック記号は一切付けない

{"player": "選手名", "from_club": "移籍元クラブ", "to_club": "移籍先クラブ", "from_league": "リーグコードまたは空文字", "to_league": "リーグコードまたは空文字", "fee": "移籍金(不明なら空文字)", "confidence": "high または medium または low"}
"""


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def rule_based_reliability(item):
    text = f"{item['title']} {item['summary_raw']}".lower()
    if item["source_tier"] == "official" or any(k in text for k in CONFIRMED_KEYWORDS):
        return "confirmed"
    if item["source_tier"] == "insider":
        # Fabrizio Romano等、実績のある個人記者。個人アカウントだが信頼度は「有力」からスタート
        return "strong"
    if item["source_tier"] == "major":
        return "strong"
    return "rumor"


def summarize_item(client, item):
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"見出し: {item['title']}\n概要: {item['summary_raw']}"
            }]
        )
        raw_text = response.content[0].text.strip()

        # AIがコードブロック記号(```json ... ```)を付けてしまった場合に備えて除去する
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()

        # JSONオブジェクト部分だけを抜き出す(前後に余計な文章が付いた場合の保険)
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1:
            raw_text = raw_text[start:end + 1]

        if not raw_text:
            print(f"抽出に失敗しました (id={item['id']}): AIの応答が空でした")
            return {"player": "", "from_club": "", "to_club": "", "fee": "", "confidence": "low"}

        return json.loads(raw_text)
    except Exception as e:
        print(f"抽出に失敗しました (id={item['id']}): {e}")
        try:
            print(f"  AIの生の応答: {raw_text!r}")
        except Exception:
            pass
        return {"player": "", "from_club": "", "to_club": "", "fee": "", "confidence": "low"}


def main():
    pending = load_json(PENDING_PATH, [])
    articles = load_json(ARTICLES_PATH, [])
    review_queue = load_json(REVIEW_QUEUE_PATH, [])

    if not pending:
        print("新着記事はありません")
        return

    client = Anthropic()  # 環境変数 ANTHROPIC_API_KEY を自動で読み込む

    published_count = 0
    flagged_count = 0

    for item in pending:
        parsed = summarize_item(client, item)
        reliability = rule_based_reliability(item)

        # 収集元が付けたリーグタグより、AIが判定した実際の移籍先リーグを優先する
        # (例: 「さっかりん」はJリーグ関連ソースだが、海外への移籍も含むため)
        resolved_league = parsed.get("to_league") or item.get("league", "")

        record = {
            **item,
            "league": resolved_league,
            "player": parsed.get("player", ""),
            "from_club": parsed.get("from_club", ""),
            "to_club": parsed.get("to_club", ""),
            "from_league": parsed.get("from_league", ""),
            "to_league": parsed.get("to_league", ""),
            "fee": parsed.get("fee", ""),
            "reliability": reliability,
            "ai_confidence": parsed.get("confidence", "low"),
        }

        needs_review = (
            parsed.get("confidence") == "low"
            or not parsed.get("player")
            or not parsed.get("to_club")
        )

        if needs_review:
            review_queue.append(record)
            flagged_count += 1
        else:
            articles.append(record)
            published_count += 1

    save_json(ARTICLES_PATH, articles)
    save_json(REVIEW_QUEUE_PATH, review_queue)

    print(f"公開: {published_count} 件 / 確認待ちに回した: {flagged_count} 件")


if __name__ == "__main__":
    main()
