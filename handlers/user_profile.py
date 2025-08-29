from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Any

from boltApp import bolt_app
from db.repository import get_or_create_user, update_user, get_work_hours_by_month, delete_work_record


def format_work_time_display(start_dt: datetime, end_dt: datetime | None, target_year: int, target_month: int) -> str:
    """勤務時間の表示をフォーマット（未終了の場合も対応）"""
    jst_tz = timezone(timedelta(hours=9))
    start_jst = start_dt.astimezone(jst_tz)

    # 基準となる年月
    base_year = target_year
    base_month = target_month

    start_str = ""
    end_str = ""

    # 開始時刻のフォーマット（日付を常に含める）
    if start_jst.year != base_year:
        start_str = f"{start_jst.year}/{start_jst.month}/{start_jst.day} {start_jst.hour}:{start_jst.minute:02d}"
    elif start_jst.month != base_month:
        start_str = f"{start_jst.month}/{start_jst.day} {start_jst.hour}:{start_jst.minute:02d}"
    else:
        start_str = f"{start_jst.day}日 {start_jst.hour}:{start_jst.minute:02d}"

    # 未終了の場合
    if end_dt is None:
        return f"{start_str} 〜"

    end_jst = end_dt.astimezone(jst_tz)

    # 終了時刻のフォーマット
    if end_jst.year != base_year:
        end_str = f"{end_jst.year}/{end_jst.month}/{end_jst.day} {end_jst.hour}:{end_jst.minute:02d}"
    elif end_jst.month != base_month:
        end_str = f"{end_jst.month}/{end_jst.day} {end_jst.hour}:{end_jst.minute:02d}"
    elif end_jst.day != start_jst.day:
        end_str = f"{end_jst.day}日 {end_jst.hour}:{end_jst.minute:02d}"
    else:
        end_str = f"{end_jst.hour}:{end_jst.minute:02d}"

    return f"{start_str} 〜 {end_str}"


def show_or_edit_user(say, real_name: str | None, slack_user_id: str | None = None) -> None:
    """ユーザー情報のメニューを表示"""
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "ユーザー情報メニュー"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "ユーザー情報確認"}, "action_id": "view_user_info"},
            {"type": "button", "text": {"type": "plain_text", "text": "ユーザー情報編集"}, "action_id": "edit_user"},
        ]},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "勤務時間確認"}, "action_id": "check_work_hours"},
            {"type": "button", "text": {"type": "plain_text", "text": "勤務時間削除"}, "action_id": "delete_work_hours"},
        ]},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "戻る"}, "action_id": "back_to_menu"}
        ]}
    ]
    say(blocks=blocks, text="ユーザー情報メニュー")

def show_user_info(say, real_name: str | None, slack_user_id: str | None = None) -> None:
    """ユーザー情報の詳細を表示"""
    user = get_or_create_user(slack_user_id or "unknown", real_name)

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "ユーザー情報"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*名前*\n{user.name}"},
            {"type": "mrkdwn", "text": f"*連絡先*\n{user.contact or '-'}"},
            {"type": "mrkdwn", "text": f"*勤務形態*\n{user.work_type or '-'}"},
            {"type": "mrkdwn", "text": f"*交通費*\n{user.transportation_cost or '-'}"},
            {"type": "mrkdwn", "text": f"*時給*\n{user.hourly_wage or '-'}"},
        ]},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "戻る"}, "action_id": "back_to_user_menu"}
        ]}
    ]
    say(blocks=blocks, text="ユーザー情報")


@bolt_app.action("view_user_info")
def view_user_info(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass
    show_user_info(say, real_name, user_slack_id)


@bolt_app.action("back_to_user_menu")
def back_to_user_menu(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass
    show_or_edit_user(say, real_name, user_slack_id)


@bolt_app.action("check_work_hours")
def check_work_hours(ack, body, say):  # type: ignore[no-redef]
    ack()

    # 現在の日付から例を生成
    now = datetime.now(timezone(timedelta(hours=9)))  # JST
    example = f"{now.year:04d}{now.month:02d}"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "勤務時間確認"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"何月分の給料を確認しますか？\n例: {example}"}},
        {"type": "input", "block_id": "work_month", "element": {"type": "plain_text_input", "action_id": "input", "placeholder": {"type": "plain_text", "text": example}}, "label": {"type": "plain_text", "text": "年月 (YYYYMM形式)"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "確認"}, "style": "primary", "action_id": "confirm_work_hours"},
            {"type": "button", "text": {"type": "plain_text", "text": "戻る"}, "action_id": "back_to_user_menu"}
        ]}
    ]
    say(blocks=blocks, text="勤務時間確認")


