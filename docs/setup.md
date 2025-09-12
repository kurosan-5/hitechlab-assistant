# セットアップガイド

## 概要
勤怠管理Slackボットの環境構築から起動までの完全ガイド

## 前提条件

### 必要なアカウント・権限


- **Slack ワークスペース**: 管理者権限または App 管理権限
- **GitHub アカウント**: ソースコード管理用。Githubのみ、諸事情により金森のアカウントでRenderと紐づけてあるため、運用において新しい変更をデプロイするには新しいRenderアカウント・サーバーを作成して、Slack APIに設定してあるURLを変更してください（設定変更箇所 : Event subscriptions, Interactivity & Shortcuts）

以下のアカウントはどちらもhitechlab.git@gmail.comに紐づけてある。

- **Supabase アカウント**: 無料プラン。DB用。
- **Render アカウント**: デプロイ用。masterへのプッシュをトリガーに自動デプロイ

### システム要件
- **Python**: 3.8以上
- **Git**: バージョン管理
- **テキストエディタ**: VS Code 推奨

## ステップ1: Slack App 作成

### 1.1 Slack App の作成
1. [Slack API](https://api.slack.com/apps) にアクセス
2. "Create New App" をクリック
3. "From scratch" を選択
4. App名とワークスペースを設定

### 1.2 OAuth & Permissions 設定
**Bot Token Scopes** に以下を追加:
```
app_mentions:read
channels:history
channels:read
chat:write
chat:write.public
im:history
im:read
users:read
users.profile:read
```

### 1.3 Event Subscriptions 設定
1. Event Subscriptions を有効化
2. Request URL を設定（後で更新）: `https://your-app.onrender.com/slack/events`

**Subscribe to bot events** に追加:
```
app_mention
message.channels
message.im
```

### 1.4 インストール
1. "Install to Workspace" をクリック
2. Bot User OAuth Token を取得・保存

## 1.5 Slack Bot DM設定

この設定は見逃しがちであるが、大切なので必ず確認すること。

 - App Home →　Show Tabsセクション内Message Tabの下 : 「Allow users to send Slash commands and messages from the messages tab」項目をチェックする。

これにより、ボットにDMを送信することができるようになる。

## ステップ2: Supabase データベース設定

### 2.1 Supabase プロジェクト作成
1. [Supabase](https://supabase.com) にログイン
2. "New project" をクリック
3. プロジェクト名・パスワード・リージョンを設定
4. プロジェクト作成完了まで待機

### 2.2 データベーススキーマ作成
1. Supabase ダッシュボード → SQL Editor
2. db/schema.sqlの内容をコピーして実行する:

```sql
-- db/schema.sql の内容をコピー&実行
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slack_user_id TEXT UNIQUE,
  slack_display_name TEXT,
  contact TEXT,
  work_type TEXT,
  transportation_cost NUMERIC,
  hourly_wage NUMERIC,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- ... 他のテーブルも同様に実行
```

### 2.3 API キー取得
1. Project Settings → API Keys
2. service_role キーを取得・保存
3. URLを保存（下に詳細）

URL:
Dashboardなど見ていると、そのページのURLが表示されていると思うが、URL部分
(ex: https://supabase.com/dashboard/project/○○/)
の、○○という文字列がプロジェクトURLとなる：
```bash
# .env
SUPABASE_URL=https://○○.supabase.co
```
## ステップ3: ローカル環境設定

### 3.1 リポジトリクローン
```bash
git clone <repository-url>
cd hitechlab-assistant
```

### 3.2 Python 仮想環境作成
```bash
# 仮想環境作成
python -m venv .venv

# 仮想環境アクティベート
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

### 3.3 依存関係インストール
```bash
pip install -r requirements.txt
```

### 3.4 環境変数設定
`.env` ファイルを作成:
```env
# Slack 設定
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret

# Supabase 設定
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# サーバー設定
PORT=3001
TZ=UTC

# ログレベル（オプション）
LOG_LEVEL=INFO
```

### 3.5 動作確認
```bash
python app.py
```

## ステップ4: Render デプロイ設定

### 4.1 Render アカウント設定
1. [Render](https://render.com) にログイン
2. GitHub と連携

### 4.2 Web Service 作成
1. "New" → "Web Service"
2. GitHub リポジトリを選択
3. 以下の設定を入力:

**Basic Settings:**
- Name: `hitech-memobot`
- Environment: `Python 3`
- Region: `Singapore (Asia)` 推奨
- Branch: `master`

**Build & Deploy:**
- Build Command: `pip install -r requirements.txt`
- Start Command: `python app.py`

### 4.3 環境変数設定
Environment タブで以下を追加:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
PORT=3001
TZ=UTC
```

### 4.4 デプロイ実行
1. "Create Web Service" をクリック
2. ビルド完了まで待機
3. デプロイ URL を確認

## ステップ5: Slack Event URL 更新

### 5.1 Request URL 設定
1. Slack App 設定 → Event Subscriptions
2. Request URL を更新: `https://your-app.onrender.com/slack/events`
3. "Save Changes" をクリック
4. Interactivity & Shortcuts → URL欄に同様のURLを入力・保存

### 5.2 動作確認
1. Slack で Bot を DM に追加
2. `メニュー` と送信
3. メニューが表示されることを確認

## ステップ6: 動作テスト

### 6.1 DM 機能テスト
以下のコマンドを Bot DM で実行:
```
メニュー

出勤開始

ユーザー情報
```

### 6.2 チャンネル機能テスト
1. Bot をチャンネルに追加
2. 以下を実行:
```
メニュー
```
メニュー画面が返ってきたら成功

### 6.3 エラーログ確認
問題がある場合、Render ログを確認:
1. Render ダッシュボード → サービス選択
2. Logs タブでエラー内容確認

## トラブルシューティング

### よくある問題

#### 1. Slack Token エラー
```
[設定不足] SLACK_BOT_TOKEN と SLACK_SIGNING_SECRET を .env に設定してください。
```
**解決方法:**
- 環境変数が正しく設定されているか確認
- Token に余分なスペースがないか確認

#### 2. Supabase 接続エラー
```
RuntimeError: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment
```
**解決方法:**
- Supabase URL と API キーを確認
- ダッシュボードで正しいキーをコピー

#### 3. Event Subscription エラー
```
Your URL didn't respond with the value of the challenge parameter.
```
**解決方法:**
- Render アプリが正常に起動しているか確認
- URL が正しく設定されているか確認
- HTTPS URL を使用しているか確認

#### 4. Permission エラー
```
missing_scope: The token used is not granted the required scopes
```
**解決方法:**
- OAuth & Permissions で必要なスコープを追加
- Bot を再インストール

#### 5. Database Schema エラー
```
relation "users" does not exist
```
**解決方法:**
- `db/schema.sql` を Supabase で実行
- テーブルが正しく作成されているか確認

### デバッグ方法

#### 1. ローカルデバッグ
```bash
# デバッグモードで起動
LOG_LEVEL=DEBUG python app.py
```


#### 2. データベース確認
```sql
-- Supabase SQL Editor で実行
SELECT * FROM users LIMIT 5;
SELECT * FROM works LIMIT 5;
```

## セキュリティ設定

### 1. 環境変数保護
- `.env` ファイルを `.gitignore` に追加
- 本番環境では Render の Environment Variables を使用

### 2. API キー管理
- Service Role Key は適切に保護

### 3. ネットワーク設定
- Supabase で IP 制限設定（オプション）
- Render でカスタムドメイン設定（オプション）

### 公式ドキュメント
- [Slack API Documentation](https://api.slack.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Render Documentation](https://render.com/docs)

### コミュニティ
- Slack API Community
- Supabase Discord
- GitHub Issues
