import os
from typing import Any, Optional

from supabase import create_client, Client


_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment")

    _client = create_client(url, key)
    return _client


def to_record(res: Any) -> Any:
    """Normalize supabase-py v2 response data."""
    return getattr(res, "data", res)
