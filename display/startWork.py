from datetime import datetime, timezone, timedelta
from boltApp import bolt_app
from db.repository import start_work as repo_start_work, get_or_create_user_by_name

def start_work(say) -> None:
	# 現在のローカル時刻から日付と時間の文字列を生成
	now = datetime.now()
	initial_date = now.strftime("%Y-%m-%d")
	initial_time = now.strftime("%H:%M")

	blocks = [
		{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": "開始日時を選択",
				"emoji": True
			}
		},
		{
			"type": "actions",
			"elements": [
				{
					"type": "datepicker",
					"initial_date": initial_date,
					"placeholder": {
						"type": "plain_text",
						"text": "Select a date",
						"emoji": True
					},
					"action_id": "datapicker"
				},
				{
					"type": "timepicker",
					"initial_time": initial_time,
					"placeholder": {
						"type": "plain_text",
						"text": "Select time",
						"emoji": True
					},
					"action_id": "timepicker"
				}
			]
		},
		{
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "決定",
						"emoji": True
					},
					"style": "primary",
					"value": "click_me_123",
					"action_id": "save_start_time"
				},
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "キャンセル",
						"emoji": True
					},
					"value": "click_me_123",
					"action_id": "cancel_start_time"
				}
			]
		}
	]
	say(blocks=blocks, text="開始時間を選択してください。")


@bolt_app.action("save_start_time")
def save_start_time(ack, body, say, client):
	ack()
	# ユーザーが選択した開始日時を取得（block_id が動的なため values を走査）
	selected_date = None
	selected_time = None
	try:
		values = body.get("state", {}).get("values", {})
		for _, blocks in values.items():
			for action_id, payload in blocks.items():
				if action_id == "datapicker":
					# datepicker は selected_date を持つ
					selected_date = payload.get("selected_date")
				elif action_id == "timepicker":
					# timepicker は selected_time を持つ
					selected_time = payload.get("selected_time")
	except Exception:
		pass

	if selected_date and selected_time:
		# Slackプロフィール名でユーザー同定（簡易）
		real_name = None
		try:
			user_slack_id = body.get("user", {}).get("id")
			if user_slack_id:
				prof = client.users_profile_get(user=user_slack_id)
				real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
		except Exception:
			pass

		user = get_or_create_user_by_name(real_name or "unknown")

		# 入力はJSTとして解釈し、UTCへ変換
		hh, mm = map(int, selected_time.split(":"))
		y, m, d = map(int, selected_date.split("-"))
		jst = timezone(timedelta(hours=9))
		start_ts = datetime(y, m, d, hh, mm, tzinfo=jst).astimezone(timezone.utc)

		repo_start_work(user.id, start_ts)
		say(text=f"開始を登録しました: {selected_date} {selected_time}")
	else:
		say(text="開始日時の選択を取得できませんでした。もう一度お試しください。")

@bolt_app.action("cancel_start_time")
def cancel_start_time(ack, say):
	ack()
	say(text="開始日時の選択がキャンセルされました。メニューに戻ります。")
	from display.menu import display_menu  # 遅延インポート
	display_menu(say)  # メニューに戻る
