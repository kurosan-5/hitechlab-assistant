# エラー対応ガイド・トラブルシューティング

## 🚨 緊急時対応

### システム全体停止時
1. **Render Dashboard** でサービス状況確認
2. **ログ確認**: 最新のエラーログをチェック
3. **ロールバック**: 必要に応じて前回正常動作版に戻す
4. **ユーザー通知**: Slackで障害告知

### 緊急連絡先
- **システム管理者**: [h.kanamori415@gmail.com]
- **Slack管理者**: [h.kanamori415@gmail.com]

---

## 🔍 エラー分類別対応ガイド

### 1. Slack連携エラー

#### 1.1 認証エラー
**エラーメッセージ例:**
```
[設定不足] SLACK_BOT_TOKEN と SLACK_SIGNING_SECRET を .env に設定してください。
```
```
InvalidSlackToken: The token provided is not valid
```

**原因と対処法:**
| 原因 | 対処法 | 確認方法 |
|------|--------|----------|
| Bot Token 未設定 | 環境変数 `SLACK_BOT_TOKEN` を設定 | Render Dashboard → Environment |
| Token 有効期限切れ | Slack App で新しいToken生成 | Slack API Dashboard |
| Signing Secret 不正 | `SLACK_SIGNING_SECRET` を再設定 | Slack App → Basic Information |
| スコープ不足 | 必要なBot Token Scopesを追加 | OAuth & Permissions |

**解決手順:**
1. Slack API Dashboard で Token 確認
2. 必要なスコープが付与されているか確認
3. 環境変数を正しく設定
4. アプリケーション再起動

#### 1.2 Event Subscription エラー
**エラーメッセージ例:**
```
Your URL didn't respond with the value of the challenge parameter.
```
```
Event delivery failed: HTTP 500
```

**原因と対処法:**
| 原因 | 対処法 | 確認方法 |
|------|--------|----------|
| Request URL 不正 | 正しいURL設定 | `https://your-app.onrender.com/slack/events` |
| サーバー未起動 | アプリケーション起動確認 | Render Logs |
| SSL証明書エラー | HTTPS対応確認 | ブラウザでURL直接アクセス |
| レスポンス超過 | 処理時間短縮・非同期化 | ログでレスポンス時間確認 |

**解決手順:**
1. アプリケーションが正常起動しているか確認
2. `/slack/events` エンドポイントの動作確認
3. Slack Event Subscriptions で URL 再設定
4. Challenge verification の応答確認

#### 1.3 Rate Limiting エラー
**エラーメッセージ例:**
```
SlackApiError: rate_limited
```

**対処法:**
- API呼び出し頻度を調整
- Retry-After ヘッダーに従って待機
- バッチ処理でAPI呼び出し削減

### 2. データベースエラー

#### 2.1 接続エラー
**エラーメッセージ例:**
```
RuntimeError: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment
```
```
ConnectionError: Cannot connect to Supabase
```

