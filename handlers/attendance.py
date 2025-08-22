from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from boltApp import bolt_app
from db.repository import upsert_attendance, get_users, get_attendance_between_tue_fri


def prompt_attendance(say) -> None:
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "今日の出勤予定を選択してください"}},
        {
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "出勤"}, "style": "primary", "action_id": "attend_yes"},
                {"type": "button", "text": {"type": "plain_text", "text": "休み"}, "style": "danger", "action_id": "attend_no"},
            ],
        },
    ]
    say(blocks=blocks, text="出勤予定の選択")


@bolt_app.action("attend_yes")
def attend_yes(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    _save_attendance(True, body, say, client)


@bolt_app.action("attend_no")
def attend_no(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    _save_attendance(False, body, say, client)


def _save_attendance(is_attend: bool, body, say, client) -> None:
    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass

    from db.repository import get_or_create_user_by_name

    user = get_or_create_user_by_name(real_name or "unknown")
    upsert_attendance(user.id, datetime.now(timezone.utc), is_attend)
    say("出勤予定を保存しました。" if is_attend else "休み予定を保存しました。")


def show_attendance_overview(say) -> None:
    now = datetime.now(timezone.utc)
    users = get_users()
    user_map: Dict[str, str] = {u.id: u.name for u in users}
    rows = get_attendance_between_tue_fri(now)

    # group by date with default 未報告 and fill from records
    from collections import defaultdict

    by_date: Dict[str, Dict[str, str]] = defaultdict(dict)  # date -> user_id -> status
    # initialize with 未報告
    for r in rows:
        key = f"{r['_year']:04d}-{r['_month']:02d}-{r['_day']:02d}"
        by_date.setdefault(key, {})
    # Ensure at least some target dates exist; if no rows, we still want show upcoming Tue/Fri with 未報告
    if not by_date:
        # Create next 6 Tue/Fri dates as placeholders
        from datetime import timedelta
        cur = now
        created = 0
        while created < 6:
            jst = cur.astimezone(timezone(timedelta(hours=9)))
            if jst.weekday() in (1, 4):
                key = f"{jst.year:04d}-{jst.month:02d}-{jst.day:02d}"
                by_date.setdefault(key, {})
                created += 1
            cur += timedelta(days=1)

    # Set records
    for r in rows:
        key = f"{r['_year']:04d}-{r['_month']:02d}-{r['_day']:02d}"
        by_date[key][r["user_id"]] = "出勤" if r["is_attend"] else "休み"

    # Build blocks
    blocks = [{"type": "header", "text": {"type": "plain_text", "text": "出勤確認（火/金）"}}]
    if not by_date:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "対象期間にデータがありません。"}})
    else:
        for day, status_map in sorted(by_date.items()):
            lines = []
            for u in users:
                status = status_map.get(u.id, "未報告")
                lines.append(f"{u.name}: {status}")
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*{day}*\n" + "\n".join(lines)}})

    say(blocks=blocks, text="出勤確認")
