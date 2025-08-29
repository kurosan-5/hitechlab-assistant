from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from .supabase_client import get_client, to_record


JST = timezone(timedelta(hours=9))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ymd_from_jst(dt_utc: datetime) -> tuple[int, int, int]:
    # convert UTC to JST for y/m/d columns
    jst_dt = dt_utc.astimezone(JST)
    return jst_dt.year, jst_dt.month, jst_dt.day


@dataclass
class User:
    id: str
    name: str
    slack_user_id: Optional[str] = None
    slack_display_name: Optional[str] = None
    contact: Optional[str] = None
    work_type: Optional[str] = None
    transportation_cost: Optional[float] = None
    hourly_wage: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def get_or_create_user(slack_user_id: str, display_name: Optional[str]) -> User:
    sb = get_client()
    # Try by slack_user_id first
    res = sb.table("users").select("*").eq("slack_user_id", slack_user_id).limit(1).execute()
    data = to_record(res) or []
    if data:
        row = data[0]
    else:
        # Fallback: no record -> create
        ins_payload = {
            "name": display_name or slack_user_id,
            "slack_user_id": slack_user_id,
            "slack_display_name": display_name,
        }
        res = sb.table("users").insert(ins_payload).execute()
        items = to_record(res) or []
        row = items[0] if items else {"id": None, **ins_payload}
    return User(**row)


def update_user(user_id: str, payload: dict[str, Any]) -> User:
    sb = get_client()
    res = sb.table("users").update(payload).eq("id", user_id).execute()
    items = to_record(res) or []
    row = items[0] if items else {"id": user_id, **payload}
    return User(**row)


def start_work(user_id: str, start_ts_utc: datetime, comment: str | None = None) -> dict[str, Any]:
    sb = get_client()
    payload = {
        "user_id": user_id,
        "start_time": start_ts_utc.isoformat(),
        "comment": comment,
    }
    res = sb.table("works").insert(payload).execute()
    items = to_record(res) or []
    return items[0] if items else payload


def end_work(user_id: str, end_ts_utc: datetime, break_time_min: int | None = None, comment: str | None = None) -> Optional[dict[str, Any]]:
    sb = get_client()
    # 終了時刻の日付（JST）で該当する作業記録を検索
    jst_date = end_ts_utc.astimezone(JST).date()
    jst_start_of_day = datetime.combine(jst_date, datetime.min.time(), tzinfo=JST).astimezone(timezone.utc)
    jst_end_of_day = datetime.combine(jst_date, datetime.max.time(), tzinfo=JST).astimezone(timezone.utc)

    res = (
        sb.table("works")
        .select("*")
        .eq("user_id", user_id)
        .gte("start_time", jst_start_of_day.isoformat())
        .lte("start_time", jst_end_of_day.isoformat())
        .is_("end_time", None)
        .order("start_time", desc=True)
        .limit(1)
        .execute()
    )
    rows = to_record(res) or []
    if not rows:
        return None
    work_id = rows[0]["id"]

    payload: dict[str, Any] = {"end_time": end_ts_utc.isoformat()}
    if break_time_min is not None:
        payload["break_time"] = break_time_min
    if comment is not None:
        payload["comment"] = comment

    res2 = sb.table("works").update(payload).eq("id", work_id).execute()
    items2 = to_record(res2) or []
    return items2[0] if items2 else {"id": work_id, **payload}


def get_active_work_start_time(user_id: str, end_ts_utc: datetime) -> Optional[datetime]:
    """指定された終了日時の日付で、未完了の作業記録の開始時刻を取得する"""
    sb = get_client()
    jst_date = end_ts_utc.astimezone(JST).date()
    jst_start_of_day = datetime.combine(jst_date, datetime.min.time(), tzinfo=JST).astimezone(timezone.utc)
    jst_end_of_day = datetime.combine(jst_date, datetime.max.time(), tzinfo=JST).astimezone(timezone.utc)

    res = (
        sb.table("works")
        .select("start_time")
        .eq("user_id", user_id)
        .gte("start_time", jst_start_of_day.isoformat())
        .lte("start_time", jst_end_of_day.isoformat())
        .is_("end_time", None)
        .order("start_time", desc=True)
        .limit(1)
        .execute()
    )
    rows = to_record(res) or []
    if not rows:
        return None

    # ISO文字列をdatetimeに変換
    start_time_str = rows[0]["start_time"]
    return datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))


def upsert_attendance(user_id: str, date_utc: datetime, is_attend: bool) -> dict[str, Any]:
    sb = get_client()
    y, m, d = ymd_from_jst(date_utc)
    payload = {
        "user_id": user_id,
        "year": y,
        "month": m,
        "day": d,
        "is_attend": is_attend,
    }
    # upsert by unique constraint
    res = sb.table("attendance").upsert(payload, on_conflict="user_id,year,month,day").execute()
    items = to_record(res) or []
    return items[0] if items else payload


