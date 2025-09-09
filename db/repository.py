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


def upsert_attendance(user_id: str, date_utc: datetime, is_attend: bool, start_time: Optional[str] = None) -> dict[str, Any]:
    sb = get_client()
    y, m, d = ymd_from_jst(date_utc)
    payload = {
        "user_id": user_id,
        "year": y,
        "month": m,
        "day": d,
        "is_attend": is_attend,
    }
    # 出勤の場合のみstart_timeを設定
    if is_attend and start_time:
        payload["start_time"] = start_time

    # upsert by unique constraint
    res = sb.table("attendance").upsert(payload, on_conflict="user_id,year,month,day").execute()
    items = to_record(res) or []
    return items[0] if items else payload


def get_users() -> list[User]:
    sb = get_client()
    res = sb.table("users").select("*").order("name").execute()
    data = to_record(res) or []
    return [User(**row) for row in data]


def get_attendance_between_tue_fri(from_utc: datetime, months_ahead: int = 1) -> list[dict[str, Any]]:
    # Collect dates of Tue/Fri from today to +months_ahead (JST-based days) and query per day
    sb = get_client()
    result: list[dict[str, Any]] = []

    # 1 month ahead as 30 days window
    end_limit = from_utc + timedelta(days=30)

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


# ===== チャンネルメモ機能 =====

