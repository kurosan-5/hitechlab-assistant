"""
Slack Bot メインファイル (HTTP / Events API モード)

機能:
- DMで「テストメッセージ」と送ると「テスト」と返信
- Flask で /slack/events を公開し、ポート3001で待ち受け

必要な環境変数 (.env):
- SLACK_BOT_TOKEN: xoxb- で始まる Bot Token
- SLACK_SIGNING_SECRET: Slack App の Signing Secret
- PORT: (任意) デフォルトは 3001
"""

import logging
import os
import sys
from dotenv import load_dotenv
from display.menu import display_menu

def _setup_logging() -> None:
	logging.basicConfig(
		level=os.getenv("LOG_LEVEL", "INFO").upper(),
		format="%(asctime)s %(levelname)s %(name)s - %(message)s",
	)


def _get_env(key: str) -> str | None:
	val = os.getenv(key)
	return val if val and val.strip() else None



def main() -> int:
	# .env を読み込む（存在しない場合は無視）
	load_dotenv()
	_setup_logging()
	logger = logging.getLogger("hitech-memoBot")

	bot_token = _get_env("SLACK_BOT_TOKEN")
	signing_secret = _get_env("SLACK_SIGNING_SECRET")

	if not bot_token or not signing_secret:
		print(
			"[設定不足] SLACK_BOT_TOKEN と SLACK_SIGNING_SECRET を .env に設定してください。\n",
			file=sys.stderr,
		)
		return 2

	# 依存ライブラリのインポートはここで行い、未インストールでもコンパイル可能にする
	from slack_bolt import App
	from slack_bolt.adapter.flask import SlackRequestHandler
	from flask import Flask, request

	bolt_app = App(token=bot_token, signing_secret=signing_secret)

	@bolt_app.event("message")
	def handle_dm_message(body, say, logger):  # type: ignore[no-redef]
		event = body.get("event", {})
		# bot自身やスレッド更新等は無視
		if event.get("subtype"):
			return
		# DM以外は無視
		if event.get("channel_type") != "im":
			return

		text = event.get("text", "").strip()
		if text == "menu" or text == "メニュー" or text=="めにゅー":
			display_menu(say)

	flask_app = Flask(__name__)
	handler = SlackRequestHandler(bolt_app)

	@flask_app.route("/slack/events", methods=["POST"])
	def slack_events():  # type: ignore[no-redef]
		return handler.handle(request)

	port = int(os.getenv("PORT", "3001"))
	logger.info("Starting Slack bot HTTP server on port %s …", port)
	flask_app.run(host="0.0.0.0", port=port)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

