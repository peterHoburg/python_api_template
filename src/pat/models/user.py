"""User model for the application."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from pat.models.base import Base


class User(Base):
    """User model representing application users.

    Attributes:
        id: Unique identifier for the user (inherited from Base)
        first_name: User's first name
        last_name: User's last name
        email: User's email address (unique)
        created_at: Timestamp when the user was created (inherited from Base)
        updated_at: Timestamp when the user was last updated (inherited from Base)

    """

    # Use the automatic table name generation from Base class
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(300), unique=True)

    def __repr__(self) -> str:
        """Return a string representation of the User.

        Returns:
            A string representation of the User

        """
        return f"User(id={self.id!r}, name={self.first_name!r}, fullname={self.last_name!r})"
