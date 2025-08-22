# 勤怠管理 Slack ボット (Bolt / Supabase / Render)

このリポジトリは、仕様書に基づく勤怠管理 Slack ボットの実装です。

## セットアップ

1) .env を準備
- `.env.example` をコピーし、以下を設定
  - SLACK_BOT_TOKEN
  - SLACK_SIGNING_SECRET
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE_KEY
  - PORT (任意、デフォルト 3001)
  - TZ=UTC

2) 依存インストール
- 仮想環境を使う場合の例:
```bash
source .venv/bin/activate && pip install -r requirements.txt
```

3) DB スキーマ
- Supabase SQL エディタ等で `db/schema.sql` を実行

4) 起動
```bash
source .venv/bin/activate && python app.py
```

## Slack イベント受信
- Render 等で `POST /slack/events` を Slack Event Subscriptions に設定

## 機能
- DM で「メニュー」「出勤開始」「退勤」「出勤更新」「出勤確認」「ユーザー情報」に対応
- 出勤開始/退勤は `works`、出勤更新は `attendance`、ユーザー情報は `users` を更新
- 日付は JST、時刻は UTC 保存

## 補足
- 現状、JST で選択した時間を正しく UTC に変換して保存します。必要に応じて運用ルールに合わせて調整可能です。