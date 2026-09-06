# 移籍ウォッチ(iseki-soccer.com)セットアップ手順

このファイル一式を使えば、自動で海外サッカーの移籍情報を集めて日本語で公開するサイトが動きます。
以下の手順を順番に進めてください。難しい設定作業はなく、すべてクリックと貼り付けで完了します。

---

## STEP 1. GitHubアカウントを作る(無料・5分)

1. https://github.com/signup にアクセス
2. メールアドレス・パスワード・ユーザー名を入力して登録
3. 届いた確認メールのリンクをクリック

Gmailアカウントを作るのと同じ感覚です。クレジットカードは不要です。

---

## STEP 2. Claude APIキーを取得する(要クレジットカード登録)

このサイトは記事の日本語要約にClaude(Anthropic社のAI)を使います。

1. https://console.anthropic.com にアクセスし、アカウントを作成
2. 支払い方法(クレジットカード)を登録し、少額をチャージ(月1,000〜1,500円分の利用を想定)
3. 「API Keys」のページで新しいキーを発行し、`sk-ant-...` から始まる文字列をコピーしてどこかに保存しておく

このキーは絶対に他人に見せたり、Webサイト上に直接貼り付けたりしないでください。次のSTEP3で「秘密の保管庫」に登録します。

---

## STEP 2.5 X(旧Twitter)のAPIキーを取得する(Fabrizio Romano等の取得用)

1. https://developer.x.com にアクセスし、開発者アカウントを作成
2. 支払い方法を登録(従量課金制。1アカウント・1日1回の取得なら月300円程度の想定)
3. 新しいアプリを作成し、「Bearer Token」を発行してコピーしておく

こちらも他人に見せず、STEP4で秘密の保管庫に登録します。

---

## STEP 3. このファイル一式をGitHubにアップロードする

1. GitHubにログインした状態で https://github.com/new にアクセス
2. リポジトリ名を `iseki-soccer` にして「Create repository」をクリック
3. 作成された画面の「uploading an existing file」というリンクをクリック
4. このフォルダの中身(index.html, scripts, config, data, requirements.txt, .github フォルダなど)を全てドラッグ&ドロップしてアップロード
   - `.github` フォルダが見えない場合は、フォルダごとドラッグすればアップロードされます
5. 「Commit changes」をクリック

---

## STEP 4. APIキーを安全な場所に登録する

1. アップロードしたリポジトリの画面で「Settings」タブを開く
2. 左メニューの「Secrets and variables」→「Actions」を選択
3. 「New repository secret」をクリック
4. Name欄に `ANTHROPIC_API_KEY` と入力(この名前は一字一句そのまま)、Secret欄にSTEP2でコピーしたキーを貼り付けて保存
5. もう一度「New repository secret」をクリックし、Name欄に `X_BEARER_TOKEN`、Secret欄にSTEP2.5でコピーしたトークンを貼り付けて保存

---

## STEP 5. サイトを公開する(GitHub Pages)

1. リポジトリの「Settings」→「Pages」を開く
2. 「Branch」を `main` に設定して保存
3. 数分待つと `https://(あなたのユーザー名).github.io/iseki-soccer/` でサイトが見られるようになります

---

## STEP 6. 独自ドメイン(iseki-soccer.com)をつなぐ

1. お名前.comなどのドメイン取得サービスで `iseki-soccer.com` を購入
2. 購入したサービスの管理画面で、DNS設定に以下を追加(サービスにより手順表記は異なります)
   - GitHub Pagesが案内するIPアドレス/CNAME情報を設定(STEP5のPages設定画面に手順が表示されます)
3. GitHubの「Settings」→「Pages」の「Custom domain」欄に `iseki-soccer.com` と入力して保存

---

## STEP 7. 自動更新が動いているか確認する

1. リポジトリの「Actions」タブを開く
2. 「移籍情報の自動更新」というワークフローが表示されていればOK
3. 今すぐ試したい場合は「Run workflow」ボタンを押すと、その場で収集→要約→公開が実行されます
4. 毎日日本時間の朝7時に自動実行されます(何もしなくてOK)

---

## 運用が始まったら、けいさんがやること

- 基本的に何もしなくてOKです(毎朝ロボットが自動更新)
- `data/review_queue.json` に確信度の低い記事が溜まった場合だけ、内容を見て問題なければ `data/articles.json` に手動でコピーしてください(週に数件想定)
- 対象メディアを増やしたい場合は `config/sources.json` にRSSのURLを追記するだけで反映されます

---

## 困ったときは

- 「Actions」タブで赤い✕マークが出ていたら、エラー内容をコピーして聞いてください
- GitHubからの通知メールでエラーが分かるようになっています
