from datetime import UTC, datetime
from zoneinfo import ZoneInfo

TEST_TIMEZONE = ZoneInfo("Europe/Bratislava")

def local_to_utc(value: str) -> datetime:
    local_time = datetime.fromisoformat(value).replace(
        tzinfo=TEST_TIMEZONE
    )

    return local_time.astimezone(UTC).replace(tzinfo=None)