import logging
import os
import sys
from display.menu import display_menu
from handlers.startWork import start_work
from handlers.workflows import prompt_end_work
from handlers.attendance import prompt_attendance, show_attendance_overview
from handlers.user_profile import show_or_edit_user
from boltApp import bolt_app
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

def _setup_logging() -> None:
	logging.basicConfig(
		level=os.getenv("LOG_LEVEL", "WARNING").upper(),
		format="%(asctime)s %(levelname)s %(name)s - %(message)s",
	)

	# Slackライブラリやその他の外部ライブラリのログを抑制
	logging.getLogger("slack_bolt").setLevel(logging.ERROR)
	logging.getLogger("slack_sdk").setLevel(logging.ERROR)
	logging.getLogger("urllib3").setLevel(logging.ERROR)
	logging.getLogger("requests").setLevel(logging.ERROR)
	logging.getLogger("httpx").setLevel(logging.ERROR)
	logging.getLogger("werkzeug").setLevel(logging.ERROR)
	logging.getLogger("flask").setLevel(logging.ERROR)


def _get_env(key: str) -> str | None:
	val = os.getenv(key)
	return val if val and val.strip() else None



def main() -> int:
	# .env を読み込む（存在しない場合は無視）
	_setup_logging()
	logger = logging.getLogger("hitech-memoBot")

	@bolt_app.event("message")
	def handle_dm_message(body, say, logger, client):  # type: ignore[no-redef]
		event = body.get("event", {})
		# bot自身やスレッド更新等は無視
		if event.get("subtype"):
			return
		# DM以外は無視
		if event.get("channel_type") != "im":
			return

		text = event.get("text", "").strip()
		if text in {"menu", "メニュー", "めにゅー"}:
			display_menu(say, body=body, client=client)
		elif text in {"出勤開始", "しゅっきん", "start"}:
			start_work(say)
		elif text in {"退勤", "たいきん", "end"}:
			# ユーザー情報を取得
			user_slack_id = event.get("user")
			display_name = None
			if user_slack_id:
				try:
					prof = client.users_profile_get(user=user_slack_id)
					display_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
				except Exception:
					pass

			from db.repository import get_or_create_user
			user = get_or_create_user(user_slack_id or "unknown", display_name)
			prompt_end_work(say, user_id=user.id)
		elif text in {"出勤更新", "予定", "att"}:
			prompt_attendance(say)
		elif text in {"出勤確認", "かくにん", "check"}:
			show_attendance_overview(say)
		elif text in {"ユーザー情報", "プロフィール", "user"}:
			# fetch display name and pass slack id
			try:
				user_slack_id = event.get("user")
				prof = client.users_profile_get(user=user_slack_id)
				real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
			except Exception:
				real_name = None
			show_or_edit_user(say, real_name, user_slack_id)

	flask_app = Flask(__name__)
	handler = SlackRequestHandler(bolt_app)

	@flask_app.route("/slack/events", methods=["POST"])
	def slack_events():  # type: ignore[no-redef]
		return handler.handle(request)

	@flask_app.get("/health")
	def health():
		return "ok", 20


	port = int(os.getenv("PORT", "3001"))
	logger.info("Starting Slack bot HTTP server on port %s …", port)
	flask_app.run(host="0.0.0.0", port=port)
	return 0

if __name__ == "__main__":
	raise SystemExit(main())
