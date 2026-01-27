from datetime import datetime
import re
from typing import Optional
from app.sandbox.sub_query.getLastUser import GetLatestPeriodForUser


def _ResolvePeriodFromText(period_text: Optional[str], user_id: str) -> Optional[str]:
    if not period_text:
        return GetLatestPeriodForUser(user_id)
    text = period_text.strip()
    if text.lower() in {"this_month", "이번달", "이번 달"}:
        now = datetime.utcnow()
        return f"{now.year:04d}-{now.month:02d}"
    year_match = re.search(r"(\d{4})", text)
    month_match = re.search(r"(\d{1,2})\s*월", text)
    if year_match or month_match:
        year = int(year_match.group(1)) if year_match else None
        month = int(month_match.group(1)) if month_match else None
        if month is not None and 1 <= month <= 12:
            if year is None:
                latest = GetLatestPeriodForUser(user_id)
                if latest and re.match(r"\d{4}-\d{2}", latest):
                    year = int(latest.split("-")[0])
                else:
                    year = datetime.utcnow().year
            return f"{year:04d}-{month:02d}"
    standard_match = re.search(r"(\d{4})\s*[-/.]\s*(\d{1,2})", text)
    if standard_match:
        year = int(standard_match.group(1))
        month = int(standard_match.group(2))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"
    return GetLatestPeriodForUser(user_id)