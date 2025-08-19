from boltApp import bolt_app
from display.startWork import start_work

def display_menu(say) -> None:
	blocks = [
		{
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": "メニュー",
				"emoji": True
			}
		},
		{
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "勤務開始"
					},
					"style": "primary",
					"action_id": "start_work"
				},
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "戻る"
					},
					"action_id": "back_to_main_menu",
				}
			]
		}
	]
	say(blocks=blocks, text="項目を選択してください。")

# 勤務開始ボタン押下
	@bolt_app.action("start_work")
	def handle_start_work(ack, body, say, logger):
		ack()
		action = body["actions"][0]
		logger.info(f"button pressed: action_id={action['action_id']}, value={action.get('value')}")
		start_work(say)