"""
SQLAlchemy database schemas for coffee shop application.

Defines ORM models for transactions, products, stores, nutritional information,
and session tracing with full schema documentation.
"""

import uuid
from datetime import datetime, time

from sqlalchemy import Integer, UUID, JSON, ARRAY
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    declared_attr
)
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models with async support."""
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name with '_t' suffix."""
        return f"{cls.__name__.lower()}_t"

class Transactions(Base):
    """Stores all transaction records for product sales across stores"""

    __tablename__ = "transactions_t"
    __table_args__ = {"comment": "Transaction records for all store sales"}

    transaction_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for each transaction"
    )
    transaction_date: Mapped[datetime] = mapped_column(
        comment="Date when the transaction occurred"
    )
    transaction_time: Mapped[time] = mapped_column(
        comment="Time when the transaction occurred"
    )
    transaction_qty: Mapped[int] = mapped_column(
        comment="Quantity of products sold in this transaction"
    )
    store_id: Mapped[int] = mapped_column(
        comment="Foreign key reference to the store where transaction occurred"
    )
    product_id: Mapped[int] = mapped_column(
        comment="Foreign key reference to the product sold"
    )
    unit_price: Mapped[float] = mapped_column(
        comment="Price per unit of the product at time of transaction"
    )

class Products(Base):
    """Product catalog containing all available products"""

    __tablename__ = "products_t"
    __table_args__ = {"comment": "Product catalog with product information"}

    product_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for each product"
    )
    product_name: Mapped[str] = mapped_column(
        comment="Name of the product"
    )

class Stores(Base):
    """Store locations and management information"""

    __tablename__ = "stores_t"
    __table_args__ = {"comment": "Store locations with manager and address details"}

    store_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier for each store"
    )
    store_name: Mapped[str] = mapped_column(
        comment="Name of the store"
    )
    city: Mapped[str] = mapped_column(
        comment="City where the store is located"
    )
    address: Mapped[str] = mapped_column(
        comment="Street address of the store"
    )
    manager: Mapped[str] = mapped_column(
        comment="Name of the store manager"
    )

class Nutritions(Base):
    """Nutritional information for products"""

    __tablename__ = "nutritions_t"
    __table_args__ = {"comment": "Nutritional facts and values for each product"}

    product_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique identifier linking to product"
    )
    calories: Mapped[int] = mapped_column(
        comment="Calorie content per serving"
    )
    fat: Mapped[int] = mapped_column(
        comment="Fat content in grams per serving"
    )
    carb: Mapped[int] = mapped_column(
        comment="Carbohydrate content in grams per serving"
    )
    fiber: Mapped[int] = mapped_column(
        comment="Fiber content in grams per serving"
    )
    sodium: Mapped[int] = mapped_column(
        comment="Sodium content in milligrams per serving"
    )

class SessionTracing(Base):
    """Agentic session information"""

    __tablename__ = "service__session_tracing_t"
    __table_args__ = {"comment": "Technical table for agent tracing."}

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        comment="Unique identifier for each session"
    )
    session_history: Mapped[list[dict]] = mapped_column(
        ARRAY(JSON),
        comment="History of the session"
    )

meta = Base.metadata
