"""
チャンネルタスク管理機能
"""

from typing import Dict, Any, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime

from db.repository import (
    get_channel_tasks,
    save_channel_task,
    update_task_status,
    delete_task
)


def create_task_create_form_blocks() -> list[Dict[str, Any]]:
    """タスク作成フォーム用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "➕ タスク作成"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "新しいタスクを作成します。必須項目を入力してください："
            }
        },
        {
            "type": "input",
            "block_id": "task_name_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "task_name_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "例: プレゼン資料作成、会議準備..."
                }
            },
            "label": {
                "type": "plain_text",
                "text": "タスク名 *"
            }
        },
        {
            "type": "input",
            "block_id": "task_description_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "task_description_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "タスクの詳細説明（任意）"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "説明"
            },
            "optional": True
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ 作成"
                    },
                    "style": "primary",
                    "action_id": "execute_task_create"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "❌ キャンセル"
                    },
                    "action_id": "cancel_task_create"
                }
            ]
        }
    ]


def create_filter_button(text: str, action_id: str, is_active: bool = False) -> Dict[str, Any]:
    """フィルターボタンを作成"""
    button = {
        "type": "button",
        "text": {
            "type": "plain_text",
            "text": text
        },
        "action_id": action_id
    }
    if is_active:
        button["style"] = "primary"
    return button


def create_task_list_blocks(tasks: List[Dict], filter_status: str = "all") -> list[Dict[str, Any]]:
    """タスク一覧表示用のブロックを作成"""
    # フィルタリング
    if filter_status == "completed":
        filtered_tasks = [task for task in tasks if task.get('status') == 'completed']
        title = "📋 完了済みタスク"
    elif filter_status == "pending":
        filtered_tasks = [task for task in tasks if task.get('status') != 'completed']
        title = "📋 未完了タスク"
    else:
        filtered_tasks = tasks
        title = "📋 全てのタスク"

    if not filtered_tasks:
        empty_message = {
            "completed": "完了済みのタスクはありません。",
            "pending": "未完了のタスクはありません。",
            "all": "現在、登録されているタスクはありません。"
        }.get(filter_status, "タスクはありません。")

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": empty_message
                }
            },
            # フィルターボタン
            {
                "type": "actions",
                "elements": [
                    create_filter_button("📋 全て", "show_task_list_all", filter_status == "all"),
                    create_filter_button("⏳ 未完了", "show_task_list_pending", filter_status == "pending"),
                    create_filter_button("✅ 完了済み", "show_task_list_completed", filter_status == "completed")
                ]
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

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"表示中: *{len(filtered_tasks)}件* / 全体: *{len(tasks)}件*"
            }
        },
        # フィルターボタン
        {
            "type": "actions",
            "elements": [
                create_filter_button("📋 全て", "show_task_list_all", filter_status == "all"),
                create_filter_button("⏳ 未完了", "show_task_list_pending", filter_status == "pending"),
                create_filter_button("✅ 完了済み", "show_task_list_completed", filter_status == "completed")
            ]
        },
        {
            "type": "divider"
        }
    ]

    for task in filtered_tasks:
        status_emoji = "✅" if task['status'] == 'completed' else "⏳"
        created_at = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
        formatted_date = created_at.strftime('%Y-%m-%d %H:%M')

        task_text = f"*{task['task_name']}* {status_emoji}\n"
        if task.get('description'):
            task_text += f"{task['description'][:100]}{'...' if len(task['description']) > 100 else ''}\n"
        task_text += f"作成者: <@{task['user_id']}> | 作成日: {formatted_date}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": task_text
            },
            "accessory": {
                "type": "overflow",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "✅ 完了にする" if task['status'] != 'completed' else "⏳ 未完了にする"
                        },
                        "value": f"toggle_task_status_{task['id']}"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "🗑️ 削除"
                        },
                        "value": f"delete_task_{task['id']}"
                    }
                ],
                "action_id": "task_action"
            }
        })
        blocks.append({"type": "divider"})

    # 戻るボタン
    blocks.append({
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
    })

    return blocks


def create_task_management_blocks() -> list[Dict[str, Any]]:
    """タスク管理メニュー用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📋 タスク管理"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*利用可能な機能*\n\n• タスクの作成・編集・削除\n• タスク一覧の表示\n• ステータス管理"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 タスク一覧"
                    },
                    "style": "primary",
                    "action_id": "show_task_list"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "➕ タスク作成"
                    },
                    "style": "primary",
                    "action_id": "show_task_create_form"
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
                        "text": "🔙 メニューに戻る"
                    },
                    "action_id": "show_channel_menu"
                }
            ]
        }
    ]
