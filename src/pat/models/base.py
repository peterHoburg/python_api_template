"""Base model classes for SQLAlchemy models."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Define naming convention for constraints
convention: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Create metadata with naming convention
metadata = MetaData(naming_convention=convention)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models.

    This class provides common attributes and methods for all models.
    """

    # Use the metadata with naming convention
    metadata = metadata

    # No class variable type annotations needed

    # Define common columns for all models
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Generate the table name automatically from the class name.

        Returns:
            str: The table name in snake_case

        """
        # Convert CamelCase to snake_case
        name = cls.__name__
        return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")

    def to_dict(self) -> dict[str, Any]:
        """Convert the model instance to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the model

        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Base":
        """Create a model instance from a dictionary.

        Args:
            data: A dictionary with model attributes

        Returns:
            Base: A new model instance

        """
        return cls(**{k: v for k, v in data.items() if k in [c.name for c in cls.__table__.columns]})
