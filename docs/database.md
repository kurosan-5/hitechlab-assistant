# データベース仕様書

## 概要
Supabase PostgreSQLを使用したデータベース設計とAPI仕様

## データベース構成

### 技術仕様
- **データベースエンジン**: PostgreSQL 15+
- **クラウドサービス**: Supabase
- **文字コード**: UTF-8
- **タイムゾーン**: UTC（アプリケーション層でJST変換）
- **暗号化**: 保存時・通信時暗号化

## テーブル設計

### 1. users（ユーザー情報）

#### テーブル定義
```sql
CREATE TABLE public.users (
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
```

#### 列詳細
| 列名 | 型 | 制約 | 説明 |
|------|-----|------|------|
| id | UUID | PRIMARY KEY | ユーザー一意識別子 |
| name | TEXT | NOT NULL | ユーザー名（フルネーム） |
| slack_user_id | TEXT | UNIQUE | SlackユーザーID |
| slack_display_name | TEXT | | Slack表示名 |
| contact | TEXT | | 連絡先情報 |
| work_type | TEXT | | 勤務形態 |
| transportation_cost | NUMERIC | | 日額交通費 |
| hourly_wage | NUMERIC | | 時給 |
| created_at | TIMESTAMPTZ | NOT NULL | 作成日時 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新日時 |

#### インデックス
```sql
CREATE UNIQUE INDEX idx_users_slack_user_id ON users(slack_user_id);
CREATE INDEX idx_users_created_at ON users(created_at);
```

### 2. works（勤務記録）

