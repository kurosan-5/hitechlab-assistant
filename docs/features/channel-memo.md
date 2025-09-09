# チャンネルメモ機能仕様書

## 概要
Slackチャンネル内でメモを作成し、検索・管理・統計機能を提供する

## 機能一覧

### 1. 自動メッセージ記録機能
- **動作**: チャンネル内の全メッセージを自動保存
- **対象**: テキストメッセージ（ボットメッセージ除く）
- **保存内容**: メッセージ本文、投稿者、チャンネル、タイムスタンプ、パーマリンク

#### 除外対象
- ボットによる投稿（`bot_id`有り）
- サブタイプ付きメッセージ（`subtype`有り）
- システムメッセージ

### 2. メモ検索機能
- **コマンド**: `メモ検索 [キーワード]`, `memo search [keyword]`, `!search [keyword]`
- **場所**: チャンネル内
- **機能**: キーワードによる過去メッセージの全文検索

#### 検索仕様
- **部分一致**: キーワードの部分文字列検索
- **大小文字不問**: case-insensitive検索
- **複数キーワード**: スペース区切りでAND検索
- **表示件数**: 最大10件まで

#### 検索結果表示
```
📝 メモ検索結果: "キーワード"
┣ 👤 ユーザー名 (MM/DD HH:MM)
┃ メッセージ内容（100文字まで）
┃ 📎 元メッセージへのリンク（あれば）
┗ ... (最大10件)
```

### 4. メモ統計機能
- **コマンド**: `メモ統計`
- **場所**: チャンネル内
- **機能**: チャンネル内のメモ統計とユーザーランキング

#### 統計内容
- **総メモ数**: チャンネル内の全メモ数
- **今日のメモ数**: 当日投稿されたメモ数
- **アクティブユーザー数**: 投稿実績のあるユーザー数
- **ユーザーランキング**: 投稿数上位5名

### 5. メモ管理機能（UIベース）
- **アクセス**: チャンネルメニュー → メモ管理
- **機能**: メモの作成、編集、削除、一覧表示

#### メモ作成
- **入力フォーム**: モーダルダイアログでメモ内容入力
- **メタデータ**: 現在時刻、ユーザー情報を自動付与
- **保存**: 手動作成フラグ付きで保存

#### メモ編集
- **対象**: 投稿済みメモの内容編集
- **UI**: モーダルダイアログでの編集フォーム
- **履歴**: 編集履歴は更新日時で管理

#### メモ削除
- **実行**: 確認なしでの即座削除
- **対象**: 個別メモの完全削除
- **復旧**: 削除後の復旧機能なし

### 6. チャンネルメニュー機能
- **コマンド**: `メニュー`, `menu`, `めにゅー`
- **場所**: チャンネル内
- **機能**: チャンネル機能のメインメニュー表示

## データモデル

### channel_memosテーブル
```sql
CREATE TABLE channel_memos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id TEXT NOT NULL,
  channel_name TEXT,
  user_id TEXT NOT NULL,
  user_name TEXT,
  message TEXT NOT NULL,
  message_ts TEXT NOT NULL,
  thread_ts TEXT,
  permalink TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### インデックス設計
```sql
-- 検索性能向上
CREATE INDEX idx_channel_memos_channel_id ON channel_memos(channel_id);
CREATE INDEX idx_channel_memos_message_search ON channel_memos USING gin(to_tsvector('japanese', message));
CREATE INDEX idx_channel_memos_created_at ON channel_memos(created_at);
CREATE INDEX idx_channel_memos_user_id ON channel_memos(user_id);
```

## コマンド解析仕様

### パターンマッチング
```python
SEARCH_PATTERNS = [
    "メモ検索 ",
    "memo search ",
    "!search "
]

STATS_PATTERNS = [
    "メモ統計"
]
```

### コマンド変換
```python
def convert_legacy_commands(text):
    # !search を メモ検索 形式に正規化
    if text.startswith("!search "):
        keyword = text[8:].strip()
        return f"メモ検索 {keyword}"
    return text
```

## 検索エンジン仕様

### 全文検索
- **エンジン**: PostgreSQL標準の全文検索
- **言語**: 日本語対応（japanese設定）
- **インデックス**: GINインデックス使用

### クエリ生成
```sql
SELECT * FROM channel_memos
WHERE channel_id = %s
  AND to_tsvector('japanese', message) @@ plainto_tsquery('japanese', %s)
ORDER BY created_at DESC
LIMIT 10;
```

### パフォーマンス最適化
- **インデックス活用**: GINインデックスによる高速検索
- **結果制限**: 常に上限10件での制限
- **キャッシュ**: 頻繁な検索クエリのキャッシュ

## UI設計仕様

### Block Kit要素
```json
{
  "type": "section",
  "text": {
    "type": "mrkdwn",
    "text": "*ユーザー名* (MM/DD HH:MM)\nメッセージ内容..."
  },
  "accessory": {
    "type": "overflow",
    "options": [
      {"text": "編集", "value": "edit_memo_[id]"},
      {"text": "削除", "value": "delete_memo_[id]"},
      {"text": "リンク", "url": "[permalink]"}
    ]
  }
}
```

### モーダルダイアログ
```json
{
  "type": "modal",
  "title": "メモを編集",
  "blocks": [
    {
      "type": "input",
      "block_id": "memo_text_block",
      "element": {
        "type": "plain_text_input",
        "action_id": "memo_text_input",
        "multiline": true,
        "initial_value": "現在のメモ内容"
      }
    }
  ]
}
```

## エラーハンドリング

### 検索エラー
- **空キーワード**: "検索キーワードを入力してください"
- **結果なし**: "該当するメモが見つかりませんでした"
- **DB接続エラー**: "検索中にエラーが発生しました"

### メモ操作エラー
- **権限エラー**: "このメモを編集する権限がありません"
- **存在しないメモ**: "指定されたメモが見つかりません"
- **更新失敗**: "メモの更新に失敗しました"

### システムエラー
```python
try:
    # メモ操作
    result = save_channel_memo(memo_data)
except Exception as e:
    logger.error(f"Memo operation failed: {e}")
    say(text="❌ 操作中にエラーが発生しました")
```

## セキュリティ考慮

### アクセス制御
- **チャンネル限定**: 各チャンネルのメモは該当チャンネルでのみ表示
- **ユーザー認証**: Slack認証によるユーザー識別
- **権限管理**: メモ編集は投稿者本人のみ（将来拡張予定）

### データ保護
- **SQL インジェクション対策**: パラメータ化クエリ使用
- **XSS対策**: Slack Block Kit使用によるサニタイズ
- **データ暗号化**: データベース通信の暗号化

## パフォーマンス仕様

### 応答時間目標
- **メモ記録**: 500ms以内
- **検索処理**: 2秒以内
- **統計生成**: 3秒以内
- **一覧表示**: 1秒以内

### スケーラビリティ
- **メモ件数**: チャンネルあたり10万件まで
- **同時検索**: 50並行まで
- **チャンネル数**: 100チャンネルまで

### リソース最適化
- **クエリ最適化**: インデックス活用とクエリチューニング
- **メモリ効率**: 大量結果の段階的読み込み
- **ネットワーク効率**: レスポンスサイズの最小化
