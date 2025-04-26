from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from pat.models.base import Base


class User(Base):
    # Use the automatic table name generation from Base class
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(300), unique=True)

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.first_name!r}, fullname={self.last_name!r})"
