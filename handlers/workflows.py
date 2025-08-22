from __future__ import annotations

from datetime import datetime, timezone, timedelta

from boltApp import bolt_app
from db.repository import start_work as repo_start_work, end_work as repo_end_work, get_or_create_user_by_name


def prompt_start_work(say) -> None:
    # kept for potential future expansion (now handled in display.startWork)
    from display.startWork import start_work as show_picker

    show_picker(say)


def prompt_end_work(say) -> None:
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "退勤時刻を入力してください（例: 18:30）。休憩分は分単位で。"}},
        {
            "type": "actions",
            "elements": [
                {"type": "timepicker", "action_id": "end_timepicker", "placeholder": {"type": "plain_text", "text": "Select time"}},
                {"type": "static_select", "action_id": "break_minutes", "placeholder": {"type": "plain_text", "text": "休憩(分)"}, "options": [
                    {"text": {"type": "plain_text", "text": t}, "value": v} for t, v in [("0", "0"), ("15", "15"), ("30", "30"), ("45", "45"), ("60", "60")]
                ]},
                {"type": "button", "text": {"type": "plain_text", "text": "保存"}, "style": "primary", "action_id": "save_end_time"},
            ],
        },
    ]
    say(blocks=blocks, text="退勤時刻の入力")


@bolt_app.action("save_end_time")
def save_end_time(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass

    name = real_name or "unknown"
    user = get_or_create_user_by_name(name)

    values = body.get("state", {}).get("values", {})
    sel_time = None
    break_min = 0
    for _, blocks in values.items():
        if "end_timepicker" in blocks:
            sel_time = blocks["end_timepicker"].get("selected_time")
        if "break_minutes" in blocks:
            opt = blocks["break_minutes"].get("selected_option") or {}
            break_min = int(opt.get("value") or 0)

    # Use today JST date with selected HH:MM -> convert to UTC based on current date
    # Interpret selected time as JST of today
    now_utc = datetime.now(timezone.utc)
    jst = timezone(timedelta(hours=9))
    if sel_time:
        hh, mm = map(int, sel_time.split(":"))
        jst_dt = now_utc.astimezone(jst)
        end_ts = datetime(
            jst_dt.year, jst_dt.month, jst_dt.day, hh, mm, tzinfo=jst
        ).astimezone(timezone.utc)
    else:
        end_ts = now_utc

    updated = repo_end_work(user.id, end_ts, break_min)
    if updated:
        say(f"退勤を保存しました。休憩: {break_min}分")
    else:
        say("本日の開始記録が見つかりませんでした。先に出勤開始を登録してください。")
