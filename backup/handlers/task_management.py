"""
チャンネルタスク管理機能ハンドラー
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime

from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from db.repository import (
    save_channel_task,
    get_channel_tasks,
    update_task_status,
    update_task_content,
    delete_task,
    get_task_by_id,
    utc_now
)


def handle_create_task(message, say, client: WebClient):
    """!task コマンドでタスクを作成（外部呼び出し用）"""
    try:
        # コマンドからタスク名を抽出
        match = re.match(r"^!task\s+(.+)", message["text"], re.IGNORECASE)
        if not match:
            say(text="タスク名を指定してください。例: `!task 会議の準備`")
            return

        task_name = match.group(1).strip()

        # チャンネル情報を取得
        channel_id = message["channel"]
        channel_info = client.conversations_info(channel=channel_id)
        channel_name = channel_info["channel"]["name"] if channel_info["ok"] else "unknown"

        # ユーザー情報を取得
        user_id = message["user"]
        user_info = client.users_info(user=user_id)
        user_name = user_info["user"]["real_name"] if user_info["ok"] else "unknown"

        # タスクデータを作成
        task_data = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "user_id": user_id,
            "user_name": user_name,
            "task_name": task_name,
            "description": "",
            "status": "pending",
            "created_at": utc_now().isoformat()
        }

        # データベースに保存
        saved_task = save_channel_task(task_data)

        if saved_task:
            say(
                text=f"✅ タスクを作成しました",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"✅ *タスクを作成しました*\n\n*タスク名:* {task_name}\n*作成者:* <@{user_id}>\n*ステータス:* 未完了"
                        }
                    }
                ]
            )
        else:
            say(text="❌ タスクの作成に失敗しました")

    except Exception as e:
        print(f"Error handling create task: {e}")
        say(text="❌ タスクの作成中にエラーが発生しました")


def register_task_handlers(app: App):
    """タスク管理関連のハンドラーを登録"""

    @app.message(re.compile(r"^!task\s+(.+)", re.IGNORECASE))
    def handle_create_task(message, say, client: WebClient):
        """!task コマンドでタスクを作成"""
        try:
            # コマンドからタスク名を抽出
            match = re.match(r"^!task\s+(.+)", message["text"], re.IGNORECASE)
            if not match:
                say(text="タスク名を指定してください。例: `!task 会議の準備`")
                return

            task_name = match.group(1).strip()

            # チャンネル情報を取得
            channel_id = message["channel"]
            channel_info = client.conversations_info(channel=channel_id)
            channel_name = channel_info["channel"]["name"] if channel_info["ok"] else "unknown"

            # ユーザー情報を取得
            user_id = message["user"]
            user_info = client.users_info(user=user_id)
            user_name = user_info["user"]["real_name"] if user_info["ok"] else "unknown"

            # タスクデータを作成
            task_data = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "user_id": user_id,
                "user_name": user_name,
                "task_name": task_name,
                "description": "",
                "status": "pending",
                "created_at": utc_now().isoformat()
            }

            # データベースに保存
            saved_task = save_channel_task(task_data)

            if saved_task:
                say(
                    text=f"✅ タスクを作成しました",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"✅ *タスクを作成しました*\n\n*タスク名:* {task_name}\n*作成者:* <@{user_id}>\n*ステータス:* 未完了"
                            }
                        }
                    ]
                )
            else:
                say(text="❌ タスクの作成に失敗しました")

        except Exception as e:
            print(f"Error handling create task: {e}")
            say(text="❌ タスクの作成中にエラーが発生しました")


def handle_task_complete(ack, body, say, client: WebClient):
    """タスク完了処理（外部呼び出し用）"""
    try:
        task_id = body["actions"][0]["value"]

        # タスクを完了状態に更新
        success = update_task_status(task_id, "completed", utc_now())

        if success:
            # 完了したタスクの情報を取得
            task = get_task_by_id(task_id)
            if task:
                say(
                    text="✅ タスク完了",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"✅ *タスクが完了しました*\n\n*タスク名:* {task['task_name']}\n*完了者:* <@{body['user']['id']}>"
                            }
                        }
                    ]
                )
            else:
                say(text="✅ タスクを完了しました")
        else:
            say(text="❌ タスクの完了処理に失敗しました")

    except Exception as e:
        print(f"Error handling task complete: {e}")
        say(text="❌ タスクの完了処理中にエラーが発生しました")


def handle_task_cancel(ack, body, say, client: WebClient):
    """タスクキャンセル処理（外部呼び出し用）"""
    try:
        task_id = body["actions"][0]["value"]

        # タスクをキャンセル状態に更新
        success = update_task_status(task_id, "cancelled")

        if success:
            # キャンセルしたタスクの情報を取得
            task = get_task_by_id(task_id)
            if task:
                say(
                    text="🚫 タスクキャンセル",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"🚫 *タスクがキャンセルされました*\n\n*タスク名:* {task['task_name']}\n*キャンセル者:* <@{body['user']['id']}>"
                            }
                        }
                    ]
                )
            else:
                say(text="🚫 タスクをキャンセルしました")
        else:
            say(text="❌ タスクのキャンセル処理に失敗しました")

    except Exception as e:
        print(f"Error handling task cancel: {e}")
        say(text="❌ タスクのキャンセル処理中にエラーが発生しました")


def handle_task_delete(ack, body, say, client: WebClient):
    """タスク削除処理（外部呼び出し用）"""
    try:
        task_id = body["actions"][0]["value"]

        # タスクの情報を取得（削除前に）
        task = get_task_by_id(task_id)

        # タスクを削除
        success = delete_task(task_id)

        if success:
            if task:
                say(
                    text="🗑️ タスク削除",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"🗑️ *タスクが削除されました*\n\n*タスク名:* {task['task_name']}\n*削除者:* <@{body['user']['id']}>"
                            }
                        }
                    ]
                )
            else:
                say(text="🗑️ タスクを削除しました")
        else:
            say(text="❌ タスクの削除に失敗しました")

    except Exception as e:
        print(f"Error handling task delete: {e}")
        say(text="❌ タスクの削除中にエラーが発生しました")


def register_task_handlers(app: App):


    @app.action("task_complete")
    def handle_task_complete(ack, body, say, client: WebClient):
        """タスク完了ボタンの処理"""
        ack()
        try:
            task_id = body["actions"][0]["value"]

            # タスクを完了状態に更新
            success = update_task_status(task_id, "completed", utc_now())

            if success:
                # 完了したタスクの情報を取得
                task = get_task_by_id(task_id)
                if task:
                    say(
                        text=f"✅ タスク完了",
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"✅ *タスクが完了しました*\n\n*タスク名:* {task['task_name']}\n*完了者:* <@{body['user']['id']}>"
                                }
                            }
                        ]
                    )
                else:
                    say(text="✅ タスクを完了しました")
            else:
                say(text="❌ タスクの完了処理に失敗しました")

        except Exception as e:
            print(f"Error handling task complete: {e}")
            say(text="❌ タスクの完了処理中にエラーが発生しました")


    @app.action("task_cancel")
    def handle_task_cancel(ack, body, say, client: WebClient):
        """タスクキャンセルボタンの処理"""
        ack()
        try:
            task_id = body["actions"][0]["value"]

            # タスクをキャンセル状態に更新
            success = update_task_status(task_id, "cancelled")

            if success:
                # キャンセルしたタスクの情報を取得
                task = get_task_by_id(task_id)
                if task:
                    say(
                        text=f"🚫 タスクキャンセル",
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"🚫 *タスクがキャンセルされました*\n\n*タスク名:* {task['task_name']}\n*キャンセル者:* <@{body['user']['id']}>"
                                }
                            }
                        ]
                    )
                else:
                    say(text="🚫 タスクをキャンセルしました")
            else:
                say(text="❌ タスクのキャンセル処理に失敗しました")

        except Exception as e:
            print(f"Error handling task cancel: {e}")
            say(text="❌ タスクのキャンセル処理中にエラーが発生しました")


    @app.action("task_delete")
    def handle_task_delete(ack, body, say, client: WebClient):
        """タスク削除ボタンの処理"""
        ack()
        try:
            task_id = body["actions"][0]["value"]

            # タスクの情報を取得（削除前に）
            task = get_task_by_id(task_id)

            # タスクを削除
            success = delete_task(task_id)

            if success:
                if task:
                    say(
                        text=f"🗑️ タスク削除",
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"🗑️ *タスクが削除されました*\n\n*タスク名:* {task['task_name']}\n*削除者:* <@{body['user']['id']}>"
                                }
                            }
                        ]
                    )
                else:
                    say(text="🗑️ タスクを削除しました")
            else:
                say(text="❌ タスクの削除に失敗しました")

        except Exception as e:
            print(f"Error handling task delete: {e}")
            say(text="❌ タスクの削除中にエラーが発生しました")


def create_task_list_blocks(
    tasks: list[Dict[str, Any]],
    title: str = "📋 タスク一覧"
) -> list[Dict[str, Any]]:
    """タスクリスト表示用のブロックを作成"""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title
            }
        }
    ]

    if not tasks:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "📝 現在、タスクはありません"
            }
        })
        return blocks

    for task in tasks:
        # ステータスアイコン
        status_icon = {
            "pending": "⏳",
            "completed": "✅",
            "cancelled": "🚫"
        }.get(task["status"], "❓")

        # 作成日時
        created_at = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
        date_str = created_at.strftime("%m/%d %H:%M")

        # タスク表示テキスト
        task_text = f"{status_icon} *{task['task_name']}*\n"
        task_text += f"作成者: <@{task['user_id']}> | 作成日時: {date_str}"

        if task["description"]:
            task_text += f"\n説明: {task['description']}"

        block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": task_text
            }
        }

        # 未完了タスクにアクションボタンを追加
        if task["status"] == "pending":
            block["accessory"] = {
                "type": "overflow",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "✅ 完了"
                        },
                        "value": f"complete_{task['id']}"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "🚫 キャンセル"
                        },
                        "value": f"cancel_{task['id']}"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "🗑️ 削除"
                        },
                        "value": f"delete_{task['id']}"
                    }
                ],
                "action_id": f"task_action_{task['id']}"
            }

        blocks.append(block)

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
                "text": "*タスク管理機能*\n\n• `!task タスク名` - 新しいタスクを作成\n• タスク一覧からタスクの完了・キャンセル・削除が可能"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "➕ タスク作成"
                    },
                    "style": "primary",
                    "action_id": "show_task_create_form"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📝 未完了タスク"
                    },
                    "value": "pending",
                    "action_id": "show_tasks_pending"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ 完了済みタスク"
                    },
                    "value": "completed",
                    "action_id": "show_tasks_completed"
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
                        "text": "📋 全てのタスク"
                    },
                    "value": "all",
                    "action_id": "show_tasks_all"
                }
            ]
        }
    ]


def create_task_create_form_blocks() -> list[Dict[str, Any]]:
    """タスク作成フォーム用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "➕ 新しいタスクを作成"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "作成したいタスクの名前を入力してください"
            }
        },
        {
            "type": "input",
            "element": {
                "type": "plain_text_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "例: 会議の準備、資料作成、レビュー依頼..."
                },
                "action_id": "task_name_input"
            },
            "label": {
                "type": "plain_text",
                "text": "タスク名"
            }
        },
        {
            "type": "input",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "タスクの詳細や備考があれば入力してください（任意）"
                },
                "action_id": "task_description_input"
            },
            "label": {
                "type": "plain_text",
                "text": "説明（任意）"
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
                        "text": "✅ タスクを作成"
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
