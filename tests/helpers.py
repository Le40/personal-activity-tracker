from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TEST_TIMEZONE = ZoneInfo("Europe/Bratislava")

def local_to_utc(value: str) -> datetime:
    local_time = datetime.fromisoformat(value).replace(
        tzinfo=TEST_TIMEZONE
    )

    return local_time.astimezone(timezone.utc).replace(tzinfo=None)