# タスク管理機能仕様書

## 概要
Slackチャンネル内でチーム向けタスクの作成、進捗管理、完了処理を行う機能

## 機能一覧

### 1. タスク作成機能
- **アクセス**: チャンネルメニュー → タスク管理 → タスク作成
- **場所**: チャンネル内
- **機能**: 新しいタスクの登録

#### 作成フロー
1. タスク作成ボタンクリック
2. タスク情報入力フォーム表示
3. タスク詳細入力（タイトル・説明・担当者・期限）
4. 保存実行
5. チャンネルに作成通知

#### 入力項目
- **タスクタイトル**: 必須、100文字以内
- **タスク説明**: 任意、500文字以内

### 2. タスク一覧表示機能
- **コマンド**: チャンネルメニュー → タスク管理 → タスク一覧
- **場所**: チャンネル内
- **機能**: 現在のタスク状況を一覧表示

#### 表示内容
- **アクティブタスク**: 未完了タスクの一覧
- **タスク情報**: タイトル・担当者・期限・状態
- **アクションボタン**: 完了・削除
- **表示順**: 作成日時順（新しい順）

#### 表示形式
```
📋 タスク一覧 (3件)
┃ 👤 @user1 | 期限: 12/25
┃ 📝 詳細説明テキスト...
┃ [完了] [削除]
┗ ... (他のタスク)
```

### 3. タスク完了機能
- **操作**: タスク一覧の「完了」ボタン
- **場所**: チャンネル内
- **機能**: タスクを完了状態に変更

#### 完了処理
1. 完了ボタンクリック
2. 確認ダイアログ表示
3. 確認後にタスク状態更新
4. 完了通知をチャンネルに投稿
5. タスク一覧から除外

#### 完了時の変更
- **ステータス**: `pending` → `completed`
- **完了日時**: 現在時刻を記録
- **表示**: 一覧から自動的に除外

### 4. タスク削除機能
- **操作**: タスク一覧の「削除」ボタン
- **場所**: チャンネル内
- **機能**: タスクの完全削除

#### 削除処理
1. 削除ボタンクリック
2. 確認なしで即座削除実行
3. データベースから物理削除
4. 削除通知をチャンネルに投稿

### 5. タスクコマンド機能
- **コマンド**: `!task タスクの内容`
- **場所**: チャンネル内
- **機能**: コマンドライン的なタスク操作

#### コマンド解析
```python
def parse_task_command(text):
    if text.startswith("!task "):
        parts = text[6:].strip().split()
        command = parts[0] if parts else "list"
        args = parts[1:] if len(parts) > 1 else []
        return command, args
    return None, []
```

## データモデル

### channel_tasksテーブル
```sql
CREATE TABLE channel_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id TEXT NOT NULL,
  channel_name TEXT,
  title TEXT NOT NULL,
  description TEXT,
  assigned_user_id TEXT,
  assigned_user_name TEXT,
  due_date DATE,
  priority TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'pending',
  created_by_user_id TEXT NOT NULL,
  created_by_user_name TEXT,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### インデックス設計
```sql
-- パフォーマンス向上用インデックス
CREATE INDEX idx_channel_tasks_channel_id ON channel_tasks(channel_id);
CREATE INDEX idx_channel_tasks_status ON channel_tasks(status);
CREATE INDEX idx_channel_tasks_assigned_user ON channel_tasks(assigned_user_id);
CREATE INDEX idx_channel_tasks_due_date ON channel_tasks(due_date);
```

### 列定義詳細
- **priority**: 'high', 'medium', 'low'
- **status**: 'pending', 'completed', 'cancelled'
- **due_date**: 期限日（時刻なし）
- **completed_at**: 完了日時（UTCタイムスタンプ）

## UI設計仕様

### タスク作成フォーム
```json
{
  "type": "modal",
  "title": "新しいタスクを作成",
  "blocks": [
    {
      "type": "input",
      "label": "タスクタイトル",
      "element": {
        "type": "plain_text_input",
        "action_id": "task_title",
        "max_length": 100
      }
    },
    {
      "type": "input",
      "label": "タスク説明",
      "element": {
        "type": "plain_text_input",
        "action_id": "task_description",
        "multiline": true,
        "max_length": 500
      }
    },
    {
      "type": "input",
      "label": "担当者",
      "element": {
        "type": "users_select",
        "action_id": "task_assignee"
      }
    }
  ]
}
```

### タスク一覧表示
```json
{
  "type": "section",
  "fields": [
    {"type": "mrkdwn", "text": "*タイトル:* タスク名"},
    {"type": "mrkdwn", "text": "*担当:* <@USER123>"},
    {"type": "mrkdwn", "text": "*期限:* 2024-12-25"},
    {"type": "mrkdwn", "text": "*優先度:* 高"}
  ],
  "accessory": {
    "type": "overflow",
    "options": [
      {"text": "完了", "value": "complete_task_[id]"},
      {"text": "削除", "value": "delete_task_[id]"}
    ]
  }
}
```

## ビジネスロジック

### タスクステータス管理
```python
class TaskStatus:
    PENDING = "pending"      # 未完了
    COMPLETED = "completed"  # 完了
    CANCELLED = "cancelled"  # キャンセル

