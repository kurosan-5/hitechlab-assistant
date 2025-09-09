"""
チャンネル機能ハンドラー登録
"""

import re
from typing import Dict, Any

from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from db.repository import (
    search_channel_memos,
    get_channel_memo_stats,
    get_channel_tasks,
    get_recent_channel_memos,
    save_channel_task,
    update_task_status,
    delete_task,
    get_all_channel_memos,
    get_channel_memo_by_id,
    update_channel_memo,
    delete_channel_memo,
    save_channel_memo
)

from .menu import (
    create_channel_menu_blocks,
    create_channel_help_blocks,
    create_memo_management_blocks
)

from .memo import (
    create_memo_search_input_blocks,
    create_search_result_blocks,
    create_memo_stats_blocks,
    create_recent_memos_blocks,
    create_memo_list_blocks,
    create_memo_edit_modal_blocks,
    create_memo_create_form_blocks
)

from .tasks import (
    create_task_create_form_blocks,
    create_task_list_blocks,
    create_task_management_blocks
)


def handle_channel_message(event, body, say, client, logger):
    """チャンネルメッセージの統一処理"""
    text = event.get("text", "").strip()

    # メニュー表示
    if re.match(r"^(メニュー|めにゅー|menu)$", text, re.IGNORECASE):
        try:
            blocks = create_channel_menu_blocks()
            say(
                text="📱 チャンネルメニュー",
                blocks=blocks
            )
        except Exception as e:
            logger.error(f"Error showing channel menu: {e}")
            say(text="❌ メニューの表示中にエラーが発生しました")

    # メモ作成（!memo, !m, !メモ コマンド）
    elif re.match(r"^(!memo|!m|!メモ)\s+(.+)", text, re.IGNORECASE):
        try:
            # メモ内容を抽出
            memo_match = re.match(r"^(!memo|!m|!メモ)\s+(.+)", text, re.IGNORECASE)
            if memo_match:
                memo_content = memo_match.group(2).strip()
                channel_id = event.get("channel")
                user_id = event.get("user")
                message_ts = event.get("ts")

                # ユーザー情報を取得
                try:
                    user_info = client.users_info(user=user_id)
                    user_name = user_info.get("user", {}).get("real_name") or user_info.get("user", {}).get("display_name") or "Unknown User"
                except Exception as e:
                    logger.warning(f"Failed to get user info for {user_id}: {e}")
                    user_name = "Unknown User"

                # チャンネル情報を取得
                try:
                    channel_info = client.conversations_info(channel=channel_id)
                    channel_name = channel_info.get("channel", {}).get("name", "unknown")
                except Exception as e:
                    logger.warning(f"Failed to get channel info for {channel_id}: {e}")
                    channel_name = "unknown"

                # メモデータを作成
                from datetime import datetime, timezone
                memo_data = {
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "user_id": user_id,
                    "user_name": user_name,
                    "message": memo_content,
                    "message_ts": message_ts,
                    "thread_ts": None,
                    "permalink": None,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }

                # メモを保存
                saved_memo = save_channel_memo(memo_data)

                print(f"DEBUG: Command memo save attempt - Data: {memo_data}")
                print(f"DEBUG: Command memo save result: {saved_memo}")

                if saved_memo:
                    say(text=f"📝 メモを作成しました:\n> {memo_content}")
                else:
                    say(text="❌ メモの作成に失敗しました")
        except Exception as e:
            logger.error(f"Error creating memo: {e}")
            say(text="❌ メモの作成中にエラーが発生しました")

    # タスク作成（!task コマンド）
    elif re.match(r"^!task\s+(.+)", text, re.IGNORECASE):
        try:
            # タスク名を抽出
            task_match = re.match(r"^!task\s+(.+)", text, re.IGNORECASE)
            if task_match:
                task_name = task_match.group(1).strip()
                channel_id = event.get("channel")
                user_id = event.get("user")

                # タスクデータを作成
                task_data = {
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "task_name": task_name,
                    "status": "pending"
                }

                # タスクを保存
                saved_task = save_channel_task(task_data)

                if saved_task:
                    say(text=f"✅ タスク「{task_name}」を作成しました")
                else:
                    say(text="❌ タスクの作成に失敗しました")
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            say(text="❌ タスクの作成中にエラーが発生しました")

    # メモ一覧表示（!memo コマンド）
    elif re.match(r"^!memo\s*$", text, re.IGNORECASE):
        try:
            channel_id = event.get("channel")
            memos = get_all_channel_memos(channel_id, limit=50)

            blocks = create_memo_list_blocks(memos)

            # スレッドに返信する形で表示
            thread_ts = event.get("ts")  # 元メッセージのタイムスタンプ
            say(
                text="📝 メモ一覧",
                blocks=blocks,
                thread_ts=thread_ts
            )
        except Exception as e:
            logger.error(f"Error showing memo list: {e}")
            say(text="❌ メモ一覧の表示中にエラーが発生しました")

