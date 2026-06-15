import datetime
from typing import Any

from models import db, Day, WorkingTime


def ensure_default_working_time(text: str) -> WorkingTime:
    """Ensure a WorkingTime row exists for the given text.
    Returns the WorkingTime instance.
    """
    entity = db.session.get(WorkingTime, text)
    if entity is None:
        minutes = 8 * 60 if text == "8+0" else 0
        entity = WorkingTime(text=text, minutes=minutes)
        db.session.add(entity)
        db.session.flush()
    return entity


def ensure_day(day: Any) -> Day:
    """Ensure a Day row exists for the given date-like value and return it.

    Accepts datetime.date, datetime.datetime, or ISO date string (YYYY-MM-DD).
    """
    if isinstance(day, datetime.datetime):
        d = day.date()
    elif isinstance(day, str):
        # accept strings like 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS'
        try:
            d = datetime.date.fromisoformat(day[:10])
        except Exception:
            # fallback: use the raw string as id
            d = None
    else:
        d = day

    day_id = d.isoformat() if isinstance(d, datetime.date) else str(day)
    entity = db.session.get(Day, day_id)
    if entity is None:
        # default working time: weekdays 8+0, weekends 0
        working_time_text = "8+0" if isinstance(d, datetime.date) and d.weekday() < 5 else "0"
        ensure_default_working_time(working_time_text)
        entity = Day(id=day_id, out_minutes=0, woking_time=working_time_text)
        db.session.add(entity)
        db.session.flush()
    return entity