#### テーブル定義
```sql
CREATE TABLE public.works (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  break_time INTEGER,
  comment TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### 列詳細
| 列名 | 型 | 制約 | 説明 |
|------|-----|------|------|
| id | UUID | PRIMARY KEY | 勤務記録一意識別子 |
| user_id | UUID | NOT NULL, FK | ユーザー外部キー |
| start_time | TIMESTAMPTZ | NOT NULL | 勤務開始時刻（UTC） |
| end_time | TIMESTAMPTZ | | 勤務終了時刻（UTC） |
| break_time | INTEGER | | 休憩時間（分） |
| comment | TEXT | | 勤務コメント |
| created_at | TIMESTAMPTZ | NOT NULL | 作成日時 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新日時 |

#### インデックス
```sql
CREATE INDEX idx_works_user_id ON works(user_id);
CREATE INDEX idx_works_start_time ON works(start_time);
CREATE INDEX idx_works_user_date ON works(user_id, DATE(start_time AT TIME ZONE 'JST'));
```

### 3. attendance（出勤予定）

#### テーブル定義
```sql
CREATE TABLE public.attendance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  year INTEGER NOT NULL,
  month INTEGER NOT NULL,
  day INTEGER NOT NULL,
  is_attend BOOLEAN NOT NULL,
  start_time TIME,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT attendance_unique UNIQUE(user_id, year, month, day)
);
```

#### 列詳細
| 列名 | 型 | 制約 | 説明 |
|------|-----|------|------|
| id | UUID | PRIMARY KEY | 出勤予定一意識別子 |
| user_id | UUID | NOT NULL, FK | ユーザー外部キー |
| year | INTEGER | NOT NULL | 年 |
| month | INTEGER | NOT NULL | 月 |
| day | INTEGER | NOT NULL | 日 |
| is_attend | BOOLEAN | NOT NULL | 出勤予定フラグ |
| start_time | TIME | | 出勤開始時刻 |
| created_at | TIMESTAMPTZ | NOT NULL | 作成日時 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新日時 |

#### インデックス
```sql
CREATE UNIQUE INDEX idx_attendance_user_date ON attendance(user_id, year, month, day);
CREATE INDEX idx_attendance_date ON attendance(year, month, day);
```

### 4. channel_memos（チャンネルメモ）

#### テーブル定義
```sql
CREATE TABLE public.channel_memos (
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

#### 列詳細
| 列名 | 型 | 制約 | 説明 |
|------|-----|------|------|
| id | UUID | PRIMARY KEY | メモ一意識別子 |
| channel_id | TEXT | NOT NULL | SlackチャンネルID |
| channel_name | TEXT | | チャンネル名 |
| user_id | TEXT | NOT NULL | SlackユーザーID |
| user_name | TEXT | | ユーザー表示名 |
| message | TEXT | NOT NULL | メッセージ本文 |
| message_ts | TEXT | NOT NULL | Slackメッセージタイムスタンプ |
| thread_ts | TEXT | | スレッドタイムスタンプ |
| permalink | TEXT | | メッセージパーマリンク |
| created_at | TIMESTAMPTZ | NOT NULL | 作成日時 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新日時 |

#### インデックス
```sql
CREATE INDEX idx_channel_memos_channel_id ON channel_memos(channel_id);
CREATE INDEX idx_channel_memos_created_at ON channel_memos(created_at);
CREATE INDEX idx_channel_memos_user_id ON channel_memos(user_id);
CREATE INDEX idx_channel_memos_message_search ON channel_memos USING gin(to_tsvector('japanese', message));
```

### 5. channel_tasks（チャンネルタスク）

#### テーブル定義
```sql
CREATE TABLE public.channel_tasks (
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

#### 列詳細
| 列名 | 型 | 制約 | 説明 |
|------|-----|------|------|
| id | UUID | PRIMARY KEY | タスク一意識別子 |
| channel_id | TEXT | NOT NULL | SlackチャンネルID |
| channel_name | TEXT | | チャンネル名 |
| title | TEXT | NOT NULL | タスクタイトル |
| description | TEXT | | タスク説明 |
| assigned_user_id | TEXT | | 担当者SlackユーザーID |
| assigned_user_name | TEXT | | 担当者表示名 |
| due_date | DATE | | 期限日 |
| priority | TEXT | DEFAULT 'medium' | 優先度（high/medium/low） |
| status | TEXT | DEFAULT 'pending' | ステータス（pending/completed/cancelled） |
| created_by_user_id | TEXT | NOT NULL | 作成者SlackユーザーID |
| created_by_user_name | TEXT | | 作成者表示名 |
| completed_at | TIMESTAMPTZ | | 完了日時 |
| created_at | TIMESTAMPTZ | NOT NULL | 作成日時 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新日時 |

#### インデックス
```sql
CREATE INDEX idx_channel_tasks_channel_id ON channel_tasks(channel_id);
CREATE INDEX idx_channel_tasks_status ON channel_tasks(status);
CREATE INDEX idx_channel_tasks_assigned_user ON channel_tasks(assigned_user_id);
CREATE INDEX idx_channel_tasks_due_date ON channel_tasks(due_date);
```

## データベース制約

### 外部キー制約
```sql
-- works テーブル
ALTER TABLE works ADD CONSTRAINT fk_works_user_id
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- attendance テーブル
ALTER TABLE attendance ADD CONSTRAINT fk_attendance_user_id
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

### チェック制約
```sql
-- users テーブル
ALTER TABLE users ADD CONSTRAINT chk_users_name_not_empty
  CHECK (LENGTH(TRIM(name)) > 0);

ALTER TABLE users ADD CONSTRAINT chk_users_hourly_wage_positive
  CHECK (hourly_wage IS NULL OR hourly_wage >= 0);

ALTER TABLE users ADD CONSTRAINT chk_users_transportation_cost_positive
  CHECK (transportation_cost IS NULL OR transportation_cost >= 0);

-- works テーブル
ALTER TABLE works ADD CONSTRAINT chk_works_break_time_positive
  CHECK (break_time IS NULL OR break_time >= 0);

ALTER TABLE works ADD CONSTRAINT chk_works_end_after_start
  CHECK (end_time IS NULL OR end_time > start_time);

-- attendance テーブル
ALTER TABLE attendance ADD CONSTRAINT chk_attendance_month_valid
  CHECK (month >= 1 AND month <= 12);

ALTER TABLE attendance ADD CONSTRAINT chk_attendance_day_valid
  CHECK (day >= 1 AND day <= 31);

-- channel_tasks テーブル
ALTER TABLE channel_tasks ADD CONSTRAINT chk_channel_tasks_priority
  CHECK (priority IN ('high', 'medium', 'low'));

ALTER TABLE channel_tasks ADD CONSTRAINT chk_channel_tasks_status
  CHECK (status IN ('pending', 'completed', 'cancelled'));
```

## 全文検索設定

### 日本語全文検索
```sql
-- 日本語検索設定
CREATE TEXT SEARCH CONFIGURATION japanese (COPY = pg_catalog.simple);

-- メモ検索用インデックス
CREATE INDEX idx_channel_memos_fulltext
ON channel_memos USING gin(to_tsvector('japanese', message));
```

### 検索クエリ例
```sql
-- キーワード検索
SELECT * FROM channel_memos
WHERE channel_id = $1
  AND to_tsvector('japanese', message) @@ plainto_tsquery('japanese', $2)
ORDER BY created_at DESC LIMIT 10;
```

## RLS（Row Level Security）設定

### セキュリティポリシー
```sql
-- RLS 有効化
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE works ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;

-- ユーザー自身のデータのみアクセス可能
CREATE POLICY users_self_access ON users
  FOR ALL USING (slack_user_id = current_setting('app.current_user_id'));

CREATE POLICY works_self_access ON works
  FOR ALL USING (user_id IN (
    SELECT id FROM users WHERE slack_user_id = current_setting('app.current_user_id')
  ));

CREATE POLICY attendance_self_access ON attendance
  FOR ALL USING (user_id IN (
    SELECT id FROM users WHERE slack_user_id = current_setting('app.current_user_id')
  ));
```

## データアクセス仕様

### 接続設定
```python
# Supabase接続設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def get_client():
    """Supabaseクライアント取得"""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
```

### CRUD操作パターン

#### Create（作成）
```python
def create_user(user_data: dict) -> dict:
    sb = get_client()
    result = sb.table("users").insert(user_data).execute()
    return to_record(result)[0] if to_record(result) else None
```

#### Read（取得）
```python
def get_user_by_slack_id(slack_user_id: str) -> Optional[dict]:
    sb = get_client()
    result = sb.table("users").select("*").eq("slack_user_id", slack_user_id).execute()
    data = to_record(result)
    return data[0] if data else None
```

#### Update（更新）
```python
def update_user(user_id: str, updates: dict) -> bool:
    sb = get_client()
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = sb.table("users").update(updates).eq("id", user_id).execute()
    return len(to_record(result)) > 0
```

#### Delete（削除）
```python
def delete_user(user_id: str) -> bool:
    sb = get_client()
    result = sb.table("users").delete().eq("id", user_id).execute()
    return len(to_record(result)) > 0
```

## パフォーマンス最適化

### インデックス戦略
- **主要な検索条件にインデックス作成**
- **複合インデックスの活用**
- **全文検索用GINインデックス**
- **日付範囲検索の最適化**

### クエリ最適化
```sql
-- 効率的な月次勤務時間集計
SELECT
  COUNT(*) as work_days,
  SUM(EXTRACT(EPOCH FROM (end_time - start_time)) / 3600 - COALESCE(break_time, 0) / 60.0) as total_hours
FROM works
WHERE user_id = $1
  AND start_time >= $2
  AND start_time < $3
  AND end_time IS NOT NULL;
```

### 接続プール設定
```python
# Supabaseは自動で接続プールを管理
# アプリケーション側では適切なクライアント再利用を実装
```

## バックアップ・リストア

### 自動バックアップ
- **Supabase自動バックアップ**: 日次自動バックアップ
- **ポイントインタイムリカバリ**: 35日間の復旧ポイント
- **レプリケーション**: 自動レプリケーション設定

### 手動エクスポート
```sql
-- データエクスポート例
COPY users TO 'users_backup.csv' CSV HEADER;
COPY works TO 'works_backup.csv' CSV HEADER;
```

## 監視・メンテナンス

### パフォーマンス監視
- **Supabaseダッシュボード**: リアルタイム監視
- **クエリパフォーマンス**: 実行時間とリソース使用量
- **接続数監視**: 同時接続数の追跡

### 定期メンテナンス
- **統計情報更新**: 月次実行
- **インデックス再構築**: 四半期実行
- **不要データ削除**: 年次実行
