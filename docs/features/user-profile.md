# ユーザープロファイル機能仕様書

## 概要
Slackユーザーの個人情報、勤務設定、勤務履歴を管理する機能

## 機能一覧

### 1. プロフィール表示機能
- **コマンド**: `ユーザー情報`, `プロフィール`, `user`
- **場所**: DM（ダイレクトメッセージ）
- **機能**: 現在の個人設定と基本情報を表示

#### 表示内容
- **基本情報**: 名前、Slack表示名、登録日
- **連絡先**: 電話番号、メールアドレス等
- **勤務情報**: 勤務形態、時給、交通費
- **統計情報**: 総勤務時間、今月の勤務時間

#### 表示形式
```
👤 ユーザープロフィール
┣ 📝 名前: 山田太郎
┣ 💬 Slack表示名: @yamada
┣ 📞 連絡先: 090-1234-5678
┣ 💼 勤務形態: アルバイト
┣ 💰 時給: 1,500円
┣ 🚃 交通費: 500円
┗ 📊 今月勤務: 12時間
```

### 2. プロフィール編集機能
- **アクセス**: ユーザー情報メニュー → 各種編集ボタン
- **場所**: DM
- **機能**: 個人情報の編集・更新

#### 編集可能項目
- **名前**: フルネーム（必須）
- **連絡先**: 電話番号、メールアドレス
- **勤務形態**: 正社員、契約社員、アルバイト、派遣
- **時給**: 時間あたりの報酬額
- **交通費**: 日額の交通費

#### 編集フロー
1. 編集対象項目のボタンクリック
2. 入力フォーム表示
3. 新しい値を入力
4. 保存実行
5. 更新完了メッセージ表示

### 3. 勤務時間確認機能
- **アクセス**: ユーザー情報メニュー → 勤務時間確認
- **場所**: DM
- **機能**: 指定月の勤務時間と給与計算

#### 確認フロー
1. 勤務時間確認ボタンクリック
2. 年月入力フォーム表示（YYYYMM形式）
3. 対象月の勤務データ集計
4. 結果表示（勤務時間・給与・詳細）

#### 表示内容
- **勤務日数**: 実際に働いた日数
- **総勤務時間**: 時間・分での表示

#### 計算式
```python
# 勤務時間計算
work_hours = (end_time - start_time - break_time_minutes) / 60
```

### 4. ユーザー自動登録機能
- **トリガー**: 初回Slack操作時
- **場所**: システム内部処理
- **機能**: Slackユーザー情報の自動取得・登録

#### 自動取得情報
- **SlackユーザーID**: 一意識別子
- **表示名**: Slackプロフィールの名前
- **リアルネーム**: Slackプロフィールの本名
- **登録日時**: アカウント作成時刻

#### 初期値設定
- **名前**: Slack表示名またはリアルネーム
- **勤務形態**: null（未設定）
- **時給**: null（未設定）
- **交通費**: null（未設定）

## データモデル

### usersテーブル詳細
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,                    -- ユーザー名
  slack_user_id TEXT UNIQUE,             -- SlackユーザーID
  slack_display_name TEXT,               -- Slack表示名
  contact TEXT,                          -- 連絡先
  work_type TEXT,                        -- 勤務形態
  transportation_cost NUMERIC,           -- 交通費（日額）
  hourly_wage NUMERIC,                   -- 時給
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### バリデーション
- **name**: 必須、100文字以内
- **contact**: 任意、200文字以内
- **work_type**: 任意、50文字以内
- **transportation_cost**: 任意、0以上の数値
- **hourly_wage**: 任意、0以上の数値

## ビジネスロジック

### ユーザー取得・作成
```python
def get_or_create_user(slack_user_id: str, display_name: str) -> User:
    """
    Slackユーザーの取得または新規作成
    1. slack_user_idで検索
    2. 存在しない場合は新規作成
    3. Slack表示名を自動設定
    """
    user = find_user_by_slack_id(slack_user_id)
    if not user:
        user = create_user({
            'name': display_name or slack_user_id,
            'slack_user_id': slack_user_id,
            'slack_display_name': display_name
        })
    return user
```

### 勤務時間集計
```python
def calculate_monthly_work_summary(user_id: str, year: int, month: int):
    """
    指定月の勤務サマリー計算
    1. 該当月のworksレコード取得
    2. 勤務時間の計算（休憩時間を除く）
    """
    works = get_works_by_month(user_id, year, month)

    total_hours = 0
    work_days = 0

    for work in works:
        if work.end_time:
            hours = calculate_work_hours(work)
            total_hours += hours
            work_days += 1

    return {
        'total_hours': total_hours,
        'work_days': work_days
    }
```

