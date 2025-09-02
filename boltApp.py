import os
import sys
import logging
from dotenv import load_dotenv
from slack_bolt import App

# デバッグ用のロガー設定
logger = logging.getLogger(__name__)


def _get_env(key: str) -> str | None:
	val = os.getenv(key)
	return val if val and val.strip() else None


# .env を読み込む
load_dotenv()
logger.info("DEBUG: [boltApp] .env ファイル読み込み完了")

bot_token = _get_env("SLACK_BOT_TOKEN")
signing_secret = _get_env("SLACK_SIGNING_SECRET")

logger.info(f"DEBUG: [boltApp] 環境変数確認:")
logger.info(f"  - SLACK_BOT_TOKEN: {'設定済み' if bot_token else '未設定'}")
logger.info(f"  - SLACK_SIGNING_SECRET: {'設定済み' if signing_secret else '未設定'}")

if not bot_token or not signing_secret:
	logger.error("DEBUG: [boltApp] 必要な環境変数が不足しています")
	print(
		"[設定不足] SLACK_BOT_TOKEN と SLACK_SIGNING_SECRET を .env に設定してください。\n",
		file=sys.stderr,
	)
	# このモジュールは import される可能性があるため、即時終了は避ける
	# app.py 側で不備を検知し終了する想定
	bot_token = bot_token or ""
	signing_secret = signing_secret or ""

logger.info("DEBUG: [boltApp] Bolt app 初期化開始")
bolt_app = App(token=bot_token, signing_secret=signing_secret)
logger.info("DEBUG: [boltApp] Bolt app 初期化完了")
