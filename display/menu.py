from boltApp import bolt_app
from .startWork import start_work


def display_menu(say) -> None:
	blocks = [
		{"type": "header", "text": {"type": "plain_text", "text": "勤怠メニュー", "emoji": True}},
		{
			"type": "actions",
			"elements": [
				{"type": "button", "text": {"type": "plain_text", "text": "出勤開始"}, "style": "primary", "action_id": "start_work"},
				{"type": "button", "text": {"type": "plain_text", "text": "退勤"}, "action_id": "end_work"},
			],
		},
		{
			"type": "actions",
			"elements": [
				{"type": "button", "text": {"type": "plain_text", "text": "出勤更新"}, "action_id": "update_attendance"},
				{"type": "button", "text": {"type": "plain_text", "text": "出勤確認（火/金）"}, "action_id": "check_attendance"},
				{"type": "button", "text": {"type": "plain_text", "text": "ユーザー情報"}, "action_id": "user_info"},
			],
		},
	]
	say(blocks=blocks, text="項目を選択してください。")


@bolt_app.action("start_work")
def handle_start_work(ack, body, say, logger):  # type: ignore[no-redef]
	ack()
	start_work(say)


@bolt_app.action("end_work")
def handle_end_work(ack, body, say):  # type: ignore[no-redef]
	from handlers.workflows import prompt_end_work

	ack()
	prompt_end_work(say)


@bolt_app.action("update_attendance")
def handle_update_attendance(ack, body, say):  # type: ignore[no-redef]
	from handlers.attendance import prompt_attendance

	ack()
	prompt_attendance(say)


@bolt_app.action("check_attendance")
def handle_check_attendance(ack, body, say):  # type: ignore[no-redef]
	from handlers.attendance import show_attendance_overview

	ack()
	show_attendance_overview(say)


@bolt_app.action("user_info")
def handle_user_info(ack, body, say, client, logger):  # type: ignore[no-redef]
	from handlers.user_profile import show_or_edit_user

	ack()
	user_id = body.get("user", {}).get("id") or body.get("user", {}) or body.get("user_id")
	# DM context: fetch Slack profile
	try:
		if user_id:
			prof = client.users_profile_get(user=user_id)
			real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
		else:
			real_name = None
	except Exception:
		real_name = None
	show_or_edit_user(say, real_name)