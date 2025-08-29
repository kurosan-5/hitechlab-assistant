from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict

from boltApp import bolt_app
from db.repository import upsert_attendance, get_users, get_attendance_between_tue_fri


def prompt_attendance(say, values=None, error_message=None) -> None:
    # 現在の日付を初期値として設定
    now = datetime.now()
    initial_date = now.strftime("%Y-%m-%d")

    # 以前の値を保持
    if values:
        for _, blocks in values.items():
            for action_id, payload in blocks.items():
                if action_id == "attendance_datepicker" and payload.get("selected_date"):
                    initial_date = payload.get("selected_date")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "出勤予定を選択", "emoji": True},
        }
    ]

    # エラーメッセージがある場合は表示
    if error_message:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"❌ {error_message}"}
        })

    blocks.extend([
        {
            "type": "actions",
            "elements": [
                {
                    "type": "datepicker",
                    "initial_date": initial_date,
                    "placeholder": {"type": "plain_text", "text": "日付を選択", "emoji": True},
                    "action_id": "attendance_datepicker",
                },
            ],
        },
        {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "出勤"}, "style": "primary", "action_id": "attend_yes"},
                {"type": "button", "text": {"type": "plain_text", "text": "休み"}, "style": "danger", "action_id": "attend_no"},
                {"type": "button", "text": {"type": "plain_text", "text": "キャンセル"}, "action_id": "attend_cancel"},
            ],
        },
    ])
    say(blocks=blocks, text="出勤予定の選択")


@bolt_app.action("attend_yes")
def attend_yes(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    _save_attendance(True, body, say, client)


@bolt_app.action("attend_no")
def attend_no(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    _save_attendance(False, body, say, client)

@bolt_app.action("attend_cancel")
def attend_cancel(ack, body, say):
    ack()
    say("出勤予定をキャンセルしました。")
    from display.menu import display_menu
    display_menu(say, body=body)

def _save_attendance(is_attend: bool, body, say, client) -> None:
    user_slack_id = body.get("user", {}).get("id")
    display_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            display_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass

    from db.repository import get_or_create_user

    user = get_or_create_user(user_slack_id or "unknown", display_name)

    # 選択された日付を取得
    values = body.get("state", {}).get("values", {})
    selected_date = None

    for _, blocks in values.items():
        for action_id, payload in blocks.items():
            if action_id == "attendance_datepicker":
                selected_date = payload.get("selected_date")
                break

    # 日付が選択されていない場合はエラー
    if not selected_date:
        prompt_attendance(say, values, "日付を選択してください。")
        return

    # 選択された日付をdatetimeに変換
    try:
        y, m, d = map(int, selected_date.split("-"))
        jst = timezone(timedelta(hours=9))
        selected_dt = datetime(y, m, d, 12, 0, tzinfo=jst).astimezone(timezone.utc)
    except Exception:
        prompt_attendance(say, values, "正しい日付を選択してください。")
        return
        return

    upsert_attendance(user.id, selected_dt, is_attend)
    status_text = "出勤予定" if is_attend else "休み予定"
    say(f"{selected_date} の{status_text}を保存しました。")

    # メニューに戻る
    from display.menu import display_menu
    display_menu(say, body=body, client=client)


def show_attendance_overview(say, client=None) -> None:
    try:
        now = datetime.now(timezone.utc)
        users = get_users()
        user_map: Dict[str, str] = {u.id: u.name for u in users}
        rows = get_attendance_between_tue_fri(now)

        # 2か月分の火曜日と金曜日の日付を生成
        from collections import defaultdict

        by_date: Dict[str, Dict[str, str]] = defaultdict(dict)  # date -> user_id -> status

        # 2か月分（約60日）の火曜日と金曜日を生成
        jst_tz = timezone(timedelta(hours=9))
        cur = now.astimezone(jst_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        # 過去1週間と未来2か月分をカバー
        start_date = cur - timedelta(days=7)
        end_date = cur + timedelta(days=60)

        current = start_date
        while current <= end_date:
            if current.weekday() in (1, 4):  # 火曜日=1, 金曜日=4
                key = f"{current.year:04d}-{current.month:02d}-{current.day:02d}"
                by_date[key] = {}
            current += timedelta(days=1)

        # 取得したデータをマッピング
        for r in rows:
            key = f"{r['_year']:04d}-{r['_month']:02d}-{r['_day']:02d}"
            if key in by_date:  # 対象日付の場合のみ
                by_date[key][r["user_id"]] = "出勤" if r["is_attend"] else "休み"

        # メインメッセージを投稿
        main_blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "📅 出勤状況はこちらのスレッドをご確認ください"}
            }
        ]

        # メインメッセージを投稿してタイムスタンプを取得
        response = say(blocks=main_blocks, text="出勤状況")

        # スレッドで詳細を表示
        if response and hasattr(response, 'get') and response.get('ts'):
            thread_ts = response['ts']

            # ブロックを構築
            blocks = [{"type": "header", "text": {"type": "plain_text", "text": "出勤確認（火/金）"}}]

            for day in sorted(by_date.keys()):
                status_map = by_date[day]

                # 日付のみの行を追加
                lines = [f"*{day}*"]

                # ユーザーの報告がある場合のみ表示
                if status_map:
                    for user_id, status in status_map.items():
                        user_name = user_map.get(user_id, f"Unknown({user_id})")
                        lines.append(f"{user_name}: {status}")

                # 改行で結合して表示
                text_content = "\n".join(lines)
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text_content}})

            # スレッドに詳細を投稿
            say(blocks=blocks, text="出勤確認詳細", thread_ts=thread_ts)
        else:
            # フォールバック: スレッド投稿に失敗した場合は通常の投稿
            blocks = [{"type": "header", "text": {"type": "plain_text", "text": "出勤確認（火/金）"}}]

            for day in sorted(by_date.keys()):
                status_map = by_date[day]

                # 日付のみの行を追加
                lines = [f"*{day}*"]

                # ユーザーの報告がある場合のみ表示
                if status_map:
                    for user_id, status in status_map.items():
                        user_name = user_map.get(user_id, f"Unknown({user_id})")
                        lines.append(f"{user_name}: {status}")

                # 改行で結合して表示
                text_content = "\n".join(lines)
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text_content}})

            say(blocks=blocks, text="出勤確認")

    except Exception as e:
        # データベース接続エラーやその他のエラーをキャッチ
        error_blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "❌ 出勤状況の取得中にエラーが発生しました。\nしばらく時間をおいてから再度お試しください。"}
            }
        ]
        say(blocks=error_blocks, text="エラー")

        # ログにエラーを出力（デバッグ用）
        import logging
        logging.error(f"Error in show_attendance_overview: {e}", exc_info=True)


# 不足しているアクションハンドラーを追加
@bolt_app.action("attendance_datepicker")
def handle_attendance_datepicker(ack):
    """出勤予定日付ピッカーのハンドラー（何もしない）"""
    ack()
