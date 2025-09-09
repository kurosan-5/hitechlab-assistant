from __future__ import annotations

from datetime import datetime, timezone, timedelta

from boltApp import bolt_app
from db.repository import start_work as repo_start_work, end_work as repo_end_work, get_active_work_start_time

def prompt_start_work(say) -> None:
    # kept for potential future expansion (now handled in handlers.startWork)
    from handlers.startWork import start_work as show_picker

    show_picker(say)


def prompt_end_work(say, values=None, error_message=None, user_id=None) -> None:
    # 現在のローカル時刻から日付と時間の文字列を生成
    now = datetime.now()
    initial_date = now.strftime("%Y-%m-%d")
    initial_time = now.strftime("%H:%M")
    initial_break_time = "00:00"
    initial_comment = ""

    # 以前の値を保持
    if values:
        for _, blocks in values.items():
            for action_id, payload in blocks.items():
                if action_id == "end_datepicker" and payload.get("selected_date"):
                    initial_date = payload.get("selected_date")
                elif action_id == "end_timepicker" and payload.get("selected_time"):
                    initial_time = payload.get("selected_time")
                elif action_id == "break_time_picker" and payload.get("selected_time"):
                    initial_break_time = payload.get("selected_time")
                elif action_id == "end_comment_input":
                    # 空文字列でも保持する（バリデーションエラー時のため）
                    comment_value = payload.get("value")
                    initial_comment = comment_value if comment_value is not None else ""

    # 開始時刻を取得して表示用に整形
    header_text = "終了日時を選択"
    if user_id:
        try:
            # 今日の日付で開始時刻を検索
            end_ts_temp = datetime.now(timezone.utc)
            start_ts = get_active_work_start_time(user_id, end_ts_temp)
            if start_ts:
                start_jst = start_ts.astimezone(timezone(timedelta(hours=9)))
                header_text = f"終了日時を選択 ({start_jst.month}/{start_jst.day} {start_jst.hour}:{start_jst.minute}開始)"
        except Exception:
            pass

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": True},
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
                    "placeholder": {"type": "plain_text", "text": "Select a date", "emoji": True},
                    "action_id": "end_datepicker",
                },
                {
                    "type": "timepicker",
                    "initial_time": initial_time,
                    "placeholder": {"type": "plain_text", "text": "Select time", "emoji": True},
                    "action_id": "end_timepicker",
                },
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*休憩時間を選択（HH:MM形式）*"},
            "accessory": {
                "type": "timepicker",
                "initial_time": initial_break_time,
                "action_id": "break_time_picker",
                "placeholder": {"type": "plain_text", "text": "休憩時間", "emoji": True},
            }
        },
        {
            "type": "input",
            "element": {
                "type": "plain_text_input",
                "action_id": "end_comment_input",
                "placeholder": {"type": "plain_text", "text": "業務内容を入力してください（必須）"},
                "multiline": True,
                "initial_value": initial_comment or "",
            },
            "label": {"type": "plain_text", "text": "コメント"},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "決定", "emoji": True},
                    "style": "primary",
                    "action_id": "save_end_time",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "キャンセル", "emoji": True},
                    "action_id": "cancel_end_time",
                },
            ],
        },
    ])
    say(blocks=blocks, text="終了日時を選択してください。")


@bolt_app.action("save_end_time")
def save_end_time(ack, body, say, client):  # type: ignore[no-redef]
    ack()
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

    # ユーザーが選択した終了日時、休憩時間、コメントを取得
    values = body.get("state", {}).get("values", {})
    selected_date = None
    selected_time = None
    break_min = 0
    comment = None

    for _, blocks in values.items():
        for action_id, payload in blocks.items():
            if action_id == "end_datepicker":
                selected_date = payload.get("selected_date")
            elif action_id == "end_timepicker":
                selected_time = payload.get("selected_time")
            elif action_id == "break_time_picker":
                break_time_str = payload.get("selected_time")
                if break_time_str:
                    # "HH:MM" 形式から分に変換
                    hours, minutes = map(int, break_time_str.split(":"))
                    break_min = hours * 60 + minutes
            elif action_id == "end_comment_input":
                comment_value = payload.get("value")
                comment = (comment_value or "").strip()

    # コメントのバリデーション
    if not comment:
        prompt_end_work(say, values, "コメントは必須です。業務内容を入力してください。", user.id)
        return

    if selected_date and selected_time:
        # 入力はJSTとして解釈し、UTCへ変換
        hh, mm = map(int, selected_time.split(":"))
        y, m, d = map(int, selected_date.split("-"))
        jst = timezone(timedelta(hours=9))
        end_ts = datetime(y, m, d, hh, mm, tzinfo=jst).astimezone(timezone.utc)
    else:
        # 日付または時刻が選択されていない場合は現在時刻を使用
        end_ts = datetime.now(timezone.utc)

    # 開始時刻との比較バリデーション
    start_ts = get_active_work_start_time(user.id, end_ts)
    if start_ts and end_ts <= start_ts:
        prompt_end_work(say, values, "終了時刻は開始時刻よりも後の時刻を設定してください。", user.id)
        return

    updated = repo_end_work(user.id, end_ts, break_min, comment)
    if updated:
        date_time_str = f"{selected_date} {selected_time}" if selected_date and selected_time else "現在時刻"

        # 勤務時間を計算（開始時刻から終了時刻までの時間 - 休憩時間）
        if start_ts:
            # 総勤務時間（分）
            total_work_minutes = (end_ts - start_ts).total_seconds() / 60
            # 実勤務時間（分） = 総勤務時間 - 休憩時間
            actual_work_minutes = total_work_minutes - break_min
            if actual_work_minutes < 0 :
                prompt_end_work(say, values, "勤務時間よりも長く休憩時間を設定することはできません", user.id)
                return
            # 時間単位に変換（小数点以下1桁まで表示）
            work_hours = actual_work_minutes / 60
            work_hours_str = f"{work_hours:.1f}時間"
        else:
            work_hours_str = "計算不可"

        # 休憩時間を時:分形式で表示
        break_hours = break_min // 60
        break_minutes = break_min % 60
        break_str = f"{break_hours}時間{break_minutes}分" if break_hours > 0 else f"{break_minutes}分"

        say(f"退勤を保存しました: {date_time_str}\n休憩: {break_str}\n勤務時間: {work_hours_str}")
        # メニューに戻って出勤ボタンの表示を更新
        from display.menu import display_menu
        display_menu(say, body=body, client=client)
    else:
        say("対象日の開始記録が見つかりませんでした。先に出勤開始を登録してください。")


@bolt_app.action("cancel_end_time")
def cancel_end_time(ack, body, say, client=None):  # type: ignore[no-redef]
    ack()
    say("退勤入力をキャンセルしました。メニューに戻ります。")
    from display.menu import display_menu
    display_menu(say, body=body, client=client)


# 不足しているアクションハンドラーを追加
@bolt_app.action("end_datepicker")
def handle_end_datepicker(ack):
    """終了日付ピッカーのハンドラー（何もしない）"""
    ack()


@bolt_app.action("end_timepicker")
def handle_end_timepicker(ack):
    """終了時刻ピッカーのハンドラー（何もしない）"""
    ack()


@bolt_app.action("break_time_picker")
def handle_break_time_picker(ack):
    """休憩時間ピッカーのハンドラー（何もしない）"""
    ack()


@bolt_app.action("end_comment_input")
def handle_end_comment_input(ack):
    """コメント入力のハンドラー（何もしない）"""
    ack()