**原因と対処法:**
| 原因 | 対処法 | 確認方法 |
|------|--------|----------|
| 環境変数未設定 | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` 設定 | Render Environment |
| API Key 無効 | Supabase で新しいKey生成 | Supabase Dashboard |
| ネットワーク問題 | Supabase サービス状況確認 | [Supabase Status](https://status.supabase.com/) |
| プロジェクト停止 | Supabase プロジェクト復旧 | Supabase Dashboard |

**解決手順:**
1. Supabase Dashboard でプロジェクト状況確認
2. API Key の有効性確認
3. 環境変数の設定確認
4. ネットワーク接続テスト

#### 2.2 スキーマエラー
**エラーメッセージ例:**
```
relation "users" does not exist
```
```
column "slack_user_id" does not exist
```

**対処法:**
1. `db/schema.sql` をSupabase SQL Editorで実行
2. テーブル存在確認: `\dt` コマンド
3. カラム確認: `\d table_name` コマンド
4. 必要に応じてマイグレーション実行

#### 2.3 データ整合性エラー
**エラーメッセージ例:**
```
duplicate key value violates unique constraint
```
```
foreign key constraint violation
```

**対処法:**
- 重複データの確認・削除
- 外部キー関係の確認
- データクリーンアップスクリプト実行

### 3. アプリケーション実行エラー

#### 3.1 起動エラー
**エラーメッセージ例:**
```
ModuleNotFoundError: No module named 'slack_bolt'
```
```
ImportError: cannot import name 'get_client' from 'db.supabase_client'
```

**原因と対処法:**
| 原因 | 対処法 | 確認方法 |
|------|--------|----------|
| 依存関係未インストール | `pip install -r requirements.txt` | requirements.txt |
| Python版本不整合 | Python 3.8+ 使用確認 | `python --version` |
| パッケージ破損 | 仮想環境再作成 | `.venv` 削除・再作成 |
| インポートパス問題 | モジュールパス確認 | PYTHONPATH設定 |

**解決手順:**
1. Python バージョン確認
2. 仮想環境の有効化確認
3. 依存関係の再インストール
4. インポートパスの確認

#### 3.2 ランタイムエラー
**エラーメッセージ例:**
```
AttributeError: 'NoneType' object has no attribute 'id'
```
```
KeyError: 'user'
```

**原因と対処法:**
- Null値チェック不備 → 適切なNull値ハンドリング
- 辞書キー存在確認不備 → `.get()` メソッド使用
- 型不整合 → Type Hints とバリデーション強化

#### 3.3 メモリ・パフォーマンスエラー
**エラーメッセージ例:**
```
MemoryError: Unable to allocate memory
```
```
TimeoutError: Request timeout
```

**対処法:**
- クエリ最適化（LIMIT追加、インデックス活用）
- 処理の非同期化
- メモリリーク箇所の特定・修正
- Render プランのアップグレード

### 4. 機能別エラー

#### 4.1 勤怠管理エラー

**出勤開始失敗:**
```python
# エラー: 重複出勤記録
if existing_work_today:
    say("❌ 今日は既に出勤記録があります。")
    return
```

**解決方法:**
- 既存記録の確認・削除
- 日付境界の確認（JST/UTC変換）

**退勤処理失敗:**
```python
# エラー: 出勤記録なし
if not start_record:
    say("❌ 対象日の開始記録が見つかりませんでした。")
    return
```

**解決方法:**
- 出勤開始の事前実行
- 日付指定の確認

#### 4.2 チャンネルメモエラー

**検索失敗:**
```
❌ 検索中にエラーが発生しました
```

**原因と対処法:**
- 全文検索インデックス未作成 → インデックス再構築
- 検索クエリ構文エラー → クエリ修正
- 大量データによるタイムアウト → 検索条件絞り込み

**メモ保存失敗:**
```
❌ メモの作成に失敗しました
```

**原因と対処法:**
- 文字数制限超過 → 文字数確認・制限
- データベース容量不足 → 古いデータ削除
- ネットワークエラー → 再試行機能実装

#### 4.3 タスク管理エラー

**タスク作成失敗:**
```
❌ タスクの作成に失敗しました
```

**原因と対処法:**
- 必須項目未入力 → バリデーション強化
- 権限不足 → チャンネル参加状況確認
- データ形式エラー → 入力値チェック

### 5. UI・表示エラー

#### 5.1 メニュー表示エラー
**メニュー未表示:**
- ボットのチャンネル参加確認
- メッセージイベント受信確認
- コマンド認識ロジック確認

#### 5.2 フォーム表示エラー
**モーダル表示失敗:**
- Block Kit 構文確認
- 文字数制限確認
- ネストレベル確認

---

## 🛠️ デバッグ手順

### 1. ログ確認手順
```bash
# Render ログ確認
# 1. Render Dashboard にログイン
# 2. サービス選択
# 3. Logs タブでリアルタイムログ確認

# ローカルデバッグ時
LOG_LEVEL=DEBUG python app.py
```

### 2. データベース状況確認
```sql
-- Supabase SQL Editor で実行

-- テーブル一覧確認
\dt

-- ユーザーデータ確認
SELECT id, name, slack_user_id FROM users LIMIT 10;

-- 最新の勤務記録確認
SELECT u.name, w.start_time, w.end_time
FROM works w
JOIN users u ON w.user_id = u.id
ORDER BY w.created_at DESC
LIMIT 10;