def register_channel_handlers(app: App):
    """チャンネル機能のハンドラーを登録"""

    # 統一メッセージハンドラーを使用するため、メッセージハンドラーは登録しない
    # 代わりにアクションハンドラーのみ登録

    # メニューボタンアクション
    @app.action("show_channel_menu")
    def handle_show_channel_menu(ack, body, say, client: WebClient):
        """メニューを表示"""
        ack()
        try:
            blocks = create_channel_menu_blocks()
            say(
                text="📱 チャンネルメニュー",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing menu: {e}")
            say(text="❌ メニューの表示中にエラーが発生しました")

    @app.action("show_memo_management")
    def handle_show_memo_management(ack, body, say, client: WebClient):
        """メモ管理を表示"""
        ack()
        try:
            blocks = create_memo_management_blocks()
            say(
                text="📝 メモ管理",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing memo management: {e}")
            say(text="❌ メモ管理の表示中にエラーが発生しました")

    # ヘルプ表示
    @app.action("show_channel_help")
    def handle_show_channel_help(ack, body, say, client: WebClient):
        """ヘルプを表示"""
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

    # メモ作成フォーム表示
    @app.action("show_memo_create")
    def handle_show_memo_create(ack, body, say, client: WebClient):
        """メモ作成フォームを表示"""
        ack()
        try:
            blocks = create_memo_create_form_blocks()
            say(
                text="📝 メモ作成",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing memo create form: {e}")
            say(text="❌ メモ作成フォームの表示中にエラーが発生しました")

    # メモ検索フォーム表示
    @app.action("show_memo_search")
    def handle_show_memo_search(ack, body, say, client: WebClient):
        """メモ検索フォームを表示"""
        ack()
        try:
            blocks = create_memo_search_input_blocks()
            say(
                text="🔍 メモ検索",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing memo search: {e}")
            say(text="❌ 検索フォームの表示中にエラーが発生しました")

    # メモ検索実行
    @app.action("execute_memo_search")
    def handle_execute_memo_search(ack, body, say, client: WebClient):
        """メモ検索を実行"""
        ack()
        try:
            # フォームから検索キーワードを取得
            search_input = None
            values = body.get("state", {}).get("values", {})

            # search_input_blockからsearch_inputを探す
            for block_id, actions in values.items():
                if "search_input" in actions:
                    search_input = actions["search_input"]["value"]
                    break

            if not search_input or not search_input.strip():
                say(text="❌ 検索キーワードを入力してください")
                return

            keyword = search_input.strip()
            channel_id = body["channel"]["id"]

            # 検索実行
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

    # メモ作成実行
    @app.action("execute_memo_create")
    def handle_execute_memo_create(ack, body, say, client: WebClient):
        """メモ作成を実行"""
        ack()
        try:
            # フォームからメモ内容を取得
            memo_content = None
            values = body.get("state", {}).get("values", {})

            # memo_content_blockからmemo_content_inputを探す
            for block_id, actions in values.items():
                if "memo_content_input" in actions:
                    memo_content = actions["memo_content_input"]["value"]
                    break

            if not memo_content or not memo_content.strip():
                say(text="❌ メモ内容を入力してください")
                return

            channel_id = body["channel"]["id"]
            user_id = body["user"]["id"]

            # ユーザー情報を取得
            try:
                user_info = client.users_info(user=user_id)
                user_name = user_info.get("user", {}).get("real_name") or user_info.get("user", {}).get("display_name") or "Unknown User"
            except Exception as e:
                print(f"Failed to get user info for {user_id}: {e}")
                user_name = "Unknown User"

            # チャンネル情報を取得
            try:
                channel_info = client.conversations_info(channel=channel_id)
                channel_name = channel_info.get("channel", {}).get("name", "unknown")
            except Exception as e:
                print(f"Failed to get channel info for {channel_id}: {e}")
                channel_name = "unknown"

            # メモデータを作成
            from datetime import datetime, timezone
            import time

            # フォームから作成する場合は現在時刻をタイムスタンプとして使用
            current_ts = str(time.time())

            memo_data = {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "user_id": user_id,
                "user_name": user_name,
                "message": memo_content.strip(),
                "message_ts": current_ts,  # 現在時刻をタイムスタンプとして使用
                "thread_ts": None,
                "permalink": None
            }

            # メモを保存
            saved_memo = save_channel_memo(memo_data)

            if saved_memo:
                say(text=f"✅ メモを作成しました:\n> {memo_content.strip()}")
            else:
                say(text="❌ メモの作成に失敗しました")

        except Exception as e:
            print(f"Error executing memo create: {e}")
            say(text="❌ メモの作成中にエラーが発生しました")

    # メモ一覧表示
    @app.action("show_memo_list")
    def handle_show_memo_list(ack, body, say, client: WebClient):
        """メモ一覧を表示"""
        ack()
        try:
            channel_id = body["channel"]["id"]
            memos = get_all_channel_memos(channel_id, limit=50)

            blocks = create_memo_list_blocks(memos)
            say(
                text="📝 メモ一覧",
                blocks=blocks
            )

        except Exception as e:
            print(f"Error showing memo list: {e}")
            say(text="❌ メモ一覧の表示中にエラーが発生しました")

    # メモ統計表示
    @app.action("show_memo_stats")
    def handle_show_memo_stats(ack, body, say, client: WebClient):
        """メモ統計を表示（ユーザーランキング含む）"""
        ack()
        try:
            channel_id = body["channel"]["id"]

            # 統計情報を取得（ユーザーランキング含む）
            stats = get_channel_memo_stats(channel_id)

            if stats:
                blocks = create_memo_stats_blocks(stats)
                say(
                    text="📊 メモ統計",
                    blocks=blocks
                )
            else:
                say(text="📊 統計データがありません")

        except Exception as e:
            print(f"Error showing memo stats: {e}")
            say(text="❌ 統計の表示中にエラーが発生しました")

    # タスク管理メニュー表示
    @app.action("show_task_management")
    def handle_show_task_management(ack, body, say, client: WebClient):
        """タスク管理メニューを表示"""
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

    # タスク一覧表示（全て）
    @app.action("show_task_list")
    def handle_show_task_list(ack, body, say, client: WebClient):
        """タスク一覧を表示（全て）"""
        ack()
        try:
            channel_id = body["channel"]["id"]
            tasks = get_channel_tasks(channel_id)

            blocks = create_task_list_blocks(tasks, "all")
            say(
                text="📋 全てのタスク",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing task list: {e}")
            say(text="❌ タスク一覧の表示中にエラーが発生しました")

    # タスク一覧表示（全て）
    @app.action("show_task_list_all")
    def handle_show_task_list_all(ack, body, say, client: WebClient):
        """タスク一覧を表示（全て）"""
        ack()
        try:
            channel_id = body["channel"]["id"]
            tasks = get_channel_tasks(channel_id)

            blocks = create_task_list_blocks(tasks, "all")
            say(
                text="📋 全てのタスク",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing task list: {e}")
            say(text="❌ タスク一覧の表示中にエラーが発生しました")

    # タスク一覧表示（未完了）
    @app.action("show_task_list_pending")
    def handle_show_task_list_pending(ack, body, say, client: WebClient):
        """タスク一覧を表示（未完了）"""
        ack()
        try:
            channel_id = body["channel"]["id"]
            tasks = get_channel_tasks(channel_id)

            blocks = create_task_list_blocks(tasks, "pending")
            say(
                text="📋 未完了タスク",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing pending task list: {e}")
            say(text="❌ 未完了タスク一覧の表示中にエラーが発生しました")

    # タスク一覧表示（完了済み）
    @app.action("show_task_list_completed")
    def handle_show_task_list_completed(ack, body, say, client: WebClient):
        """タスク一覧を表示（完了済み）"""
        ack()
        try:
            channel_id = body["channel"]["id"]
            tasks = get_channel_tasks(channel_id)

            blocks = create_task_list_blocks(tasks, "completed")
            say(
                text="📋 完了済みタスク",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing completed task list: {e}")
            say(text="❌ 完了済みタスク一覧の表示中にエラーが発生しました")

    # タスク作成フォーム表示
    @app.action("show_task_create_form")
    def handle_show_task_create_form(ack, body, say, client: WebClient):
        """タスク作成フォームを表示"""
        ack()
        try:
            blocks = create_task_create_form_blocks()
            say(
                text="➕ タスク作成",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error showing task create form: {e}")
            say(text="❌ タスク作成フォームの表示中にエラーが発生しました")

    # タスク作成実行
    @app.action("execute_task_create")
    def handle_execute_task_create(ack, body, say, client: WebClient):
        """タスク作成を実行"""
        ack()
        try:
            # フォームからタスク情報を取得
            task_name = None
            task_description = ""

            values = body.get("state", {}).get("values", {})

            # タスク名を取得
            for block_id, actions in values.items():
                if "task_name_input" in actions:
                    task_name = actions["task_name_input"]["value"]
                elif "task_description_input" in actions:
                    task_description = actions["task_description_input"]["value"] or ""

            if not task_name or not task_name.strip():
                say(text="❌ タスク名を入力してください")
                return

            # タスクを作成
            channel_id = body["channel"]["id"]
            user_id = body["user"]["id"]

            # タスクデータを構築
            from datetime import datetime, timezone
            task_data = {
                "channel_id": channel_id,
                "task_name": task_name.strip(),
                "description": task_description.strip(),
                "user_id": user_id,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            task_result = save_channel_task(task_data)

            if task_result:
                say(text=f"✅ タスク「{task_name.strip()}」を作成しました")
            else:
                say(text="❌ タスクの作成に失敗しました")

        except Exception as e:
            print(f"Error creating task: {e}")
            say(text="❌ タスクの作成中にエラーが発生しました")

    # タスク作成キャンセル
    @app.action("cancel_task_create")
    def handle_cancel_task_create(ack, body, say, client: WebClient):
        """タスク作成をキャンセル"""
        ack()
        try:
            blocks = create_task_management_blocks()
            say(
                text="📋 タスク管理",
                blocks=blocks
            )
        except Exception as e:
            print(f"Error canceling task create: {e}")
            say(text="❌ エラーが発生しました")

    # タスクアクション（完了/削除）
    @app.action("task_action")
    def handle_task_action(ack, body, say, client: WebClient):
        """タスクアクション（完了/削除）を処理"""
        ack()
        try:
            selected_option = body["actions"][0]["selected_option"]["value"]
            channel_id = body["channel"]["id"]

            if selected_option.startswith("toggle_task_status_"):
                task_id = selected_option.replace("toggle_task_status_", "")

                # 現在のタスク状態を取得して切り替え
                tasks = get_channel_tasks(channel_id)
                current_task = next((t for t in tasks if t['id'] == task_id), None)

                if current_task:
                    new_status = 'completed' if current_task['status'] != 'completed' else 'pending'
                    success = update_task_status(task_id, new_status)

                    if success:
                        status_text = "完了" if new_status == 'completed' else "未完了"
                        say(text=f"✅ タスクを{status_text}に変更しました")
                    else:
                        say(text="❌ タスクの更新に失敗しました")

            elif selected_option.startswith("delete_task_"):
                task_id = selected_option.replace("delete_task_", "")
                success = delete_task(task_id)

                if success:
                    say(text="🗑️ タスクを削除しました")
                else:
                    say(text="❌ タスクの削除に失敗しました")

        except Exception as e:
            print(f"Error handling task action: {e}")
            say(text="❌ タスクアクションの処理中にエラーが発生しました")

    # メモアクション（編集・削除）
    @app.action(re.compile(r"memo_actions_.+"))
    def handle_memo_action(ack, body, say, client: WebClient):
        """メモの編集・削除アクション"""
        ack()
        try:
            action = body["actions"][0]

            # URLオプション（元メッセージボタン）の場合は何もしない
            # URLオプションは自動的にブラウザで開かれるため処理不要
            if "url" in action.get("selected_option", {}):
                return

            # overflow menuの場合
            if "selected_option" in action:
                selected_option = action["selected_option"]["value"]

                if selected_option.startswith("edit_memo_"):
                    memo_id = selected_option.replace("edit_memo_", "")
                    memo = get_channel_memo_by_id(memo_id)

                    if memo:
                        # 編集モーダルを表示
                        modal_blocks = create_memo_edit_modal_blocks(memo)
                        client.views_open(
                            trigger_id=body["trigger_id"],
                            view={
                                "type": "modal",
                                "callback_id": f"edit_memo_modal_{memo_id}",
                                "title": {
                                    "type": "plain_text",
                                    "text": "メモを編集"
                                },
                                "submit": {
                                    "type": "plain_text",
                                    "text": "更新"
                                },
                                "close": {
                                    "type": "plain_text",
                                    "text": "キャンセル"
                                },
                                "blocks": modal_blocks
                            }
                        )
                    else:
                        say(text="❌ メモが見つかりませんでした")

                elif selected_option.startswith("delete_memo_"):
                    memo_id = selected_option.replace("delete_memo_", "")
                    success = delete_channel_memo(memo_id)

                    if success:
                        say(text="🗑️ メモを削除しました")
                    else:
                        say(text="❌ メモの削除に失敗しました")

        except Exception as e:
            print(f"Error handling memo action: {e}")
            say(text="❌ メモアクションの処理中にエラーが発生しました")

    # メモ編集モーダルの送信
    @app.view(re.compile(r"edit_memo_modal_.+"))
    def handle_memo_edit_submission(ack, body, say, client: WebClient):
        """メモ編集モーダルの送信処理"""
        ack()
        try:
            # モーダルIDからメモIDを取得
            callback_id = body["view"]["callback_id"]
            memo_id = callback_id.replace("edit_memo_modal_", "")

            # 新しいメモ内容を取得
            new_message = body["view"]["state"]["values"]["memo_text_block"]["memo_text_input"]["value"]

            if not new_message or not new_message.strip():
                say(text="❌ メモ内容を入力してください")
                return

            # メモを更新
            success = update_channel_memo(memo_id, new_message.strip())

            if success:
                say(text="✅ メモを更新しました")
            else:
                say(text="❌ メモの更新に失敗しました")

        except Exception as e:
            print(f"Error handling memo edit submission: {e}")
            say(text="❌ メモの更新中にエラーが発生しました")

    # 入力フィールドのハンドラー（必要に応じて）
    @app.action("search_input")
    def handle_search_input(ack):
        """検索入力フィールドのハンドラー"""
        ack()

    @app.action("memo_content_input")
    def handle_memo_content_input(ack):
        """メモ内容入力フィールドのハンドラー"""
        ack()

    @app.action("memo_text_input")
    def handle_memo_text_input(ack):
        """メモテキスト入力フィールドのハンドラー"""
        ack()

    @app.action("task_name_input")
    def handle_task_name_input(ack):
        """タスク名入力フィールドのハンドラー"""
        ack()

    @app.action("task_description_input")
    def handle_task_description_input(ack):
        """タスク説明入力フィールドのハンドラー"""
        ack()