@bolt_app.action("delete_work_hours")
def delete_work_hours(ack, body, say):  # type: ignore[no-redef]
    ack()

    # 現在の日付から例を生成
    now = datetime.now(timezone(timedelta(hours=9)))  # JST
    example = f"{now.year:04d}{now.month:02d}"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "勤務時間削除"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"何月分の勤務記録を削除しますか？\n例: {example}"}},
        {"type": "input", "block_id": "work_month", "element": {"type": "plain_text_input", "action_id": "input", "placeholder": {"type": "plain_text", "text": example}}, "label": {"type": "plain_text", "text": "年月 (YYYYMM形式)"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "確認"}, "style": "primary", "action_id": "confirm_delete_work_hours"},
            {"type": "button", "text": {"type": "plain_text", "text": "戻る"}, "action_id": "back_to_user_menu"}
        ]}
    ]
    say(blocks=blocks, text="勤務時間削除")


@bolt_app.action("confirm_work_hours")
def confirm_work_hours(ack, body, say, client):  # type: ignore[no-redef]
    ack()

    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass

    user = get_or_create_user(user_slack_id or "unknown", real_name)

    # 入力された年月を取得
    values = body.get("state", {}).get("values", {})
    work_month = None

    for _, blocks in values.items():
        for action_id, payload in blocks.items():
            if action_id == "input":
                work_month = payload.get("value")
                break

    now = datetime.now(timezone(timedelta(hours=9)))
    example = f"{now.year:04d}{now.month:02d}"
    # 年月の形式チェック
    if not work_month:
        work_month = example
    if len(work_month) != 6 or not work_month.isdigit():
        say(f"❌ 正しい形式で入力してください。例: {example}")
        return

    try:
        year = int(work_month[:4])
        month = int(work_month[4:6])
        if month < 1 or month > 12:
            raise ValueError("Invalid month")
    except ValueError:
        now = datetime.now(timezone(timedelta(hours=9)))
        example = f"{now.year:04d}{now.month:02d}"
        say(f"❌ 正しい形式で入力してください。例: {example}")
        return

    # 勤務記録を取得
    work_records, total_hours = get_work_hours_by_month(user.id, year, month)

    if not work_records:
        say(f"📅 {year}年{month}月の勤務記録はありません。")
        return

    # 詳細一覧を作成
    work_details = []
    jst_tz = timezone(timedelta(hours=9))
    month_end = datetime(year + (1 if month == 12 else 0), (1 if month == 12 else month + 1), 1, tzinfo=jst_tz)

    for record in work_records:
        start_dt = datetime.fromisoformat(record["start_time"].replace("Z", "+00:00"))

        # 終了時刻がある場合とない場合で処理を分ける
        if record.get("end_time"):
            end_dt = datetime.fromisoformat(record["end_time"].replace("Z", "+00:00"))

            # 月をまたぐ場合の実効終了時刻
            effective_end = min(end_dt, month_end.astimezone(timezone.utc))

            # 時間表示をフォーマット
            time_display = format_work_time_display(start_dt, end_dt, year, month)

            # 実際の勤務時間を計算（月内分のみ）
            work_duration = effective_end - start_dt
            break_minutes = record.get("break_time_min", 0) or 0

            # 月をまたぐ場合の休憩時間比例配分
            total_duration = end_dt - start_dt
            if total_duration.total_seconds() > 0:
                break_ratio = work_duration.total_seconds() / total_duration.total_seconds()
                effective_break_minutes = break_minutes * break_ratio
            else:
                effective_break_minutes = 0

            work_minutes = work_duration.total_seconds() / 60 - effective_break_minutes
            work_hours = max(0, work_minutes / 60)

            # 月をまたぐ場合は注記を追加
            note = ""
            if end_dt > month_end.astimezone(timezone.utc):
                note = " *（月をまたぐため月内分のみ）*"

            work_details.append(f"• {time_display} ({work_hours:.2f}時間){note}")
        else:
            # 未終了の場合
            time_display = format_work_time_display(start_dt, None, year, month)
            work_details.append(f"• {time_display} *（未終了）*")

    # 詳細リストを文字列として結合
    details_text = "\n".join(work_details)

    # 結果を表示
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{year}年{month}月の勤務時間"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*合計勤務時間*: {total_hours:.2f}時間"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*勤務日数*: {len(work_records)}日"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*勤務時間詳細*:\n{details_text}"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "戻る"}, "action_id": "back_to_user_menu"}
        ]}
    ]

    say(blocks=blocks, text=f"{year}年{month}月の勤務時間")