def complete_task(task_id):
    return update_task_status(task_id, TaskStatus.COMPLETED)
```

## API仕様

### タスク作成API
```python
def save_channel_task(task_data: dict) -> dict:
    """
    Args:
        task_data: {
            'channel_id': str,
            'title': str,
            'description': str,
            'assigned_user_id': str,
            'due_date': str,
            'priority': str,
            'created_by_user_id': str
        }
    Returns:
        dict: 作成されたタスク情報
    """
```

### タスク取得API
```python
def get_channel_tasks(channel_id: str, status: str = 'pending') -> list:
    """
    Args:
        channel_id: チャンネルID
        status: タスクステータス
    Returns:
        list: タスクリスト
    """
```

### タスク更新API
```python
def update_task_status(task_id: str, status: str) -> bool:
    """
    Args:
        task_id: タスクID
        status: 新しいステータス
    Returns:
        bool: 更新成功可否
    """
```

## エラーハンドリング

### 入力値検証
```python
def validate_task_data(data):
    errors = []

    if not data.get('title', '').strip():
        errors.append("タスクタイトルは必須です")

    if len(data.get('title', '')) > 100:
        errors.append("タイトルは100文字以内で入力してください")

    if len(data.get('description', '')) > 500:
        errors.append("説明は500文字以内で入力してください")

    return errors
```

### 操作エラー
- **タスク不存在**: "指定されたタスクが見つかりません"
- **権限エラー**: "このタスクを操作する権限がありません"
- **ステータス不正**: "無効なステータスが指定されました"

### システムエラー
```python
try:
    result = save_channel_task(task_data)
except Exception as e:
    logger.error(f"Task creation failed: {e}")
    say(text="❌ タスクの作成に失敗しました")
```

## セキュリティ仕様

### アクセス制御
- **チャンネル限定**: 各チャンネルのタスクは該当チャンネルでのみ表示
- **操作権限**: 全チャンネルメンバーが作成・完了可能
- **削除権限**: 作成者のみ削除可能（将来拡張）

### データ保護
- **入力サニタイズ**: XSS攻撃対策
- **SQLインジェクション対策**: パラメータ化クエリ
- **データ暗号化**: 通信・保存時の暗号化

## パフォーマンス仕様

### 応答時間目標
- **タスク作成**: 1秒以内
- **一覧表示**: 2秒以内
- **ステータス更新**: 500ms以内

### スケーラビリティ
- **タスク数**: チャンネルあたり1,000件まで
- **同時操作**: 20並行処理まで
- **履歴保持**: 完了タスクは6ヶ月間保持

### 最適化施策
- **インデックス活用**: クエリ性能向上
- **ページング**: 大量データの段階的読み込み
- **キャッシュ**: 頻繁アクセスデータの高速化
