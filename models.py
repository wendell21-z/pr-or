import datetime
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import BigInteger, DateTime, ForeignKeyConstraint, Index, Integer, String, Text
from sqlalchemy.dialects.mysql import BIT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class AppData(Base):
    __tablename__ = 'app_data'
    __table_args__ = (
        Index('ix_app_data_key', 'key', unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64, 'utf8mb4_general_ci'), nullable=False)
    payload: Mapped[str] = mapped_column(Text(collation='utf8mb4_general_ci'), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)


class Car(Base):
    __tablename__ = 'car'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))
    name: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))


class CarPart(Base):
    __tablename__ = 'car_part'
    __table_args__ = (
        Index('UKgw1jqsi5na4agpwka28p9bm5q', 'car_id', 'part_id', unique=True),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usage: Mapped[Optional[int]] = mapped_column(Integer)
    car_id: Mapped[Optional[int]] = mapped_column(Integer)
    part_id: Mapped[Optional[int]] = mapped_column(Integer)


class CarUsage(Base):
    __tablename__ = 'car_usage'
    __table_args__ = (
        Index('UKtixc4n30xasel7q3v3of5ix5l', 'car_id', 'day_id', unique=True),
    )
    usage: Mapped[Optional[int]] = mapped_column(Integer)
    car_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_id: Mapped[str] = mapped_column(String(255, 'utf8mb4_general_ci'), primary_key=True)

class Day(Base):
    __tablename__ = 'day'

    id: Mapped[str] = mapped_column(String(255, 'utf8mb4_general_ci'), primary_key=True)
    out_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    woking_time: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))

    def to_dict(self):
        return {
            "id": self.id,
            "out_minutes": self.out_minutes,
            "woking_time": self.woking_time
        }

class Die(Base):
    __tablename__ = 'die'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    akz: Mapped[Optional[int]] = mapped_column(Integer)
    line_id: Mapped[Optional[int]] = mapped_column(Integer)
    code: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))
    name: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))

class DieMemo(Base):
    __tablename__ = 'die_memo'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    content: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))
    die_id: Mapped[Optional[int]] = mapped_column(Integer)

class Dunnage(Base):
    __tablename__ = 'dunnage'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    capacity: Mapped[Optional[int]] = mapped_column(Integer)
    name: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))

class DunnageInventoryHistory(Base):
    __tablename__ = 'dunnage_inventory_history'

    dunnage_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_id: Mapped[str] = mapped_column(String(255, 'utf8mb4_general_ci'), primary_key=True)
    empty_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    pending_repair_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    quantity: Mapped[Optional[int]] = mapped_column(Integer)
    repair_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    sealed_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    welding_quantity: Mapped[Optional[int]] = mapped_column(Integer)

class Line(Base):
    __tablename__ = 'line'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))
    description: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))

class Part(Base):
    __tablename__ = 'part'
    __table_args__ = (
        Index('unique_code', 'id', 'code', unique=True),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))
    min: Mapped[Optional[int]] = mapped_column(Integer)
    name: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))
    die_id: Mapped[Optional[int]] = mapped_column(Integer)
    dunnage_id: Mapped[Optional[int]] = mapped_column(Integer)

class PartInventory(Base):
    __tablename__ = 'part_inventory'
    day_id: Mapped[str] = mapped_column(String(255, 'utf8mb4_general_ci'), primary_key=True)
    part_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer)


class WorkingTime(Base):
    __tablename__ = 'working_time'
    text: Mapped[str] = mapped_column(String(255, 'utf8mb4_general_ci'), primary_key=True)
    minutes: Mapped[Optional[int]] = mapped_column(Integer)

class Task(Base):
    __tablename__ = 'task'
    __table_args__ = (
        ForeignKeyConstraint(['day_id'], ['day.id'], name='FKc7x3d4hql0uqn3ibkh66cn325'),
        ForeignKeyConstraint(['die_id'], ['planning_die.id'], name='FK216d22r6e0att5kp4hd0vgffc'),
        Index('FK216d22r6e0att5kp4hd0vgffc', 'die_id'),
        Index('FKc7x3d4hql0uqn3ibkh66cn325', 'day_id'),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    is_day_pinned: Mapped[Optional[int]] = mapped_column(BIT(1))
    is_die_pinned: Mapped[Optional[int]] = mapped_column(BIT(1))
    is_quantity_pinned: Mapped[Optional[int]] = mapped_column(BIT(1))
    is_seq_pinned: Mapped[Optional[int]] = mapped_column(BIT(1))
    memo: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))
    pinned_type: Mapped[Optional[int]] = mapped_column(Integer)
    quantity: Mapped[Optional[int]] = mapped_column(Integer)
    seq_in_day: Mapped[Optional[int]] = mapped_column(Integer)
    day_id: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_general_ci'))
    die_id: Mapped[Optional[int]] = mapped_column(Integer)
    priority: Mapped[Optional[int]] = mapped_column(Integer)