@bolt_app.action("confirm_delete_work_hours")
def confirm_delete_work_hours(ack, body, say, client):  # type: ignore[no-redef]
    ack()

    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass

    user = get_or_create_user(user_slack_id or "unknown", real_name)

    # 入力された年月を取得
    values = body.get("state", {}).get("values", {})
    work_month = None

    for _, blocks in values.items():
        for action_id, payload in blocks.items():
            if action_id == "input":
                work_month = payload.get("value")
                break
    now = datetime.now(timezone(timedelta(hours=9)))
    example = f"{now.year:04d}{now.month:02d}"
    # 年月の形式チェック
    if not work_month:
        work_month = example
    # 年月の形式チェック
    if len(work_month) != 6 or not work_month.isdigit():
        say(f"❌ 正しい形式で入力してください。例: {example}")
        return

    try:
        year = int(work_month[:4])
        month = int(work_month[4:6])
        if month < 1 or month > 12:
            raise ValueError("Invalid month")
    except ValueError:
        now = datetime.now(timezone(timedelta(hours=9)))
        example = f"{now.year:04d}{now.month:02d}"
        say(f"❌ 正しい形式で入力してください。例: {example}")
        return

    # 勤務記録を取得
    work_records, _ = get_work_hours_by_month(user.id, year, month)

    if not work_records:
        say(f"📅 {year}年{month}月の勤務記録はありません。")
        return

    # 勤務記録をボタンで表示
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{year}年{month}月の勤務記録削除"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "削除したい勤務記録を選択してください："}}
    ]

    around_numbers = [
        "①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
        "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳"
    ]

    # 古い順でボタンを追加
    for i, record in enumerate(work_records, 1):
        # インデックスは0から始まるので、i-1を使用（iは1から始まる）
        number_index = i - 1
        if number_index >= len(around_numbers):
            # 配列の範囲を超えた場合は数字を使用
            number_str = str(i)
        else:
            number_str = around_numbers[number_index]

        start_time = datetime.fromisoformat(record["start_time"].replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(record["end_time"].replace("Z", "+00:00")) if record.get("end_time") else None

        # JSTに変換
        jst_start = start_time.astimezone(timezone(timedelta(hours=9)))
        jst_end = end_time.astimezone(timezone(timedelta(hours=9))) if end_time else None

        if jst_end:
            duration = end_time - start_time
            break_minutes = record.get("break_time_min", 0) or 0
            work_minutes = duration.total_seconds() / 60 - break_minutes
            work_hours = work_minutes / 60

            text = f"{number_str}: {jst_start.strftime('%m/%d %H:%M')}〜{jst_end.strftime('%H:%M')} ({work_hours:.2f}時間)"
        else:
            text = f"{number_str}: {jst_start.strftime('%m/%d %H:%M')}〜（未終了）"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": f"削除"},
                "action_id": f"delete_work_record_{record['id']}",
                "style": "danger"
            }
        })

    blocks.append({
        "type": "actions",
        "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "戻る"}, "action_id": "back_to_user_menu"}
        ]
    })

    say(blocks=blocks, text=f"{year}年{month}月の勤務記録削除")


