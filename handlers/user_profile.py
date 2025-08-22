from __future__ import annotations

from typing import Any

from boltApp import bolt_app
from db.repository import get_or_create_user_by_name, update_user


def show_or_edit_user(say, real_name: str | None) -> None:
    user = get_or_create_user_by_name(real_name or "unknown")

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "ユーザー情報"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*名前*\n{user.name}"},
            {"type": "mrkdwn", "text": f"*連絡先*\n{user.contact or '-'}"},
            {"type": "mrkdwn", "text": f"*勤務形態*\n{user.work_type or '-'}"},
            {"type": "mrkdwn", "text": f"*交通費*\n{user.transportation_cost or '-'}"},
            {"type": "mrkdwn", "text": f"*時給*\n{user.hourly_wage or '-'}"},
        ]},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "編集"}, "action_id": "edit_user"}
        ]}
    ]
    say(blocks=blocks, text="ユーザー情報")


@bolt_app.action("edit_user")
def edit_user(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass
    user = get_or_create_user_by_name(real_name or "unknown")

    blocks = [
        {"type": "input", "block_id": "contact", "element": {"type": "plain_text_input", "action_id": "input", "initial_value": user.contact or ""}, "label": {"type": "plain_text", "text": "連絡先"}},
        {"type": "input", "block_id": "work_type", "element": {"type": "plain_text_input", "action_id": "input", "initial_value": user.work_type or ""}, "label": {"type": "plain_text", "text": "勤務形態"}},
        {"type": "input", "block_id": "transportation_cost", "element": {"type": "plain_text_input", "action_id": "input", "initial_value": str(user.transportation_cost or "")}, "label": {"type": "plain_text", "text": "交通費"}},
        {"type": "input", "block_id": "hourly_wage", "element": {"type": "plain_text_input", "action_id": "input", "initial_value": str(user.hourly_wage or "")}, "label": {"type": "plain_text", "text": "時給"}},
        {"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "保存"}, "style": "primary", "action_id": "save_user"}]}
    ]
    say(blocks=blocks, text="ユーザー編集")


@bolt_app.action("save_user")
def save_user(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass
    user = get_or_create_user_by_name(real_name or "unknown")

    values = body.get("state", {}).get("values", {})
    payload: dict[str, Any] = {}
    for block_id, blocks in values.items():
        if block_id in ("contact", "work_type", "transportation_cost", "hourly_wage"):
            val = blocks.get("input", {}).get("value")
            if block_id in ("transportation_cost", "hourly_wage"):
                try:
                    payload[block_id] = float(val) if val else None
                except Exception:
                    continue
            else:
                payload[block_id] = val

    user2 = update_user(user.id, payload)
    say("ユーザー情報を保存しました。")
