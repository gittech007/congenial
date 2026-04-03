from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    us_states: Mapped[list[USState]] = relationship("USState", back_populates="country")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="country")

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix})"


class USState(Base):
    __tablename__ = "us_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("countries.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    country: Mapped[Country] = relationship("Country", back_populates="us_states")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="us_state")

    def __str__(self) -> str:
        return self.name


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    ram_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False)
    ssd_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="plan")

    def __str__(self) -> str:
        return self.name


class OSOption(Base):
    __tablename__ = "os_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="os_option")

    def __str__(self) -> str:
        return self.name


class Validity(Base):
    __tablename__ = "validities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="validity")

    def __str__(self) -> str:
        return self.label
