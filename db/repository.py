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
    contact: Optional[str] = None
    work_type: Optional[str] = None
    transportation_cost: Optional[float] = None
    hourly_wage: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def get_or_create_user_by_name(name: str) -> User:
    sb = get_client()
    res = sb.table("users").select("*").eq("name", name).limit(1).execute()
    data = to_record(res) or []
    if data:
        row = data[0]
    else:
        res = sb.table("users").insert({"name": name}).execute()
        items = to_record(res) or []
        row = items[0] if items else {"id": None, "name": name}
    return User(**row)


def update_user(user_id: str, payload: dict[str, Any]) -> User:
    sb = get_client()
    res = sb.table("users").update(payload).eq("id", user_id).execute()
    items = to_record(res) or []
    row = items[0] if items else {"id": user_id, **payload}
    return User(**row)


def start_work(user_id: str, start_ts_utc: datetime, comment: str | None = None) -> dict[str, Any]:
    sb = get_client()
    y, m, d = ymd_from_jst(start_ts_utc)
    payload = {
        "user_id": user_id,
        "year": y,
        "month": m,
        "day": d,
        "start_time": start_ts_utc.isoformat(),
        "comment": comment,
    }
    res = sb.table("works").insert(payload).execute()
    items = to_record(res) or []
    return items[0] if items else payload


def end_work(user_id: str, end_ts_utc: datetime, break_time_min: int | None = None) -> Optional[dict[str, Any]]:
    sb = get_client()
    y, m, d = ymd_from_jst(end_ts_utc)
    # 最新の start を取得（当日）
    res = (
        sb.table("works")
        .select("*")
        .eq("user_id", user_id)
        .eq("year", y)
        .eq("month", m)
        .eq("day", d)
    .is_("end_time", "null")
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

    res2 = sb.table("works").update(payload).eq("id", work_id).execute()
    items2 = to_record(res2) or []
    return items2[0] if items2 else {"id": work_id, **payload}


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
