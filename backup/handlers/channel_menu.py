"""
チャンネルメニュー機能ハンドラー
"""

import re
from typing import Dict, Any

from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from db.repository import (
    search_channel_memos,
    get_channel_memo_stats,
    get_channel_tasks
)
from handlers.task_management import create_task_list_blocks, create_task_management_blocks


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


def register_channel_menu_handlers(app: App):
    """チャンネルメニュー関連のハンドラーを登録"""

    @app.message(re.compile(r"^(メニュー|めにゅー|menu)$", re.IGNORECASE))
    def handle_channel_menu(message, say, client: WebClient):
        """チャンネルでメニューを表示"""
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


    @app.action("show_memo_search")
    def handle_show_memo_search(ack, body, say, client: WebClient):
        """メモ検索インターフェースを表示"""
        ack()
        try:
            blocks = create_memo_search_input_blocks()
            say(
                text="🔍 メモ検索",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing memo search: {e}")
            say(text="❌ メモ検索の表示中にエラーが発生しました")


    @app.action("show_channel_help")
    def handle_show_help(ack, body, say, client: WebClient):
        """ヘルプページを表示"""
        ack()
        try:
            blocks = create_channel_help_blocks()
            say(
                text="📖 ヘルプ",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing help: {e}")
            say(text="❌ ヘルプの表示中にエラーが発生しました")


    @app.action("execute_memo_search")
    def handle_execute_memo_search(ack, body, say, client: WebClient):
        """メモ検索を実行"""
        ack()
        try:
            # フォームから検索キーワードを取得
            search_input = None
            for action in body.get("state", {}).get("values", {}).values():
                if "search_input" in action:
                    search_input = action["search_input"]["value"]
                    break

            if not search_input or not search_input.strip():
                say(text="❌ 検索キーワードを入力してください")
                return

            keyword = search_input.strip()
            channel_id = body["channel"]["id"]

            # 検索実行
            from db.repository import search_channel_memos
            memos = search_channel_memos(
                keyword=keyword,
                channel_id=channel_id,
                limit=10
            )

            if not memos:
                say(text=f"「{keyword}」に関するメモが見つかりませんでした。")
                return

            # 検索結果を表示
            blocks = create_search_result_blocks(memos, keyword)
            say(
                text=f"🔍 検索結果: {keyword}",
                blocks=blocks
            )

        except Exception as e:
            print(f"Error executing memo search: {e}")
            say(text="❌ 検索の実行中にエラーが発生しました")


    @app.action("show_memo_stats")
    def handle_show_memo_stats(ack, body, say, client: WebClient):
        """メモ統計を表示"""
        ack()
        try:
            channel_id = body["channel"]["id"]

            # 統計情報を取得
            stats = get_channel_memo_stats(channel_id)

            if stats:
                blocks = create_memo_stats_blocks(stats)
                say(
                    text="📊 メモ統計",
                    blocks=blocks
                )
            else:
                say(
                    text="📊 メモ統計",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "📊 *メモ統計*\n\nまだメモがありません"
                            }
                        }
                    ]
                )
        except Exception as e:
            print(f"Error showing memo stats: {e}")
            say(text="❌ メモ統計の表示中にエラーが発生しました")


    @app.action("show_user_ranking")
    def handle_show_user_ranking(ack, body, say, client: WebClient):
        """アクティブユーザーランキングを表示"""
        ack()
        try:
            channel_id = body["channel"]["id"]

            # 統計情報を取得
            stats = get_channel_memo_stats(channel_id)

            if stats and stats.get("top_users"):
                blocks = create_user_ranking_blocks(stats["top_users"])
                say(
                    text="📈 アクティブユーザーランキング",
                    blocks=blocks
                )
            else:
                say(
                    text="📈 アクティブユーザーランキング",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "📈 *アクティブユーザーランキング*\n\nまだメモがありません"
                            }
                        }
                    ]
                )
        except Exception as e:
            print(f"Error showing user ranking: {e}")
            say(text="❌ ユーザーランキングの表示中にエラーが発生しました")


    @app.action("show_task_management")
    def handle_show_task_management(ack, body, say, client: WebClient):
        """タスク管理機能を表示"""
        ack()
        try:
            blocks = create_task_management_blocks()
            say(
                text="📋 タスク管理",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing task management: {e}")
            say(text="❌ タスク管理の表示中にエラーが発生しました")


    @app.action("show_tasks_pending")
    def handle_show_tasks_pending(ack, body, say, client: WebClient):
        """未完了タスク一覧を表示"""
        ack()
        try:
            channel_id = body["channel"]["id"]
            tasks = get_channel_tasks(channel_id, status="pending")

            blocks = create_task_list_blocks(tasks, "📝 未完了タスク一覧")
            say(
                text="📝 未完了タスク一覧",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing pending tasks: {e}")
            say(text="❌ 未完了タスクの表示中にエラーが発生しました")


    @app.action("show_tasks_completed")
    def handle_show_tasks_completed(ack, body, say, client: WebClient):
        """完了済みタスク一覧を表示"""
        ack()
        try:
            channel_id = body["channel"]["id"]
            tasks = get_channel_tasks(channel_id, status="completed")

            blocks = create_task_list_blocks(tasks, "✅ 完了済みタスク一覧")
            say(
                text="✅ 完了済みタスク一覧",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing completed tasks: {e}")
            say(text="❌ 完了済みタスクの表示中にエラーが発生しました")


    @app.action("show_tasks_all")
    def handle_show_tasks_all(ack, body, say, client: WebClient):
        """全てのタスク一覧を表示"""
        ack()
        try:
            channel_id = body["channel"]["id"]
            tasks = get_channel_tasks(channel_id)

            blocks = create_task_list_blocks(tasks, "📋 全タスク一覧")
            say(
                text="📋 全タスク一覧",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing all tasks: {e}")
            say(text="❌ 全タスクの表示中にエラーが発生しました")


    @app.action(re.compile(r"^task_action_(.+)$"))
    def handle_task_action(ack, body, say, client: WebClient):
        """タスクアクション（完了・キャンセル・削除）を処理"""
        ack()
        try:
            # オーバーフローメニューからの選択値を取得
            selected_option = body["actions"][0]["selected_option"]["value"]
            action_type, task_id = selected_option.split("_", 1)

            # アクションタイプに応じて処理を振り分け
            if action_type == "complete":
                from handlers.task_management import handle_task_complete
                # 既存の完了ハンドラーを呼び出し（bodyを調整）
                body["actions"][0]["value"] = task_id
                handle_task_complete(lambda: None, body, say, client)
            elif action_type == "cancel":
                from handlers.task_management import handle_task_cancel
                body["actions"][0]["value"] = task_id
                handle_task_cancel(lambda: None, body, say, client)
            elif action_type == "delete":
                from handlers.task_management import handle_task_delete
                body["actions"][0]["value"] = task_id
                handle_task_delete(lambda: None, body, say, client)

        except Exception as e:
            print(f"Error handling task action: {e}")
            say(text="❌ タスク操作中にエラーが発生しました")


    @app.action("search_input")
    def handle_search_input(ack, body):
        """検索入力フィールドのアクション（何もしない）"""
        ack()  # 入力フィールドの変更を確認するだけ


    @app.action("show_task_create_form")
    def handle_show_task_create_form(ack, body, say, client: WebClient):
        """タスク作成フォームを表示"""
        ack()
        try:
            from handlers.task_management import create_task_create_form_blocks
            blocks = create_task_create_form_blocks()
            say(
                text="➕ タスク作成",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing task create form: {e}")
            say(text="❌ タスク作成フォームの表示中にエラーが発生しました")


    @app.action("task_name_input")
    def handle_task_name_input(ack, body):
        """タスク名入力フィールドのアクション（何もしない）"""
        ack()


    @app.action("task_description_input")
    def handle_task_description_input(ack, body):
        """タスク説明入力フィールドのアクション（何もしない）"""
        ack()


    @app.action("execute_task_create")
    def handle_execute_task_create(ack, body, say, client: WebClient):
        """フォームからタスクを作成"""
        ack()
        try:
            # フォームからタスク名と説明を取得
            task_name = None
            task_description = ""

            for action in body.get("state", {}).get("values", {}).values():
                if "task_name_input" in action:
                    task_name = action["task_name_input"]["value"]
                if "task_description_input" in action:
                    task_description = action["task_description_input"]["value"] or ""

            if not task_name or not task_name.strip():
                say(text="❌ タスク名を入力してください")
                return

            task_name = task_name.strip()
            channel_id = body["channel"]["id"]
            user_id = body["user"]["id"]

            # チャンネル情報を取得
            try:
                channel_info = client.conversations_info(channel=channel_id)
                channel_name = channel_info["channel"]["name"] if channel_info["ok"] else "unknown"
            except Exception:
                channel_name = "unknown"

            # ユーザー情報を取得
            try:
                user_info = client.users_info(user=user_id)
                user_name = user_info["user"]["real_name"] if user_info["ok"] else "unknown"
            except Exception:
                user_name = "unknown"

            # タスクデータを作成
            from db.repository import save_channel_task, utc_now
            task_data = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "user_id": user_id,
                "user_name": user_name,
                "task_name": task_name,
                "description": task_description,
                "status": "pending",
                "created_at": utc_now().isoformat()
            }

            # データベースに保存
            saved_task = save_channel_task(task_data)

            if saved_task:
                say(
                    text="✅ タスクを作成しました",
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
                if task_description:
                    say(text=f"*説明:* {task_description}")
            else:
                say(text="❌ タスクの作成に失敗しました")

        except Exception as e:
            print(f"Error executing task create: {e}")
            say(text="❌ タスクの作成中にエラーが発生しました")


    @app.action("cancel_task_create")
    def handle_cancel_task_create(ack, body, say, client: WebClient):
        """タスク作成をキャンセル"""
        ack()
        try:
            from handlers.task_management import create_task_management_blocks
            blocks = create_task_management_blocks()
            say(
                text="📋 タスク管理",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error canceling task create: {e}")
            say(text="タスク作成をキャンセルしました")


def create_channel_menu_blocks() -> list[Dict[str, Any]]:
    """チャンネルメニュー用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📱 チャンネルメニュー"
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
                        "text": "📊 メモ統計"
                    },
                    "action_id": "show_memo_stats"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "  ユーザーランキング"
                    },
                    "action_id": "show_user_ranking"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": " 📖 ヘルプ"
                    },
                    "action_id": "show_channel_help"
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
                }
            ]
        }
    ]


def create_memo_search_input_blocks() -> list[Dict[str, Any]]:
    """メモ検索入力フォーム用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔍 メモ検索"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "検索したいキーワードを入力してください"
            }
        },
        {
            "type": "input",
            "element": {
                "type": "plain_text_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "検索キーワードを入力..."
                },
                "action_id": "search_input"
            },
            "label": {
                "type": "plain_text",
                "text": "キーワード"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 検索実行"
                    },
                    "style": "primary",
                    "action_id": "execute_memo_search"
                }
            ]
        }
    ]


