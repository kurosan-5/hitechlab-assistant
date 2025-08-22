"""
Deprecated: 仕様変更によりSupabaseへ移行。必要があれば手動で参照。
"""
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = [
	"https://www.googleapis.com/auth/spreadsheets",
]

def get_gsheet_client():
	creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
	creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPES)
	return gspread.authorize(creds)


def _get_worksheet():
	gc = get_gsheet_client()
	spreadsheet_id = os.environ["SPREADSHEET_ID"]
	sh = gc.open_by_key(spreadsheet_id)
	ws = sh.get_worksheet(0)
	if ws is None:
		# 初期ワークシートがない場合は作成（タイトルは任意）
		ws = sh.add_worksheet(title="Sheet1", rows="100", cols="26")
	return sh, ws

def add_row(data):
	sh, ws = _get_worksheet()
	# 既存データの最終行を取得
	last_row = len(ws.get_all_values())
	next_row = last_row + 1
	# data は 2次元配列想定（[[val1, val2, ...], [...]] など）
	ws.update(f"A{next_row}", data)
	return sh.url

def read_row(index: int) -> list[str]:
	sh, ws = _get_worksheet()
	# gspread は 1 始まり。0 以下は 1 行目として扱う
	row = index if index and index > 0 else 1
	return ws.row_values(row)

def update_row(index: int, data: list[list[str]]):
	sh, ws = _get_worksheet()
	row = index if index and index > 0 else 1
	ws.update(f"A{row}", data)
	return sh.url