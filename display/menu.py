from boltApp import bolt_app
"""Menu and actions"""
from datetime import datetime, timezone
from db.repository import get_users, has_active_work, get_or_create_user

def display_menu(say, body=None, client=None) -> None:
    # ユーザーの当日未終了勤務があるかで、開始/退勤ボタンを出し分け
	show_end = False  # 既定では退勤ボタンは出さない
	try:
		slack_user_id = None
		if body and isinstance(body, dict):
			slack_user_id = body.get("user", {}).get("id") or body.get("event", {}).get("user")
		user = None
		display_name = None
		if client and slack_user_id:
			# プロフィールが取得できる場合は名前も
			prof = client.users_profile_get(user=slack_user_id)
			display_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
		if slack_user_id:
			user = get_or_create_user(slack_user_id, display_name)
			show_end = has_active_work(user.id, datetime.now(timezone.utc))

	except Exception:
		# 失敗時は安全側で開始のみを表示
		show_end = False
	primary_row: list[dict] = []
	if show_end:
		primary_row.append({"type": "button", "text": {"type": "plain_text", "text": "退勤"}, "action_id": "end_work"})
	else:
		primary_row.append({"type": "button", "text": {"type": "plain_text", "text": "出勤開始"}, "style": "primary", "action_id": "start_work"})

	blocks = [
		{"type": "header", "text": {"type": "plain_text", "text": "勤怠メニュー", "emoji": True}},
		{"type": "actions", "elements": primary_row},
		{
			"type": "actions",
			"elements": [
				{"type": "button", "text": {"type": "plain_text", "text": "出勤更新"}, "action_id": "update_attendance"},
				{"type": "button", "text": {"type": "plain_text", "text": "出勤確認"}, "action_id": "check_attendance"},
				{"type": "button", "text": {"type": "plain_text", "text": "ユーザー情報"}, "action_id": "user_info"},
			],
		},
	]
	say(blocks=blocks, text="項目を選択してください。")


@bolt_app.action("start_work")
def handle_start_work(ack, body, say, logger):  # type: ignore[no-redef]
	ack()
	# 遅延インポートで循環を回避
	from handlers.startWork import start_work  # type: ignore
	start_work(say)


@bolt_app.action("end_work")
def handle_end_work(ack, body, say, client=None):  # type: ignore[no-redef]
	from handlers.workflows import prompt_end_work
	from db.repository import get_or_create_user

	ack()

	# ユーザー情報を取得
	user_slack_id = body.get("user", {}).get("id")
	display_name = None
	if user_slack_id and client:
		try:
			prof = client.users_profile_get(user=user_slack_id)
			display_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
		except Exception:
			pass

	user = get_or_create_user(user_slack_id or "unknown", display_name)
	prompt_end_work(say, user_id=user.id)

@bolt_app.action("update_attendance")
def handle_update_attendance(ack, body, say):  # type: ignore[no-redef]
	from handlers.attendance import prompt_attendance

	ack()
	prompt_attendance(say)

@bolt_app.action("check_attendance")
def handle_check_attendance(ack, body, say, client):  # type: ignore[no-redef]
	from handlers.attendance import show_attendance_overview

	ack()
	show_attendance_overview(say, client)

@bolt_app.action("user_info")
def handle_user_info(ack, body, say, client, logger):  # type: ignore[no-redef]
	from handlers.user_profile import show_or_edit_user

	ack()
	slack_user_id = body.get("user", {}).get("id")
	# DM context: fetch Slack profile
	try:
		if slack_user_id:
			prof = client.users_profile_get(user=slack_user_id)
			real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
		else:
			real_name = None
	except Exception:
		real_name = None
	show_or_edit_user(say, real_name, slack_user_id)