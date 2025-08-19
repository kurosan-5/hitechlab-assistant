from datetime import datetime
from boltApp import bolt_app

def display_menu(say) -> None:
	# 現在のローカル時刻から日付と時間の文字列を生成
	now = datetime.now()
	initial_date = now.strftime("%Y-%m-%d")
	initial_time = now.strftime("%H:%M")

	blocks = [
		{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": "開始時間を選択",
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
def save_start_time(ack, body, say):
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
		say(text=f"開始日時が設定されました: {selected_date} {selected_time}")
	else:
		say(text="開始日時の選択を取得できませんでした。もう一度お試しください。")
