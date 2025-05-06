"""User model for the application."""

from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pat.models.base import Base
from pat.models.role import Permission, Role, user_role


class User(Base):
    """User model representing application users.

    Attributes:
        id: Unique identifier for the user (inherited from Base)
        first_name: User's first name
        last_name: User's last name
        email: User's email address (unique)
        roles: Set of roles assigned to this user
        created_at: Timestamp when the user was created (inherited from Base)
        updated_at: Timestamp when the user was last updated (inherited from Base)

    """

    # Use the automatic table name generation from Base class
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(300), unique=True)

    # Define the relationship to roles
    roles: Mapped[set[Role]] = relationship(
        secondary=user_role,
        back_populates="users",
        collection_class=set,
    )

    def __repr__(self) -> str:
        """Return a string representation of the User.

        Returns:
            A string representation of the User

        """
        return f"User(id={self.id!r}, name={self.first_name!r}, fullname={self.last_name!r})"

    def add_role(self, role: Role) -> None:
        """Add a role to this user.

        Args:
            role: The role to add

        """
        self.roles.add(role)

    def remove_role(self, role: Role) -> None:
        """Remove a role from this user.

        Args:
            role: The role to remove

        """
        if role in self.roles:
            self.roles.remove(role)

    def has_role(self, role: Role) -> bool:
        """Check if this user has a specific role.

        Args:
            role: The role to check

        Returns:
            True if the user has the role, False otherwise

        """
        return role in self.roles

    async def has_permission(self, session: AsyncSession, permission: Permission) -> bool:
        """Check if this user has a specific permission through any of their roles.

        Args:
            session: The database session
            permission: The permission to check

        Returns:
            True if the user has the permission, False otherwise

        """
        for role in self.roles:
            if await role.has_permission(session, permission):
                return True
        return False
