"""
チャンネルメニュー機能
"""

from typing import Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def handle_channel_menu(message, say, client: WebClient):
    """チャンネルでメニューを表示（外部呼び出し用）"""
    try:
        channel_id = message["channel"]

        # メニューブロックを作成
        blocks = create_channel_menu_blocks()

        say(
            text="📱 チャンネルメニュー",
            blocks=blocks
        )

    except SlackApiError as e:
        print(f"Error showing channel menu: {e}")
        say(text="❌ メニューの表示中にエラーが発生しました")


def create_channel_menu_blocks() -> list[Dict[str, Any]]:
    """チャンネルメニュー用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "チャンネルメニュー"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*利用可能な機能*\n\n🔍 メモ検索・統計\n📋 タスク管理\n💬 会話の自動記録"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 メモ検索"
                    },
                    "style": "primary",
                    "action_id": "show_memo_search"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "メモ一覧"
                    },
                    "action_id": "show_memo_list"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 メモ統計"
                    },
                    "action_id": "show_memo_stats"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 タスク管理"
                    },
                    "style": "primary",
                    "action_id": "show_task_management"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📖 ヘルプ"
                    },
                    "action_id": "show_channel_help"
                }
            ]
        }
    ]


def create_channel_help_blocks() -> list[Dict[str, Any]]:
    """チャンネルヘルプ用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📖 チャンネル機能ヘルプ"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🔍 メモ機能*\n• 会話は自動的にメモとして記録されます\n• `!memo` でメモ一覧を表示（スレッドに返信）\n• `!search キーワード` でメモを検索\n• `最近のメモ` で最新のメモを表示\n• メニューから統計情報を確認可能"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📋 タスク管理*\n• `タスク作成 タスク名 説明` でタスクを作成\n• `タスク一覧` で全タスクを表示\n• メニューからGUIでタスク管理が可能"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📱 メニュー表示*\n• `メニュー` または `めにゅー` または `menu` でメニューを表示"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔙 メニューに戻る"
                    },
                    "action_id": "show_channel_menu"
                }
            ]
        }
    ]