-- インデックス確認
\di
```

### 3. Slack API 状況確認
```python
# テストスクリプト
from boltApp import bolt_app

# 認証テスト
try:
    auth_response = bolt_app.client.auth_test()
    print(f"✅ Bot ID: {auth_response['user_id']}")
except Exception as e:
    print(f"❌ Auth failed: {e}")

# チャンネル一覧取得テスト
try:
    channels = bolt_app.client.conversations_list()
    print(f"✅ Channels found: {len(channels['channels'])}")
except Exception as e:
    print(f"❌ Channel list failed: {e}")
```

---

## 📋 チェックリスト

### システム正常性確認
- [ ] アプリケーション起動確認
- [ ] データベース接続確認
- [ ] Slack API 認証確認
- [ ] Event Subscription 動作確認
- [ ] 基本機能動作確認（メニュー表示）

### 勤怠機能確認
- [ ] 出勤開始機能
- [ ] 退勤機能
- [ ] 出勤予定機能
- [ ] 出勤確認機能
- [ ] ユーザー情報機能

### チャンネル機能確認
- [ ] メモ自動記録
- [ ] メモ検索機能
- [ ] メモ統計機能
- [ ] タスク管理機能

### セキュリティ確認
- [ ] 環境変数保護
- [ ] API キー有効性
- [ ] アクセス権限確認
- [ ] データ暗号化確認

---

## 🆘 よくあるエラーパターン

### パターン1: 初期セットアップ失敗
**症状:** アプリケーションが起動しない
**確認項目:**
1. Python バージョン (3.8+)
2. 仮想環境アクティベート
3. 依存関係インストール
4. 環境変数設定

### パターン2: Slack応答なし
**症状:** Slackでコマンド送信しても反応なし
**確認項目:**
1. Event Subscription URL設定
2. Bot Token スコープ
3. チャンネル/DM招待状況
4. ネットワーク接続

**症状:** Slackでボタン押下しても反応なし
**確認項目:**
1. Interactivity & Shortcuts URL設定
2. Bot Token スコープ
3. チャンネル/DM招待状況
4. ネットワーク接続

### パターン3: データベース操作失敗
**症状:** ユーザー情報や勤務記録が保存されない
**確認項目:**
1. Supabase 接続情報
2. テーブルスキーマ
3. API キー権限
4. データ制約違反

### パターン4: パフォーマンス問題
**症状:** レスポンスが遅い、タイムアウトエラー
**確認項目:**
1. データベースクエリ最適化
2. インデックス設定
3. メモリ使用量
4. Render プラン制限

---

## 📞 エスカレーション基準

### レベル1: 軽微な問題
- 特定機能の一時的な不具合
- 個別ユーザーの操作エラー
- **対応者:** 開発チーム

### レベル2: 中程度の問題
- 複数ユーザーに影響する機能停止
- データ整合性の問題
- **対応者:** システム管理者
- **対応時間:** 4時間以内

### レベル3: 重大な問題
- システム全体の停止
- データ損失の可能性
- セキュリティインシデント
- **対応者:** システム管理者
- **対応時間:** 1時間以内

---

## 🔧 予防保守

### 定期確認項目（日次）
- [ ] システム稼働状況確認
- [ ] エラーログ確認
- [ ] レスポンス時間監視

### 定期確認項目（週次）
- [ ] データベース容量確認
- [ ] パフォーマンス指標確認
- [ ] バックアップ状況確認

### 定期確認項目（月次）
- [ ] セキュリティアップデート
- [ ] 依存関係更新
- [ ] 不要データ削除
- [ ] 監視設定見直し

---

## 📚 関連リソース

### 公式ドキュメント
- [Slack API Documentation](https://api.slack.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Render Documentation](https://render.com/docs)

### 内部ドキュメント
- [セットアップガイド](setup.md)
- [開発者ガイド](development-guide.md)
- [デプロイメントガイド](deployment.md)

### 外部ツール
- [Slack API Tester](https://api.slack.com/methods)
- [Supabase Dashboard](https://app.supabase.com/)
- [Render Dashboard](https://dashboard.render.com/)

---

このエラー対応ガイドを参照して、迅速な問題解決を行ってください。不明な点があれば、開発チームまでお問い合わせください。
