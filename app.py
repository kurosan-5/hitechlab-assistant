import logging
import os
import sys
from display.menu import display_menu
from display.startWork import start_work
from boltApp import bolt_app
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

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
	_setup_logging()
	logger = logging.getLogger("hitech-memoBot")

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