def get_users() -> list[User]:
    sb = get_client()
    res = sb.table("users").select("*").order("name").execute()
    data = to_record(res) or []
    return [User(**row) for row in data]


def get_attendance_between_tue_fri(from_utc: datetime, months_ahead: int = 2) -> list[dict[str, Any]]:
    # Collect dates of Tue/Fri from today to +months_ahead (JST-based days) and query per day
    sb = get_client()
    result: list[dict[str, Any]] = []

    # Roughly 2 months ahead as 62 days window
    end_limit = from_utc + timedelta(days=62)

    cur = from_utc
    while cur <= end_limit:
        # JST weekday
        jst = cur.astimezone(JST)
        if jst.weekday() in (1, 4):  # Tue=1, Fri=4
            y, m, d = jst.year, jst.month, jst.day
            res = (
                sb.table("attendance")
                .select("*")
                .eq("year", y)
                .eq("month", m)
                .eq("day", d)
                .execute()
            )
            day_rows = to_record(res) or []
            for r in day_rows:
                r["_year"], r["_month"], r["_day"] = y, m, d
                result.append(r)
        cur += timedelta(days=1)

    return result


def has_active_work(user_id: str, now_utc: datetime) -> bool:
    """Return True if the user has a work record for JST-today with no end_time."""
    sb = get_client()
    # JST での今日の範囲を計算
    jst_date = now_utc.astimezone(JST).date()
    jst_start_of_day = datetime.combine(jst_date, datetime.min.time(), tzinfo=JST).astimezone(timezone.utc)
    jst_end_of_day = datetime.combine(jst_date, datetime.max.time(), tzinfo=JST).astimezone(timezone.utc)

    res = (
        sb.table("works")
        .select("id")
        .eq("user_id", user_id)
        .gte("start_time", jst_start_of_day.isoformat())
        .lte("start_time", jst_end_of_day.isoformat())
        .is_("end_time", None)
        .limit(1)
        .execute()
    )
    rows = to_record(res) or []
    return bool(rows)


def get_work_hours_by_month(user_id: str, year: int, month: int) -> tuple[list[dict[str, Any]], float]:
    """指定された年月の勤務記録と合計時間を取得（月をまたぐ場合も考慮、未終了も含む）"""
    sb = get_client()

    # JST での月の範囲を計算
    jst_start = datetime(year, month, 1, tzinfo=JST)
    if month == 12:
        jst_end = datetime(year + 1, 1, 1, tzinfo=JST)
    else:
        jst_end = datetime(year, month + 1, 1, tzinfo=JST)

    # UTCに変換
    utc_start = jst_start.astimezone(timezone.utc)
    utc_end = jst_end.astimezone(timezone.utc)

    # 指定月に開始された勤務記録を取得（終了済み・未終了問わず）
    res = (
        sb.table("works")
        .select("*")
        .eq("user_id", user_id)
        .gte("start_time", utc_start.isoformat())
        .lt("start_time", utc_end.isoformat())
        .order("start_time")
        .execute()
    )

    rows = to_record(res) or []
    total_hours = 0.0

    for row in rows:
        if row.get("start_time"):
            start_dt = datetime.fromisoformat(row["start_time"].replace("Z", "+00:00"))

            # 終了時刻がある場合のみ時間計算
            if row.get("end_time"):
                end_dt = datetime.fromisoformat(row["end_time"].replace("Z", "+00:00"))

                # 指定月の範囲内での勤務時間を計算
                # 開始時刻は必ず指定月内（クエリで絞り込み済み）
                # 終了時刻が月をまたぐ場合は、月末までの時間のみ計算
                effective_end = min(end_dt, utc_end.astimezone(timezone.utc))
                work_duration = effective_end - start_dt

                # 休憩時間を差し引く（月をまたぐ場合は比例配分）
                break_minutes = row.get("break_time_min", 0) or 0
                total_duration = end_dt - start_dt
                if total_duration.total_seconds() > 0:
                    break_ratio = work_duration.total_seconds() / total_duration.total_seconds()
                    effective_break_minutes = break_minutes * break_ratio
                else:
                    effective_break_minutes = 0

                work_minutes = work_duration.total_seconds() / 60 - effective_break_minutes
                total_hours += max(0, work_minutes / 60)  # 負の値を防ぐ

    return rows, total_hours


def delete_work_record(work_id: str) -> bool:
    """勤務記録を削除"""
    sb = get_client()
    try:
        res = sb.table("works").delete().eq("id", work_id).execute()
        return True
    except Exception:
        return False