def create_channel_help_blocks() -> list[Dict[str, Any]]:
    """チャンネル専用ヘルプページ用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📖 利用可能な機能"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🔍 メモ検索機能*\n• メニューから「メモ検索」を選択してキーワード検索\n• `!search キーワード` - コマンドでキーワード検索\n• `!recent` - 最新のメモを表示\n• `!recent 7` - 過去7日間のメモを表示"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📊 メモ統計機能*\n• メニューから「メモ統計」を選択\n• チャンネルの総メモ数、今日・今週のメモ数を表示\n• アクティブユーザーランキングを表示"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📋 タスク管理機能*\n• `!task タスク名` - 新しいタスクを作成\n• メニューから「タスク管理」を選択\n• 未完了・完了済み・全タスクの一覧表示\n• タスクの作成・完了・キャンセル・削除が可能"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*💬 自動メモ機能*\n• チャンネルでの会話が自動的にメモとして記録\n• コマンドメッセージは記録されません\n• 検索で過去の会話を簡単に見つけられます"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*基本コマンド*\n• `メニュー` / `menu` - メニューを表示\n• `!task タスク名` - タスク作成\n• `!search キーワード` - メモ検索\n• `!recent` - 最新メモ表示"
            }
        }
    ]


def create_search_result_blocks(memos: list[Dict[str, Any]], keyword: str) -> list[Dict[str, Any]]:
    """検索結果表示用のブロックを作成"""
    from datetime import datetime, timezone

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔍 検索結果: {keyword}"
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
                    "text": "元メッセージ"
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

    return blocks


def create_user_ranking_blocks(top_users: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """アクティブユーザーランキング表示用のブロックを作成"""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📈 アクティブユーザーランキング"
            }
        }
    ]

    if not top_users:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "まだメモがありません"
            }
        })
        return blocks

    # ランキング表示（上位10名）
    ranking_text = ""
    medals = ["🥇", "🥈", "🥉"]

    for i, user in enumerate(top_users[:10], 1):
        user_name = user["user_name"]
        memo_count = user["memo_count"]

        if i <= 3:
            medal = medals[i-1]
            ranking_text += f"{medal} **{i}位** {user_name} - {memo_count}件\n"
        else:
            ranking_text += f"🏅 **{i}位** {user_name} - {memo_count}件\n"

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ranking_text
        }
    })

    # 統計情報
    total_users = len(top_users)
    if total_users > 10:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"💡 上位10名を表示中（総投稿者数: {total_users}人）"
                }
            ]
        })

    return blocks


def create_memo_stats_blocks(stats: Dict[str, Any]) -> list[Dict[str, Any]]:
    """メモ統計表示用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 メモ統計"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*総メモ数*\n{stats['total_memos']}件"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*今日のメモ*\n{stats['today_memos']}件"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*今週のメモ*\n{stats['week_memos']}件"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*投稿者数*\n{stats['unique_users']}人"
                }
            ]
        }
    ]
