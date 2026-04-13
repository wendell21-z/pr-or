"""
SQLAlchemy ORM models for the scheduling system.
This project uses two persistence modes:
1. `app_data` for supplemental JSON state such as solve results.
2. Relational tables in `vw_aps_pr` for the core business data.
"""
from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Integer, String, Text, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


class AppData(Base):
    """
    Single-table key-value store.  Each row holds one logical category
    (e.g. "working_times", "lines", "dies", "solve_results" ...)
    as a JSON string in `payload`.
    """
    __tablename__ = "app_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    payload = Column(Text, nullable=False)          # JSON string
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkingTimeRecord(Base):
    __tablename__ = "working_time"

    text = Column(String(255), primary_key=True)
    minutes = Column(Integer)


class DayRecord(Base):
    __tablename__ = "day"

    id = Column(String(255), primary_key=True)
    out_minutes = Column(Integer)
    woking_time = Column(String(255))


class LineRecord(Base):
    __tablename__ = "line"

    id = Column(Integer, primary_key=True)
    code = Column(String(255))
    description = Column(String(255))


class DieRecord(Base):
    __tablename__ = "die"

    id = Column(Integer, primary_key=True)
    akz = Column(Integer)
    line_id = Column(Integer)
    code = Column(String(255))
    name = Column(String(255))


class DunnageRecord(Base):
    __tablename__ = "dunnage"

    id = Column(Integer, primary_key=True)
    capacity = Column(Integer)
    name = Column(String(255))


class PartRecord(Base):
    __tablename__ = "part"

    id = Column(Integer, primary_key=True)
    code = Column(String(255))
    min = Column("min", Integer)
    name = Column(String(255))
    die_id = Column(Integer)
    dunnage_id = Column(Integer)


class CarRecord(Base):
    __tablename__ = "car"

    id = Column(Integer, primary_key=True)
    code = Column(String(255))
    name = Column(String(255))


class CarPartRecord(Base):
    __tablename__ = "car_part"

    id = Column(BigInteger, primary_key=True)
    usage = Column(Integer)
    car_id = Column(Integer)
    part_id = Column(Integer)


class PartInventoryRecord(Base):
    __tablename__ = "part_inventory"

    id = Column(BigInteger, primary_key=True)
    day = Column(Date)
    part_id = Column(Integer)
    quantity = Column(Integer)


class DunnageInventoryHistoryRecord(Base):
    __tablename__ = "dunnage_inventory_history"

    id = Column(Integer, primary_key=True)
    dunnage_id = Column(Integer)
    day = Column(Date)
    empty_quantity = Column(Integer)
    pending_repair_quantity = Column(Integer)
    quantity = Column(Integer)
    repair_quantity = Column(Integer)
    sealed_quantity = Column(Integer)
    welding_quantity = Column(Integer)


class CarUsageRecord(Base):
    __tablename__ = "car_usage"

    id = Column(Integer, primary_key=True)
    usage = Column(Integer)
    car_id = Column(Integer)
    day_id = Column(String(255))


class DieMemoRecord(Base):
    __tablename__ = "die_memo"

    id = Column(BigInteger, primary_key=True)
    content = Column(String(255))
    die_id = Column(Integer)


class TaskRecord(Base):
    __tablename__ = "task"

    id = Column(BigInteger, primary_key=True)
    is_day_pinned = Column(Boolean)
    is_die_pinned = Column(Boolean)
    is_quantity_pinned = Column(Boolean)
    is_seq_pinned = Column(Boolean)
    memo = Column(String(255))
    pinned_type = Column(Integer)
    quantity = Column(Integer)
    seq_in_day = Column(Integer)
    day_id = Column(String(255))
    die_id = Column(Integer)
    priority = Column(Integer)


# ---------------------------------------------------------------------------
# Engine / Session helpers
# ---------------------------------------------------------------------------

def _mysql_url(
    host: str = "localhost",
    port: int = 3306,
    user: str = "root",
    password: str = "",
    database: str = "pr_or",
) -> str:
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def create_engine_from_url(url: str, **kwargs):
    return create_engine(url, pool_pre_ping=True, **kwargs)


def init_db(engine) -> None:
    """Create tables if they don't exist."""
    Base.metadata.create_all(engine)


def get_session_factory(engine):
    return sessionmaker(bind=engine)


# ---------------------------------------------------------------------------
# Convenience CRUD
# ---------------------------------------------------------------------------

def save_kv(session: Session, key: str, payload_dict: dict) -> None:
    import json
    existing = session.query(AppData).filter_by(key=key).first()
    payload_json = json.dumps(payload_dict, ensure_ascii=False, default=str)
    if existing:
        existing.payload = payload_json
        existing.updated_at = datetime.utcnow()
    else:
        session.add(AppData(key=key, payload=payload_json))


def load_kv(session: Session, key: str) -> dict:
    import json
    row = session.query(AppData).filter_by(key=key).first()
    if row is None:
        return {}
    return json.loads(row.payload)


def delete_kv(session: Session, key: str) -> None:
    session.query(AppData).filter_by(key=key).delete()
