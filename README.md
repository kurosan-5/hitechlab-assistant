# 勤怠管理 Slack ボット - 総合ドキュメント

## 📁 ドキュメント構成

- [プロジェクト概要](docs/project-overview.md) - システム全体の概要と目的
- [アーキテクチャ設計](docs/architecture.md) - システム構成と技術スタック
- [機能仕様書](docs/features/)
  - [勤怠管理機能](docs/features/attendance.md)
  - [チャンネルメモ機能](docs/features/channel-memo.md)
  - [タスク管理機能](docs/features/task-management.md)
  - [ユーザープロファイル機能](docs/features/user-profile.md)
- [API・データベース仕様](docs/database.md)
- [セットアップガイド](docs/setup.md)
- [開発者ガイド](docs/development-guide.md)
- [デプロイメントガイド](docs/deployment.md)
- [エラー対応ガイド](docs/troubleshooting.md)

## 🎯 プロジェクト概要

### システム名
勤怠管理 Slack ボット (hitechlab-assistant)

### 目的
Slack を使用した勤怠管理とチーム間の情報共有を効率化するボットシステム

### 主要機能
1. **DM - 勤怠管理機能**: 出勤・退勤時刻の記録、出勤予定の管理
2. **ユーザープロファイル機能**: 個人設定と勤務記録の管理
3. **チャンネル - メモ機能**: チャンネル内メッセージの自動記録・検索
4. **チャンネル - タスク管理機能**: チーム内タスクの作成・管理

### 技術スタック
- **フレームワーク**: Python + Slack Bolt Framework
- **データベース**: Supabase (PostgreSQL)
- **デプロイ**: Render

## 🏗️ アーキテクチャ概要

```
Slack App ↔ Bolt Framework ↔ Flask Server ↔ Supabase DB
                    ↕
            Handler Modules
            ↕
        Repository Layer
```

### ディレクトリ構造
```
hitech-memoBot/
├── app.py                 # メインアプリケーション
├── boltApp.py            # Slack Bolt設定
├── db/                   # データベース層
│   ├── repository.py     # データアクセス層
│   ├── schema.sql        # DBスキーマ
│   └── supabase_client.py # Supabase接続
├── handlers/             # 機能ハンドラー
│   ├── attendance.py     # 勤怠管理
│   ├── channel_memo.py   # チャンネルメモ
│   ├── startWork.py      # 出勤開始
│   ├── workflows.py      # 退勤処理
│   ├── user_profile.py   # ユーザー管理
│   └── channel/          # チャンネル機能
├── display/              # UI表示
├── google/               # Google Sheets連携(非推奨)
└── docs/                 # ドキュメント
```

## 🚀 クイックスタート

### 前提条件
- Python 3.8以上
- Slack ワークスペースの管理者権限
- Supabase アカウント (hitechlab.git@gmail.com)
- Render アカウント（hitechlab.git@gmail.com）

### セットアップ手順

1. **環境設定**: `.env` ファイルを作成
```bash
# 必須設定
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# オプション設定
PORT=3001
TZ=UTC
```

2. **依存関係インストール**:
```bash
# 仮想環境作成・アクティベート
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 依存関係インストール
pip install -r requirements.txt
```

3. **データベース初期化**: Supabase SQL エディタで `db/schema.sql` を実行

4. **アプリケーション起動**:
```bash
python app.py
```

詳細なセットアップ手順は [セットアップガイド](docs/setup.md) を参照してください。

## 📋 基本的な使い方

### DM機能（勤怠管理）
- `メニュー` - メインメニューを表示
- `出勤開始` - 勤務開始時刻を記録
- `退勤` - 勤務終了時刻を記録
- `出勤更新` - 出勤予定を登録
- `出勤確認` - チーム出勤状況を確認
- `ユーザー情報` - 個人設定と勤務記録

### チャンネル機能
- `@botname メニュー` - チャンネルメニューを表示
- `メモ検索 キーワード` - 過去メッセージを検索
- `メモ統計` - チャンネル統計を表示
- `!task list` - タスク一覧を表示
- `!recent 7` - 最近7日間のメモを表示

## ⚠️ よくあるエラーと対処法

エラーが発生した場合は [エラー対応ガイド](docs/troubleshooting.md) を確認してください。

### 緊急時の対応
1. **システム停止時**: Render Dashboard でログ確認
2. **認証エラー**: 環境変数の設定確認
3. **データベースエラー**: Supabase の接続状況確認

## 📞 サポート・リソース

### ドキュメント
- **初心者向け**: [セットアップガイド](docs/setup.md)
- **エラー対応**: [トラブルシューティング](docs/troubleshooting.md)

### 外部リンク
- [Slack API Documentation](https://api.slack.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Render Documentation](https://render.com/docs)

詳細は [開発者ガイド](docs/development-guide.md) を参照してください。

## 📜 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 🔧 プロジェクト情報

- **バージョン**: 1.0.0
- **最終更新**: 2025年9月
- **メンテナンス状況**: アクティブ
- **Python要件**: 3.8+