def save_channel_memo(memo_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    チャンネルメッセージをメモとして保存

    Args:
        memo_data: メモデータ辞書

    Returns:
        保存されたメモデータ、失敗時はNone
    """
    sb = get_client()
    try:
        res = sb.table("channel_memos").insert(memo_data).execute()
        data = to_record(res)
        return data[0] if data else None
    except Exception as e:
        print(f"Error saving channel memo: {e}")
        return None


def search_channel_memos(
    keyword: str,
    channel_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 10
) -> list[dict[str, Any]]:
    """
    チャンネルメモを検索

    Args:
        keyword: 検索キーワード
        channel_id: チャンネルID（指定時はそのチャンネル内のみ検索）
        user_id: ユーザーID（指定時はそのユーザーのメモのみ検索）
        limit: 取得件数制限

    Returns:
        検索結果のメモリスト（新しい順）
    """
    sb = get_client()
    try:
        query = sb.table("channel_memos").select("*")

        # キーワード検索（大文字小文字区別なし）
        query = query.ilike("message", f"%{keyword}%")

        # チャンネル絞り込み
        if channel_id:
            query = query.eq("channel_id", channel_id)

        # ユーザー絞り込み
        if user_id:
            query = query.eq("user_id", user_id)

        # 新しい順でソート、件数制限
        query = query.order("created_at", desc=True).limit(limit)

        res = query.execute()
        return to_record(res) or []

    except Exception as e:
        print(f"Error searching channel memos: {e}")
        return []


def get_recent_channel_memos(
    channel_id: str,
    limit: int = 10
) -> list[dict[str, Any]]:
    """
    チャンネルの最近のメモを取得

    Args:
        channel_id: チャンネルID
        limit: 取得件数制限

    Returns:
        最近のメモリスト（新しい順）
    """
    sb = get_client()
    try:
        query = sb.table("channel_memos").select("*")

        # チャンネル絞り込み
        query = query.eq("channel_id", channel_id)

        # 新しい順でソート、件数制限
        query = query.order("created_at", desc=True).limit(limit)

        res = query.execute()
        return to_record(res) or []

    except Exception as e:
        print(f"Error getting recent channel memos: {e}")
        return []


def get_channel_memo_stats(channel_id: str) -> Optional[dict[str, Any]]:
    """
    チャンネルのメモ統計情報を取得

    Args:
        channel_id: チャンネルID

    Returns:
        統計情報辞書、エラー時はNone
    """
    sb = get_client()
    try:
        # 総メモ数
        count_res = sb.table("channel_memos").select("*", count="exact").eq("channel_id", channel_id).execute()
        total_memos = count_res.count or 0

        if total_memos == 0:
            return None

        # 最初と最後のメモ日時
        first_res = sb.table("channel_memos").select("created_at").eq("channel_id", channel_id).order("created_at", desc=False).limit(1).execute()
        last_res = sb.table("channel_memos").select("created_at").eq("channel_id", channel_id).order("created_at", desc=True).limit(1).execute()

        first_data = to_record(first_res)
        last_data = to_record(last_res)

        first_memo_date = "不明"
        last_memo_date = "不明"

        if first_data:
            first_dt = datetime.fromisoformat(first_data[0]["created_at"].replace("Z", "+00:00"))
            first_memo_date = first_dt.astimezone(JST).strftime("%Y/%m/%d")

        if last_data:
            last_dt = datetime.fromisoformat(last_data[0]["created_at"].replace("Z", "+00:00"))
            last_memo_date = last_dt.astimezone(JST).strftime("%Y/%m/%d")

        # ユーザー別メモ数（上位ユーザー）
        # Supabaseでは集計が制限されるため、Pythonで処理
        all_memos_res = sb.table("channel_memos").select("user_id, user_name").eq("channel_id", channel_id).execute()
        all_memos = to_record(all_memos_res) or []

        # ユーザー別カウント
        user_counts = {}
        unique_users = set()

        for memo in all_memos:
            user_id = memo["user_id"]
            user_name = memo["user_name"]
            unique_users.add(user_id)

            if user_id not in user_counts:
                user_counts[user_id] = {"user_name": user_name, "memo_count": 0}
            user_counts[user_id]["memo_count"] += 1

        # 上位ユーザーをソート
        top_users = sorted(user_counts.values(), key=lambda x: x["memo_count"], reverse=True)

        # 今日のメモ数を計算
        now_utc = utc_now()
        jst_today = now_utc.astimezone(JST).date()
        today_start = datetime.combine(jst_today, datetime.min.time(), tzinfo=JST).astimezone(timezone.utc)
        today_end = datetime.combine(jst_today, datetime.max.time(), tzinfo=JST).astimezone(timezone.utc)

        today_res = (
            sb.table("channel_memos")
            .select("*", count="exact")
            .eq("channel_id", channel_id)
            .gte("created_at", today_start.isoformat())
            .lte("created_at", today_end.isoformat())
            .execute()
        )
        today_memos = today_res.count or 0

        # 今週のメモ数を計算（月曜日開始）
        jst_now = now_utc.astimezone(JST)
        days_since_monday = jst_now.weekday()  # 0=月曜日
        week_start = datetime.combine(
            jst_today - timedelta(days=days_since_monday),
            datetime.min.time(),
            tzinfo=JST
        ).astimezone(timezone.utc)

        week_res = (
            sb.table("channel_memos")
            .select("*", count="exact")
            .eq("channel_id", channel_id)
            .gte("created_at", week_start.isoformat())
            .execute()
        )
        week_memos = week_res.count or 0

        # 今月のメモ数を計算
        month_start = datetime.combine(
            jst_today.replace(day=1),
            datetime.min.time(),
            tzinfo=JST
        ).astimezone(timezone.utc)

        month_res = (
            sb.table("channel_memos")
            .select("*", count="exact")
            .eq("channel_id", channel_id)
            .gte("created_at", month_start.isoformat())
            .execute()
        )
        month_memos = month_res.count or 0

        # ユーザーランキング用のデータを準備
        user_rankings = []
        for user_id, user_data in user_counts.items():
            user_rankings.append({
                "user_id": user_id,
                "user_name": user_data["user_name"],
                "memo_count": user_data["memo_count"]
            })

        # メモ数でソート
        user_rankings.sort(key=lambda x: x["memo_count"], reverse=True)

        return {
            "total_memos": total_memos,
            "today_memos": today_memos,
            "week_memos": week_memos,
            "month_memos": month_memos,
            "unique_users": len(unique_users),
            "first_memo_date": first_memo_date,
            "last_memo_date": last_memo_date,
            "top_users": top_users,
            "user_rankings": user_rankings
        }

    except Exception as e:
        print(f"Error getting channel memo stats: {e}")
        return None


def get_recent_memos(channel_id: str, days: int = 7, limit: int = 20) -> list[dict[str, Any]]:
    """
    指定期間の最近のメモを取得

    Args:
        channel_id: チャンネルID
        days: 過去何日分を取得するか
        limit: 最大取得件数

    Returns:
        最近のメモリスト（新しい順）
    """
    sb = get_client()
    try:
        # 指定日数前の日時を計算
        since_date = utc_now() - timedelta(days=days)
        since_str = since_date.isoformat()

        query = sb.table("channel_memos").select("*")
        query = query.eq("channel_id", channel_id)
        query = query.gte("created_at", since_str)
        query = query.order("created_at", desc=True).limit(limit)

        res = query.execute()
        return to_record(res) or []

    except Exception as e:
        print(f"Error getting recent memos: {e}")
        return []


# ===== タスク管理機能 =====

def save_channel_task(task_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    チャンネルタスクを保存

    Args:
        task_data: タスクデータ辞書

    Returns:
        保存されたタスクデータ、失敗時はNone
    """
    sb = get_client()
    try:
        res = sb.table("channel_tasks").insert(task_data).execute()
        data = to_record(res)
        return data[0] if data else None
    except Exception as e:
        print(f"Error saving channel task: {e}")
        return None


def get_channel_tasks(
    channel_id: str,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50
) -> list[dict[str, Any]]:
    """
    チャンネルのタスク一覧を取得

    Args:
        channel_id: チャンネルID
        status: タスクステータス（'pending', 'completed', 'cancelled'）
        user_id: ユーザーID（指定時はそのユーザーのタスクのみ）
        limit: 取得件数制限

    Returns:
        タスクリスト（新しい順）
    """
    sb = get_client()
    try:
        query = sb.table("channel_tasks").select("*")
        query = query.eq("channel_id", channel_id)

        if status:
            query = query.eq("status", status)

        if user_id:
            query = query.eq("user_id", user_id)

        query = query.order("created_at", desc=True).limit(limit)

        res = query.execute()
        return to_record(res) or []

    except Exception as e:
        print(f"Error getting channel tasks: {e}")
        return []


def update_task_status(
    task_id: str,
    status: str,
    completed_at: Optional[datetime] = None
) -> bool:
    """
    タスクのステータスを更新

    Args:
        task_id: タスクID
        status: 新しいステータス
        completed_at: 完了日時（completed時のみ）

    Returns:
        更新成功時True
    """
    sb = get_client()
    try:
        update_data = {
            "status": status,
            "updated_at": utc_now().isoformat()
        }

        if status == "completed" and completed_at:
            update_data["completed_at"] = completed_at.isoformat()

        res = sb.table("channel_tasks").update(update_data).eq("id", task_id).execute()
        return len(to_record(res) or []) > 0

    except Exception as e:
        print(f"Error updating task status: {e}")
        return False


def update_task_content(task_id: str, task_name: str, description: str = None) -> bool:
    """
    タスクの内容を更新

    Args:
        task_id: タスクID
        task_name: 新しいタスク名
        description: 新しい説明

    Returns:
        更新成功時True
    """
    sb = get_client()
    try:
        update_data = {
            "task_name": task_name,
            "updated_at": utc_now().isoformat()
        }

        if description is not None:
            update_data["description"] = description

        res = sb.table("channel_tasks").update(update_data).eq("id", task_id).execute()
        return len(to_record(res) or []) > 0

    except Exception as e:
        print(f"Error updating task content: {e}")
        return False


def delete_task(task_id: str) -> bool:
    """
    タスクを削除

    Args:
        task_id: タスクID

    Returns:
        削除成功時True
    """
    sb = get_client()
    try:
        res = sb.table("channel_tasks").delete().eq("id", task_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting task: {e}")
        return False


def get_task_by_id(task_id: str) -> Optional[dict[str, Any]]:
    """
    IDでタスクを取得

    Args:
        task_id: タスクID

    Returns:
        タスクデータ、見つからない場合はNone
    """
    sb = get_client()
    try:
        res = sb.table("channel_tasks").select("*").eq("id", task_id).single().execute()
        return to_record(res) if res.data else None
    except Exception as e:
        print(f"Error getting task by id: {e}")
        return None


def get_all_channel_memos(channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """
    チャンネルの全メモを取得（一覧表示用）

    Args:
        channel_id: チャンネルID
        limit: 取得件数制限

    Returns:
        メモリスト（新しい順）
    """
    sb = get_client()
    try:
        query = sb.table("channel_memos").select("*")
        query = query.eq("channel_id", channel_id)
        query = query.order("created_at", desc=True).limit(limit)

        res = query.execute()
        return to_record(res) or []

    except Exception as e:
        print(f"Error getting all channel memos: {e}")
        return []


def get_channel_memo_by_id(memo_id: str) -> Optional[dict[str, Any]]:
    """
    IDによるメモの取得

    Args:
        memo_id: メモID（UUID文字列）

    Returns:
        メモデータ、見つからない場合はNone
    """
    sb = get_client()
    try:
        # UUIDの形式をチェック
        import uuid
        try:
            uuid.UUID(memo_id)
        except ValueError:
            print(f"Error: Invalid UUID format: {memo_id}")
            return None

        res = sb.table("channel_memos").select("*").eq("id", memo_id).execute()
        data = to_record(res) or []
        return data[0] if data else None
    except Exception as e:
        print(f"Error getting memo by id: {e}")
        return None


def update_channel_memo(memo_id: str, new_message: str) -> bool:
    """
    メモの更新

    Args:
        memo_id: メモID（UUID文字列）
        new_message: 新しいメッセージ内容

    Returns:
        更新成功時はTrue、失敗時はFalse
    """
    sb = get_client()
    try:
        # UUIDの形式をチェック
        import uuid
        try:
            uuid.UUID(memo_id)
        except ValueError:
            print(f"Error: Invalid UUID format: {memo_id}")
            return False

        res = sb.table("channel_memos").update({
            "message": new_message,
            "updated_at": "now()"
        }).eq("id", memo_id).execute()
        return len(to_record(res) or []) > 0
    except Exception as e:
        print(f"Error updating memo: {e}")
        return False


def delete_channel_memo(memo_id: str) -> bool:
    """
    メモの削除

    Args:
        memo_id: メモID（UUID文字列）

    Returns:
        削除成功時はTrue、失敗時はFalse
    """
    sb = get_client()
    try:
        # UUIDの形式をチェック
        import uuid
        try:
            uuid.UUID(memo_id)
        except ValueError:
            print(f"Error: Invalid UUID format: {memo_id}")
            return False

        res = sb.table("channel_memos").delete().eq("id", memo_id).execute()
        return len(to_record(res) or []) > 0
    except Exception as e:
        print(f"Error deleting memo: {e}")
        return False
