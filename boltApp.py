import os
import sys
from dotenv import load_dotenv
from slack_bolt import App


def _get_env(key: str) -> str | None:
	val = os.getenv(key)
	return val if val and val.strip() else None


# .env を読み込む
load_dotenv()

bot_token = _get_env("SLACK_BOT_TOKEN")
signing_secret = _get_env("SLACK_SIGNING_SECRET")

if not bot_token or not signing_secret:
	print(
		"[設定不足] SLACK_BOT_TOKEN と SLACK_SIGNING_SECRET を .env に設定してください。\n",
		file=sys.stderr,
	)
	# このモジュールは import される可能性があるため、即時終了は避ける
	# app.py 側で不備を検知し終了する想定
	bot_token = bot_token or ""
	signing_secret = signing_secret or ""

bolt_app = App(token=bot_token, signing_secret=signing_secret)
