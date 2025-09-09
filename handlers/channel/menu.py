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
                        "text": "� メモ作成"
                    },
                    "style": "primary",
                    "action_id": "show_memo_create"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 メモ検索"
                    },
                    "action_id": "show_memo_search"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "� メモ一覧"
                    },
                    "action_id": "show_memo_list"
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
                        "text": "� メモ統計"
                    },
                    "action_id": "show_memo_stats"
                },
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
                "text": "*� メモ機能*\n• `!memo 内容` または `!m 内容` または `!メモ 内容` でメモを作成\n• 会話は自動的にメモとして記録されます\n• `!memo` でメモ一覧を表示（スレッドに返信）\n• メニューから検索・統計情報を確認可能"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📋 タスク管理*\n• `!task タスク名` でタスクを作成\n• メニューからGUIでタスク管理が可能"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📱 基本コマンド*\n• `メニュー` または `menu` でメニューを表示\n\n*💡 使用例*\n• `!memo 明日2時に待ち合わせ` - メモ作成\n• `!m 会議資料の確認` - メモ作成（短縮版）\n• `!task プレゼン準備` - タスク作成"
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
