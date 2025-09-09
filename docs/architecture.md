# システムアーキテクチャ

## 全体アーキテクチャ

### システム構成図
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Slack Client  │◄──►│   Slack API     │◄──►│   Render/Web    │
│  (ユーザー端末)  │    │  (Event/OAuth)  │    │   (本システム)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   Supabase      │
                                               │  (PostgreSQL)   │
                                               └─────────────────┘
```

### アプリケーション層構成
```
┌─────────────────────────────────────────────────────────────┐
│                     Slack Bolt App                         │
├─────────────────────────────────────────────────────────────┤
│                      Flask Server                          │
├─────────────────────────────────────────────────────────────┤
│  Handler Layer (Business Logic)                            │
│  ├── attendance.py     (勤怠管理)                           │
│  ├── channel_memo.py   (チャンネルメモ)                      │
│  ├── workflows.py      (ワークフロー)                       │
│  ├── user_profile.py   (ユーザー管理)                       │
│  └── channel/          (チャンネル機能群)                    │
├─────────────────────────────────────────────────────────────┤
│  Repository Layer (Data Access)                            │
│  ├── repository.py     (データアクセス)                      │
│  └── supabase_client.py (DB接続)                           │
├─────────────────────────────────────────────────────────────┤
│  Database Layer (Supabase PostgreSQL)                      │
│  ├── users            (ユーザー情報)                        │
│  ├── works            (勤務記録)                           │
│  ├── attendance       (出勤予定)                           │
│  ├── channel_memos    (チャンネルメモ)                      │
│  └── channel_tasks    (チャンネルタスク)                    │
└─────────────────────────────────────────────────────────────┘
```

## 技術スタック詳細

### フロントエンド
- **Slack Client**: ネイティブSlackアプリ
- **Block Kit UI**: Slack公式UIフレームワーク
- **Interactive Components**: ボタン、モーダル、フォーム

### バックエンド
- **Python 3.8+**: メイン開発言語
- **Slack Bolt for Python**: Slackアプリフレームワーク
- **Flask**: WebフレームワークとHTTPサーバー
- **python-dotenv**: 環境変数管理

### データベース
- **Supabase**: BaaS (Backend as a Service)
- **PostgreSQL**: リレーショナルデータベース
- **Real-time subscriptions**: リアルタイム更新機能

### インフラ・デプロイメント
- **Render**: クラウドホスティング
- **GitHub**: ソースコード管理
- **Environment Variables**: 設定管理

### 外部サービス連携
- **Slack API**: Event Subscriptions, Web API

## データフロー

### 1. ユーザーインタラクション
```
User Input (Slack) → Slack API → Bolt App → Handler → Repository → Database
                                    ↓
User Feedback (Slack) ← Slack API ← Response ← Business Logic ← Data
```

### 2. イベント処理フロー
```
Slack Event → app.py → unified_handler → specific_handler → response
     ↓
  Event Type Detection (DM/Channel/Command)
     ↓
  Handler Selection (attendance/memo/task/profile)
     ↓
  Business Logic Processing
     ↓
  Database Operation (CRUD)
     ↓
  Response Generation (Blocks/Text)
     ↓
  Slack API Response
```

### 3. データ同期フロー
```
User Action → Immediate Response → Database Update → State Sync
                     ↓
              UI Update (Slack) ← State Reflection ← Database
```

## セキュリティアーキテクチャ

### 認証・認可
```
Slack OAuth 2.0 → Token Validation → App Authentication
        ↓
User Identification → Permission Check → Function Access
        ↓
Database Access → Row Level Security → Data Protection
```

### データ保護
- **通信暗号化**: HTTPS/TLS 1.2+
- **データベース暗号化**: Supabase標準暗号化
- **環境変数暗号化**: 本番環境での秘匿情報保護
- **アクセス制御**: Slack認証基盤の活用

## スケーラビリティ設計

### 水平スケーリング
- **ステートレス設計**: セッション情報なし
- **データベース分離**: ビジネスロジックとデータの分離
- **API設計**: RESTful原則準拠

### 垂直スケーリング
- **非同期処理**: 重い処理の背景実行
- **キャッシュ戦略**: 頻繁アクセスデータの最適化
- **インデックス最適化**: データベースクエリ性能向上

## 障害対応アーキテクチャ

### エラーハンドリング階層
```
1. UI Level: User-friendly error messages
2. Handler Level: Business logic error handling
3. Repository Level: Database error handling
4. Infrastructure Level: Network/system error handling
```

### 復旧メカニズム
- **Graceful Degradation**: 部分機能停止時の代替機能
- **Retry Logic**: 一時的障害時の自動再試行
- **Fallback Systems**: 主系障害時の代替システム
- **Health Checks**: システム状態監視

## パフォーマンス設計

### レスポンス時間最適化
- **3秒ルール**: Slack応答期限内での処理完了
- **非同期応答**: 長時間処理の背景実行
- **データベース最適化**: インデックスとクエリチューニング

### リソース効率化
- **メモリ管理**: 適切なオブジェクト生成・破棄
- **接続プール**: データベース接続の効率化
- **レート制限**: API呼び出し頻度の制御

## 開発・運用アーキテクチャ

### CI/CD パイプライン
```
GitHub Repository → Auto Deploy → Render Platform
```

### 監視・ロギング
- **アプリケーションログ**: Python logging module
- **エラー追跡**: Exception handling and reporting
- **パフォーマンス監視**: Response time tracking
- **ヘルスチェック**: システム稼働状況確認
