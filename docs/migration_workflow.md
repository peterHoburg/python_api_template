# Database Migration Workflow

## Overview

This document describes the workflow for managing database migrations in the Python API Template (PAT) project. The project uses [Alembic](https://alembic.sqlalchemy.org/en/latest/) for database migrations, which is a lightweight database migration tool for SQLAlchemy.

Alembic provides the following features:
- Database schema version control
- Upgrade and downgrade operations
- Automatic migration script generation
- Support for manual migration script editing
- Transaction management for safe migrations

## Setup

The project has already been configured with Alembic. The configuration includes:

- `alembic.ini`: The main configuration file for Alembic
- `alembic/`: Directory containing the Alembic environment and migration scripts
  - `env.py`: Environment configuration for running migrations
  - `script.py.mako`: Template for generating new migration scripts
  - `versions/`: Directory containing the migration scripts

The database connection is configured using `SETTINGS.postgres_uri` from `pat.config`, which allows for environment-specific database connections.

## Creating New Migrations

### Automatic Migration Generation

Alembic can automatically generate migration scripts by comparing the current database schema with the SQLAlchemy model definitions. This is the recommended approach for most changes.

To generate a new migration script:

```bash
alembic revision --autogenerate -m "Description of the changes"
```

This command will:
1. Connect to the database
2. Compare the current database schema with the SQLAlchemy models
3. Generate a new migration script in the `alembic/versions/` directory

### Manual Migration Creation

For more complex changes or when you need more control over the migration, you can create a blank migration script:

```bash
alembic revision -m "Description of the changes"
```

This will create a new migration script with empty `upgrade()` and `downgrade()` functions that you can fill in manually.

### Migration Script Structure

Each migration script contains:

1. Metadata about the migration (revision ID, dependencies, etc.)
2. An `upgrade()` function that applies the changes
3. A `downgrade()` function that reverts the changes

Example:

```python
"""Description of the changes

Revision ID: a1b2c3d4e5f6
Revises: previous_revision_id
Create Date: 2023-01-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "previous_revision_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Implementation of the changes
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Implementation to revert the changes
    pass
```

## Applying Migrations

### Upgrading the Database

To apply all pending migrations:

```bash
alembic upgrade head
```

This will apply all migrations that haven't been applied yet, in the correct order.

To apply a specific number of migrations:

```bash
alembic upgrade +n  # where n is the number of migrations to apply
```

To upgrade to a specific revision:

```bash
alembic upgrade revision_id
```

### Downgrading the Database

To revert the most recent migration:

```bash
alembic downgrade -1
```

To revert to a specific revision:

```bash
alembic downgrade revision_id
```

To revert all migrations:

```bash
alembic downgrade base
```

## Checking Migration Status

### Current Revision

To see the current revision of the database:

```bash
alembic current
```

### Migration History

To see the migration history:

```bash
alembic history
```

To see a detailed history with more information:

```bash
alembic history --verbose
```

### Pending Migrations

To see what migrations are pending:

```bash
alembic history --indicate-current
```

## Best Practices

### General Guidelines

1. **One change per migration**: Each migration should make a single logical change to the database schema. This makes it easier to understand, test, and revert if necessary.

2. **Always include downgrade operations**: Even if you don't plan to downgrade in production, including downgrade operations makes testing easier and provides a safety net.

3. **Test migrations before applying to production**: Always test migrations in a development or staging environment before applying them to production.

4. **Use transactions**: Alembic uses transactions by default, which ensures that migrations are atomic (all changes are applied or none are).

5. **Version control your migrations**: Migration scripts should be committed to version control along with the code changes that require them.

### Data Migrations

When performing data migrations (moving or transforming existing data):

1. **Separate schema changes from data changes**: First make the schema changes, then perform the data migration in a separate step.

2. **Consider performance implications**: Large data migrations can be slow and resource-intensive. Consider batching or performing them during off-peak hours.

3. **Ensure data integrity**: Include validation steps to ensure data integrity before and after the migration.

### Common Patterns

1. **Adding a column**:
   ```python
   op.add_column('table_name', sa.Column('column_name', sa.String(50), nullable=False, server_default='default_value'))
   ```

2. **Removing a column**:
   ```python
   op.drop_column('table_name', 'column_name')
   ```

3. **Creating a table**:
   ```python
   op.create_table(
       'table_name',
       sa.Column('id', sa.Integer(), nullable=False),
       sa.Column('name', sa.String(length=100), nullable=False),
       sa.PrimaryKeyConstraint('id'),
   )
   ```

4. **Dropping a table**:
   ```python
   op.drop_table('table_name')
   ```

5. **Adding an index**:
   ```python
   op.create_index('ix_table_name_column_name', 'table_name', ['column_name'])
   ```

6. **Adding a foreign key**:
   ```python
   op.add_column('child_table', sa.Column('parent_id', sa.Integer(), nullable=True))
   op.create_foreign_key('fk_child_parent', 'child_table', 'parent_table', ['parent_id'], ['id'])
   ```

## Troubleshooting

### Common Issues

1. **Migration conflicts**: If multiple developers create migrations simultaneously, conflicts can occur. Resolve these by:
   - Reviewing both migrations to understand the changes
   - Merging the changes into a single migration if possible
   - Adjusting the `down_revision` to create a proper sequence

2. **Failed migrations**: If a migration fails partway through, the database may be in an inconsistent state. Alembic uses transactions to prevent this, but if a migration is too complex or contains non-transactional operations, issues can occur. To recover:
   - Check the error message to understand what failed
   - Fix the issue in the migration script
   - If necessary, manually adjust the database to a consistent state
   - Run `alembic current` to see the current state
   - Continue the migration process

3. **Autogenerate missing changes**: Alembic's autogenerate feature may not detect all changes, particularly:
   - Changes to constraints that aren't explicitly named
   - Changes to indexes that aren't explicitly named
   - Custom column types
   - Some database-specific features

   Always review autogenerated migrations carefully and add any missing operations.

### Getting Help

If you encounter issues with migrations:

1. Check the [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/)
2. Review the error messages carefully
3. Consult with the team for project-specific migration patterns
4. Consider creating a test database to experiment with migrations safely

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/en/latest/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/en/latest/)
- [Project Database Models](src/pat/models/)