### プロフィール更新
```python
def update_user_profile(user_id: str, field: str, value: any) -> bool:
    """
    ユーザープロフィールの部分更新
    1. 入力値の検証
    2. データベース更新
    3. updated_at自動更新
    """
    if not validate_profile_field(field, value):
        return False

    return update_user_field(user_id, field, value)
```

## UI設計仕様

### プロフィール表示
```json
{
  "type": "section",
  "fields": [
    {"type": "mrkdwn", "text": "*名前:* 山田太郎"},
    {"type": "mrkdwn", "text": "*Slack名:* @yamada"},
    {"type": "mrkdwn", "text": "*連絡先:* 090-1234-5678"},
    {"type": "mrkdwn", "text": "*勤務形態:* アルバイト"}
  ]
}
```

### 編集フォーム
```json
{
  "type": "modal",
  "title": "プロフィール編集",
  "blocks": [
    {
      "type": "input",
      "label": "名前",
      "element": {
        "type": "plain_text_input",
        "action_id": "edit_name",
        "initial_value": "現在の名前",
        "max_length": 100
      }
    }
  ]
}
```

### 勤務時間表示
```json
{
  "type": "section",
  "text": {
    "type": "mrkdwn",
    "text": "*2024年12月の勤務実績*\n• 勤務日数: 20日\n• 総勤務時間: 160時間\n"
  }
}
```

## API仕様

### ユーザー情報取得
```python
def get_user_by_slack_id(slack_user_id: str) -> Optional[User]:
    """Slack IDによるユーザー取得"""

def get_user_profile(user_id: str) -> dict:
    """ユーザープロフィール詳細取得"""
```

### ユーザー情報更新
```python
def update_user_name(user_id: str, name: str) -> bool:
    """ユーザー名更新"""

def update_user_contact(user_id: str, contact: str) -> bool:
    """連絡先更新"""

def update_user_work_info(user_id: str, work_type: str,
                         hourly_wage: float, transportation_cost: float) -> bool:
    """勤務情報更新"""
```

### 勤務統計取得
```python
def get_monthly_work_stats(user_id: str, year: int, month: int) -> dict:
    """月次勤務統計取得"""

def get_user_work_summary(user_id: str) -> dict:
    """ユーザー勤務サマリー取得"""
```

## エラーハンドリング

### 入力値検証
```python
def validate_user_input(field: str, value: str) -> tuple[bool, str]:
    """
    ユーザー入力の検証
    Returns: (is_valid, error_message)
    """
    if field == 'name':
        if not value.strip():
            return False, "名前は必須です"
        if len(value) > 100:
            return False, "名前は100文字以内で入力してください"

    elif field == 'hourly_wage':
        try:
            wage = float(value)
            if wage < 0:
                return False, "時給は0以上で入力してください"
        except ValueError:
            return False, "時給は数値で入力してください"

    return True, ""
```

### 業務ルール検証
- **重複ユーザー**: 同一Slack IDの重複登録防止
- **必須項目**: 名前の空文字列チェック
- **数値範囲**: 時給・交通費の負数チェック

### エラーメッセージ
```python
ERROR_MESSAGES = {
    'user_not_found': 'ユーザー情報が見つかりません',
    'invalid_month': '正しい年月を入力してください（YYYYMM形式）',
    'update_failed': 'プロフィールの更新に失敗しました',
    'no_work_data': '指定された月の勤務データがありません'
}
```

## セキュリティ仕様

### アクセス制御
- **DM限定**: プロフィール情報はDMでのみ表示・編集
- **本人限定**: 自分のプロフィールのみ操作可能
- **Slack認証**: Slack IDによる本人確認

### データ保護
- **個人情報保護**: 他ユーザーからのアクセス制限
- **暗号化**: データベース通信・保存の暗号化
- **監査ログ**: プロフィール変更の記録保持

### プライバシー
- **情報開示制限**: 必要最小限の情報のみ表示
- **データ保持期間**: 退職後のデータ削除ポリシー
- **同意管理**: データ利用に関する同意確認

## パフォーマンス仕様

### 応答時間目標
- **プロフィール表示**: 1秒以内
- **情報更新**: 2秒以内
- **勤務統計**: 3秒以内

### スケーラビリティ
- **ユーザー数**: 1,000ユーザーまで
- **勤務データ**: ユーザーあたり年間3,000レコード
- **同時アクセス**: 50並行処理まで

### 最適化施策
- **クエリ最適化**: インデックス活用
- **キャッシュ**: プロフィール情報のキャッシュ
- **レスポンス最適化**: 不要データの除外
