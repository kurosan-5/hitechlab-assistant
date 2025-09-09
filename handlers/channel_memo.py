"""
チャンネルメモ機能ハンドラー
チャンネル内のメッセージを記録・検索する機能を提供
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional, List
from boltApp import bolt_app
from db.repository import save_channel_memo, search_channel_memos, get_channel_memo_stats

logger = logging.getLogger(__name__)


def handle_channel_message(event: dict, say, client) -> None:
    """
    チャンネルメッセージを記録

    Args:
        event: Slack イベントデータ
        say: Slack say 関数
        client: Slack Web API クライアント
    """
    try:
        # ボットのメッセージや特定のサブタイプは除外
        if event.get("subtype") or event.get("bot_id"):
            return

        # 削除されたメッセージは除外
        if event.get("subtype") == "message_deleted":
            return

        channel_id = event.get("channel")
        user_id = event.get("user")
        text = event.get("text", "").strip()
        message_ts = event.get("ts")
        thread_ts = event.get("thread_ts")

        # 空のメッセージは除外
        if not text:
            return

        # チャンネル情報を取得
        try:
            channel_info = client.conversations_info(channel=channel_id)
            channel_name = channel_info.get("channel", {}).get("name", "unknown")
        except Exception as e:
            channel_name = "unknown"

        # ユーザー情報を取得
        try:
            user_info = client.users_info(user=user_id)
            user_profile = user_info.get("user", {}).get("profile", {})
            user_name = (
                user_profile.get("real_name") or
                user_profile.get("display_name") or
                user_info.get("user", {}).get("name", "unknown")
            )
        except Exception as e:
            user_name = "unknown"

        # パーマリンクを生成
        try:
            permalink_response = client.chat_getPermalink(
                channel=channel_id,
                message_ts=message_ts
            )
            permalink = permalink_response.get("permalink")
        except Exception as e:
            permalink = None

        # データベースに保存
        memo_data = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "user_id": user_id,
            "user_name": user_name,
            "message": text,
            "message_ts": message_ts,
            "thread_ts": thread_ts,
            "permalink": permalink
        }

        saved_memo = save_channel_memo(memo_data)

    except Exception as e:
        pass


def handle_memo_search(event: dict, say, client) -> None:
    """
    メモ検索コマンドを処理

    使用例:
    - メモ検索 keyword
    - memo search keyword
    - !search keyword
    """
    try:
        text = event.get("text", "").strip()
        user_id = event.get("user")
        channel_id = event.get("channel")

        # 検索キーワードを抽出
        search_patterns = [
            "メモ検索 ",
            "memo search ",
            "!search "
        ]

        keyword = None
        for pattern in search_patterns:
            if text.lower().startswith(pattern.lower()):
                keyword = text[len(pattern):].strip()
                break

        if not keyword:
            return

        # 検索実行
        memos = search_channel_memos(
            keyword=keyword,
            channel_id=channel_id,
            limit=10
        )

        if not memos:
            say(f"「{keyword}」に関するメモが見つかりませんでした。")
            return

        # 検索結果を整形
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔍 メモ検索結果: {keyword}",
                    "emoji": True
                }
            }
        ]

        for memo in memos:
            created_at = datetime.fromisoformat(memo["created_at"].replace("Z", "+00:00"))
            jst_time = created_at.astimezone(timezone.utc).strftime("%m/%d %H:%M")

            memo_text = memo["message"]
            if len(memo_text) > 100:
                memo_text = memo_text[:100] + "..."

            block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{memo['user_name']}* ({jst_time})\n{memo_text}"
                }
            }

            if memo.get("permalink"):
                block["accessory"] = {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "元メッセージ",
                        "emoji": True
                    },
                    "url": memo["permalink"]
                }

            blocks.append(block)

        # 最大10件の制限メッセージ
        if len(memos) == 10:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 最新10件のみ表示しています。より具体的なキーワードで検索すると、より関連性の高い結果が得られます。"
                    }
                ]
            })

        say(blocks=blocks, text=f"メモ検索結果: {keyword}")

    except Exception as e:
        say("検索中にエラーが発生しました。しばらく後に再試行してください。")


def handle_memo_stats(event: dict, say, client) -> None:
    """
    メモ統計コマンドを処理

    使用例:
    - メモ統計
    - memo stats
    """
    try:
        text = event.get("text", "").strip().lower()
        channel_id = event.get("channel")

        if text not in ["メモ統計", "memo stats"]:
            return

        # 統計情報を取得
        stats = get_channel_memo_stats(channel_id)

        if not stats:
            say("このチャンネルにはまだメモがありません。")
            return

        # チャンネル名を取得
        try:
            channel_info = client.conversations_info(channel=channel_id)
            channel_name = channel_info.get("channel", {}).get("name", "unknown")
        except Exception:
            channel_name = "unknown"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 #{channel_name} メモ統計",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*総メモ数:*\n{stats['total_memos']:,} 件"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*参加ユーザー数:*\n{stats['unique_users']} 人"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*最初のメモ:*\n{stats['first_memo_date']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*最新のメモ:*\n{stats['last_memo_date']}"
                    }
                ]
            }
        ]

        if stats.get("top_users"):
            user_list = "\n".join([
                f"{i+1}. {user['user_name']}: {user['memo_count']}件"
                for i, user in enumerate(stats["top_users"][:5])
            ])

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*アクティブユーザー Top 5:*\n{user_list}"
                }
            })

        say(blocks=blocks, text=f"#{channel_name} メモ統計")

    except Exception as e:
        say("統計情報の取得中にエラーが発生しました。")


def handle_channel_memo_logic(event, body, say, client):
    """チャンネルメモロジック（統一ハンドラーから呼び出される）"""
    # ボットのメッセージは無視
    if event.get("subtype") or event.get("bot_id"):
        return

    text = event.get("text", "").strip()

    # メニューコマンドは統一ハンドラーで処理されるため、ここでは処理しない
    menu_patterns = ["メニュー", "めにゅー", "menu"]
    if text.lower() in [pattern.lower() for pattern in menu_patterns]:
        return

    # !taskコマンドは統一ハンドラーで処理されるため、ここでは処理しない
    if text.lower().startswith("!task"):
        return

    # !searchとか!recentコマンドの処理
    if text.lower().startswith("!search "):
        # !search を メモ検索 形式に変換して処理
        keyword = text[8:].strip()  # "!search " を除去
        converted_text = f"メモ検索 {keyword}"
        event_copy = event.copy()
        event_copy["text"] = converted_text
        handle_memo_search(event_copy, say, client)
        return
    elif text.lower().startswith("!recent"):
        # !recent コマンドの処理
        from db.repository import get_recent_memos
        try:
            # 日数指定があるかチェック
            parts = text.split()
            days = 7  # デフォルト7日
            if len(parts) > 1 and parts[1].isdigit():
                days = int(parts[1])

            channel_id = event.get("channel")
            memos = get_recent_memos(channel_id, days=days)

            if not memos:
                say(f"過去{days}日間のメモが見つかりませんでした。")
                return

            # 結果を表示
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📝 過去{days}日間のメモ"
                    }
                }
            ]

            for memo in memos[:10]:  # 最大10件
                created_at = datetime.fromisoformat(memo["created_at"].replace("Z", "+00:00"))
                jst_time = created_at.astimezone(timezone.utc).strftime("%m/%d %H:%M")

                memo_text = memo["message"]
                if len(memo_text) > 100:
                    memo_text = memo_text[:100] + "..."

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{memo['user_name']}* ({jst_time})\n{memo_text}"
                    }
                })

            say(text=f"過去{days}日間のメモ", blocks=blocks)

        except Exception as e:
            say(text="最近のメモの取得中にエラーが発生しました。")
        return

    # メモ検索コマンドの処理（!memoは廃止され、searchコマンドのみ）
    search_patterns = ["メモ検索 ", "memo search ", "!search "]
    if any(text.lower().startswith(pattern.lower()) for pattern in search_patterns):
        handle_memo_search(event, say, client)
        return

    # メモ統計コマンドの処理
    if text.lower() in ["メモ統計", "memo stats"]:
        handle_memo_stats(event, say, client)
        return

    # 通常のメッセージをメモとして記録
    handle_channel_message(event, say, client)
