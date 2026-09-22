"""Shared local trial allowance. Counts attempts, not token billing."""
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from .storage import private_root


class BudgetExceededError(RuntimeError):
    pass


def allowance(*, consume: bool = False) -> dict[str, int]:
    limit = int(os.getenv("YIDUO_AI_DAILY_LIMIT", "20"))
    if limit < 0:
        raise ValueError("YIDUO_AI_DAILY_LIMIT must be nonnegative")
    root = private_root()
    root.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    connection = sqlite3.connect(root / "ai_budget.db", timeout=10)
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS daily_usage (day TEXT PRIMARY KEY, used INTEGER NOT NULL)")
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT used FROM daily_usage WHERE day=?", (day,)).fetchone()
        used = row[0] if row else 0
        if consume:
            if used >= limit:
                raise BudgetExceededError("今日本站 AI 额度已用完，可继续使用基础备课。")
            used += 1
            connection.execute(
                "INSERT INTO daily_usage(day, used) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET used=excluded.used",
                (day, used),
            )
        connection.commit()
        return {"daily_limit": limit, "used": used, "remaining": max(0, limit - used)}
    finally:
        connection.close()