@bolt_app.action(re.compile(r"delete_work_record_.*"))
def handle_delete_work_record(ack, body, say):  # type: ignore[no-redef]
    ack()

    action_id = body.get("actions", [{}])[0].get("action_id", "")
    work_id = action_id.replace("delete_work_record_", "")

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "勤務記録削除確認"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ 本当にこの勤務記録を削除しますか？\nこの操作は取り消せません。"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "はい、削除します"}, "style": "danger", "action_id": f"confirm_delete_{work_id}"},
            {"type": "button", "text": {"type": "plain_text", "text": "キャンセル"}, "action_id": "back_to_user_menu"}
        ]}
    ]

    say(blocks=blocks, text="削除確認")


@bolt_app.action(re.compile(r"confirm_delete_.*"))
def handle_confirm_delete(ack, body, say, client):  # type: ignore[no-redef]
    ack()

    action_id = body.get("actions", [{}])[0].get("action_id", "")
    work_id = action_id.replace("confirm_delete_", "")

    # 勤務記録を削除
    success = delete_work_record(work_id)

    if success:
        say("✅ 勤務記録を削除しました。")
    else:
        say("❌ 勤務記録の削除に失敗しました。")

    # ユーザーメニューに戻る
    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass
    show_or_edit_user(say, real_name, user_slack_id)


@bolt_app.action("edit_user")
def edit_user(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass
    user = get_or_create_user(user_slack_id or "unknown", real_name)

    blocks = [
        {"type": "input", "block_id": "name", "element": {"type": "plain_text_input", "action_id": "input", "initial_value": user.name or ""}, "label": {"type": "plain_text", "text": "名前"}},
        {"type": "input", "block_id": "contact", "element": {"type": "plain_text_input", "action_id": "input", "initial_value": user.contact or ""}, "label": {"type": "plain_text", "text": "連絡先"}},
        {"type": "input", "block_id": "work_type", "element": {"type": "plain_text_input", "action_id": "input", "initial_value": user.work_type or ""}, "label": {"type": "plain_text", "text": "勤務形態"}},
        {"type": "input", "block_id": "transportation_cost", "element": {"type": "plain_text_input", "action_id": "input", "initial_value": str(user.transportation_cost or "")}, "label": {"type": "plain_text", "text": "交通費"}},
        {"type": "input", "block_id": "hourly_wage", "element": {"type": "plain_text_input", "action_id": "input", "initial_value": str(user.hourly_wage or "")}, "label": {"type": "plain_text", "text": "時給"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "保存"}, "style": "primary", "action_id": "save_user"},
            {"type": "button", "text": {"type": "plain_text", "text": "戻る"}, "action_id": "back_to_user_menu"}
        ]}
    ]
    say(blocks=blocks, text="ユーザー編集")


@bolt_app.action("save_user")
def save_user(ack, body, say, client):  # type: ignore[no-redef]
    ack()
    user_slack_id = body.get("user", {}).get("id")
    real_name = None
    if user_slack_id:
        try:
            prof = client.users_profile_get(user=user_slack_id)
            real_name = prof.get("profile", {}).get("real_name") or prof.get("profile", {}).get("display_name")
        except Exception:
            pass
    user = get_or_create_user(user_slack_id or "unknown", real_name)

    values = body.get("state", {}).get("values", {})
    payload: dict[str, Any] = {}
    for block_id, blocks in values.items():
        if block_id in ("name", "contact", "work_type", "transportation_cost", "hourly_wage"):
            val = blocks.get("input", {}).get("value")
            if block_id in ("transportation_cost", "hourly_wage"):
                try:
                    payload[block_id] = float(val) if val else None
                except Exception:
                    continue
            else:
                payload[block_id] = val

    user2 = update_user(user.id, payload)
    say("ユーザー情報を保存しました。")

    # ユーザーメニューに戻る
    show_or_edit_user(say, real_name, user_slack_id)

@bolt_app.action("back_to_menu")
def back_to_menu(ack, body, say):
    ack()
    from display.menu import display_menu
    display_menu(say, body=body)