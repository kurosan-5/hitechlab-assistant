import logging
import os
import sys
from display.menu import display_menu
from handlers.startWork import start_work
from handlers.workflows import prompt_end_work
from handlers.attendance import prompt_attendance, show_attendance_overview
from handlers.user_profile import show_or_edit_user
# チャンネル機能をインポート
from handlers.channel.handlers import register_channel_handlers
from boltApp import bolt_app
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

def _setup_logging() -> None:
	logging.basicConfig(
		level=os.getenv("LOG_LEVEL", "DEBUG").upper(),  # DEBUG: DEBUGレベルに変更してより詳細なログを出力
		format="%(asctime)s %(levelname)s %(name)s - %(message)s",
	)

	# DEBUG: Slackライブラリのログレベルを一時的に緩和
	logging.getLogger("slack_bolt").setLevel(logging.WARNING)
	logging.getLogger("slack_sdk").setLevel(logging.WARNING)
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
	logger = logging.getLogger("hitechlab-assistant")


	# Slack APIの権限をテスト
	try:
		from boltApp import bolt_app

		# auth.test を実行して基本権限を確認
		auth_response = bolt_app.client.auth_test()

		# botのスコープを確認
		try:
			scopes_response = bolt_app.client.auth_test()
		except Exception as scope_error:
			logger.error(f"Slack APIのスコープ確認に失敗しました: {str(scope_error)}")

	except Exception as e:
		logger.error(f"Slack APIの認証に失敗しました: {str(e)}")

	@bolt_app.event("message")
	def handle_unified_message(body, say, logger, client):  # type: ignore[no-redef]
		"""統一メッセージハンドラー - DM/チャンネルを判定して適切な処理に振り分け"""

		event = body.get("event", {})

		# bot自身やスレッド更新等は無視
		if event.get("subtype") or event.get("bot_id"):
			return

		channel_type = event.get("channel_type")
		text = event.get("text", "").strip()
		user_id = event.get("user")
		channel_id = event.get("channel")


		if channel_type == "im":
			# DM処理
			handle_dm_logic(event, body, say, client, logger)
		else:
			# チャンネル処理
			handle_channel_logic(event, body, say, client, logger)

	def handle_dm_logic(event, body, say, client, logger):
		"""DM専用処理ロジック"""
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
		elif text in {"help", "ヘルプ", "使い方"}:
			help_blocks = [
				{
					"type": "header",
					"text": {
						"type": "plain_text",
						"text": "🤖 DM機能ヘルプ（勤怠管理）",
						"emoji": True
					}
				},
				{
					"type": "section",
					"text": {
						"type": "mrkdwn",
						"text": "*📋 勤怠管理機能:*\n• `メニュー` - メインメニューを表示\n• `出勤開始` / `しゅっきん` / `start` - 勤務開始時刻を記録\n• `退勤` / `たいきん` / `end` - 勤務終了時刻を記録\n• `出勤更新` / `予定` / `att` - 出勤予定を登録\n• `出勤確認` / `かくにん` / `check` - チーム出勤状況を確認\n• `ユーザー情報` / `プロフィール` / `user` - 個人設定と勤務記録"
					}
				},
				{
					"type": "section",
					"text": {
						"type": "mrkdwn",
						"text": "*  DM専用コマンド:*\n• 出勤開始、退勤の記録\n• 火曜日・金曜日の出勤予定管理\n• 個人の勤務時間確認\n• チーム全体の出勤状況確認"
					}
				}
			]
			say(blocks=help_blocks)

	def handle_channel_logic(event, body, say, client, logger):
		"""チャンネル専用処理ロジック"""
		text = event.get("text", "").strip()
		channel_id = event.get("channel")
		user_id = event.get("user")


		try:
			# チャンネル機能を直接処理
			from handlers.channel.handlers import handle_channel_message
			handle_channel_message(event, body, say, client, logger)

		except Exception as e:
			say(text=f"❌ チャンネル処理中にエラーが発生しました: {str(e)}")

	# チャンネル機能のアクションハンドラーのみ登録（メッセージハンドラーは統一ハンドラーを使用）
	register_channel_handlers(bolt_app)

	# DEBUG: 全イベントをキャッチするハンドラー（デバッグ用）
	@bolt_app.event({"type": "message"})
	def catch_all_messages(body, logger):
		"""全メッセージイベントをキャッチ（デバッグ用）"""
		event = body.get("event", {})
		channel_type = event.get("channel_type", "unknown")
		text = event.get("text", "")
		channel_id = event.get("channel", "unknown")


	flask_app = Flask(__name__)
	handler = SlackRequestHandler(bolt_app)

	@flask_app.route("/slack/events", methods=["POST"])
	def slack_events():  # type: ignore[no-redef]
		try:
			# Content-Typeをチェック
			content_type = request.content_type

			# リクエストボディをログ出力（セキュリティ上、一部のみ）
			request_data = None
			if content_type and 'application/json' in content_type:
				request_data = request.get_json()
				if request_data:
					event_type = request_data.get("type")
					event = request_data.get("event", {})

			result = handler.handle(request)
			return result
		except Exception as e:
			return "Internal Server Error", 500

	@flask_app.get("/health")
	def health():
		return "ok", 20


	port = int(os.getenv("PORT", "3001"))
	flask_app.run(host="0.0.0.0", port=port)
	return 0

if __name__ == "__main__":
	raise SystemExit(main())
