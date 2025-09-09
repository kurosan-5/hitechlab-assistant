# 勤怠管理機能仕様書

## 概要
Slackを通じて勤務時間の記録、出勤予定の管理、チーム状況の確認を行う機能

## 機能一覧

### 1. 出勤開始機能
- **コマンド**: `出勤開始`, `しゅっきん`, `start`
- **場所**: DM（ダイレクトメッセージ）
- **処理内容**: 現在時刻で勤務開始を記録

#### 処理フロー
1. ユーザーがコマンドを送信
2. システムが現在の日本時間を取得
3. `works`テーブルに開始記録を作成
4. 確認メッセージを表示

#### データ更新
```sql
INSERT INTO works (user_id, start_time, created_at, updated_at)
VALUES (user_id, CURRENT_TIMESTAMP, NOW(), NOW());
```

### 2. 退勤機能
- **コマンド**: `退勤`, `たいきん`, `end`
- **場所**: DM
- **処理内容**: 勤務終了時刻、休憩時間、コメントを記録

#### 処理フロー
1. ユーザーがコマンドを送信
2. 退勤フォームを表示（日付・時刻・休憩・コメント）
3. ユーザーが入力・送信
4. `works`テーブルの該当レコードを更新
5. 勤務時間を計算して表示

#### UI要素
- **日付選択**: デフォルト今日
- **時刻選択**: デフォルト現在時刻
- **休憩時間**: 分単位での入力
- **コメント**: 任意のテキスト

### 3. 出勤予定機能
- **コマンド**: `出勤更新`, `予定`, `att`
- **場所**: DM
- **処理内容**: 事前の出勤計画を登録

#### 処理フロー
1. ユーザーがコマンドを送信
2. 出勤予定フォームを表示
3. 日付・開始時刻・出勤有無を選択
4. `attendance`テーブルにレコードを保存

#### データ構造
- **出勤予定**: boolean (true: 出勤, false: 休み)
- **開始時刻**: time型 (出勤の場合のみ)
- **日付**: year, month, day カラムで管理

### 4. 出勤確認機能
- **コマンド**: `出勤確認`, `かくにん`, `check`
- **場所**: DM
- **処理内容**: チーム全体の出勤状況を表示

#### 表示内容
- 火曜、金曜日各週の出勤状況（一か月先まで）
- メンバー別の出勤予定・実績

#### 計算ロジック
```python
def get_attendance_status(user, date):
    # 1. attendance テーブルで予定確認
    # 2. works テーブルで実績確認
    # 3. 優先順位: 実績 > 予定 > 未設定
```

### 5. ユーザー勤務情報機能
- **コマンド**: `ユーザー情報`, `プロフィール`, `user`
- **場所**: DM
- **処理内容**: 個人設定と勤務記録の表示・編集

#### サブ機能
- **個人情報編集**: 名前、連絡先、勤務形態
- **給与設定**: 時給、交通費
- **勤務時間確認**: 月別勤務時間集計
- **プロフィール確認**: 現在の設定値表示

## データモデル

### usersテーブル
```sql
CREATE TABLE users (
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

### worksテーブル
```sql
CREATE TABLE works (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  break_time INTEGER,
  comment TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### attendanceテーブル
```sql
CREATE TABLE attendance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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

## 時刻管理仕様

### タイムゾーン処理
- **表示**: 日本時間 (JST, UTC+9)
- **保存**: UTC時刻でデータベース保存
- **変換**: Python datetime + timedelta使用

### 日付境界
- **勤務日判定**: 日本時間の日付で判定
- **勤務時間計算**: UTC時刻で正確な計算

## エラーハンドリング

### 入力値検証
- **日付**: 過去・未来の妥当性チェック
- **時刻**: 24時間形式、分単位まで
- **数値**: 時給・交通費の正の数チェック

### 業務ルール検証
- **重複出勤**: 同日の出勤開始重複チェック
- **退勤前提**: 出勤記録がない場合の退勤エラー
- **時刻整合性**: 開始＜終了時刻のチェック

### エラーメッセージ
```python
ERROR_MESSAGES = {
    "invalid_date": "正しい日付を選択してください。",
    "no_start_record": "対象日の開始記録が見つかりませんでした。",
    "duplicate_start": "この日は既に出勤記録があります。",
    "invalid_time": "正しい時刻を選択してください。"
}
```

## UI仕様

### メニュー表示
```
🏢 勤怠管理メニュー
┣ 📅 出勤開始
┣ 🏃 退勤
┣ 📝 出勤更新
┣ 👥 出勤確認
┗ 👤 ユーザー情報
```

### フォーム要素
- **DatePicker**: Slack標準日付選択
- **TimePicker**: Slack標準時刻選択
- **TextInput**: テキスト入力フィールド
- **Select**: 選択肢ドロップダウン
- **Button**: アクション実行ボタン

## パフォーマンス考慮

### 応答時間
- **即座応答**: 3秒以内でSlack応答
- **フォーム表示**: 1秒以内でUI表示
- **データ取得**: インデックス活用で高速化

## セキュリティ

### アクセス制御
- **DM限定**: 勤怠情報は個人DM内でのみ操作
- **ユーザー認証**: Slack認証による本人確認
- **データ分離**: ユーザー別データの分離保証