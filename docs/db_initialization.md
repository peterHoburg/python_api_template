# Database Initialization Process

## Overview

This document describes the database initialization process for the Python API Template (PAT) project. The project provides utilities for initializing and seeding the database, ensuring that the database is ready for use in any environment.

The database initialization process includes:
1. Creating the database if it doesn't exist
2. Applying all pending migrations
3. Seeding the database with environment-specific data

All operations are designed to be idempotent, meaning they can be safely run multiple times without causing issues.

## Command-Line Usage

The project provides several Makefile commands for database initialization:

### Initialize the Database

```bash
make db-init
```

This command:
1. Creates the database if it doesn't exist
2. Applies all pending migrations

### Seed the Database

```bash
make db-seed
```

This command seeds the database with environment-specific data. The data seeded depends on the current environment (development, testing, or production).

### Initialize and Seed the Database

```bash
make db-setup
```

This command performs both initialization and seeding in one step.

## Programmatic Usage

The database initialization utilities can also be used programmatically in your application code.

### Initialize the Database

```python
from pat.utils.db_init import initialize_database

async def setup_db():
    # Initialize the database (create if needed and apply migrations)
    initialized = await initialize_database()
    if initialized:
        print("Database was initialized")
    else:
        print("Database was already initialized, no changes made")
```

### Seed the Database

```python
from pat.utils.db_init import seed_database

async def seed_db():
    # Seed the database with environment-specific data
    seeded = await seed_database()
    if seeded:
        print("Database was seeded")
    else:
        print("No seed function found for the current environment or data already exists")
```

### Initialize and Seed the Database

```python
from pat.utils.db_init import initialize_and_seed_database

async def setup_and_seed_db():
    # Initialize and seed the database
    changes_made = await initialize_and_seed_database()
    if changes_made:
        print("Database was initialized and/or seeded")
    else:
        print("Database was already initialized and seeded, no changes made")
```

## Custom Seed Functions

You can register custom seed functions for different environments:

```python
from pat.utils.db_init import register_seed_function
from pat.config import EnvironmentType

async def seed_custom_data():
    # Your custom seeding logic here
    pass

# Register the seed function for a specific environment
register_seed_function(str(EnvironmentType.DEVELOPMENT), seed_custom_data)
```

## Idempotence

All database initialization functions are designed to be idempotent:

1. `check_database_exists` and `create_database` check if the database already exists before attempting to create it
2. `apply_migrations` checks the current migration status and only applies pending migrations
3. Seed functions check if data already exists before seeding

This ensures that the functions can be safely run multiple times without causing issues.

## Error Handling

The database initialization utilities include comprehensive error handling:

1. Connection errors are handled with retry logic
2. Migration errors are logged and propagated
3. Seeding errors are logged and propagated

All errors include detailed logging to help diagnose issues.

## Environment-Specific Configuration

The database initialization process uses environment-specific configuration from `pat.config.SETTINGS`:

1. Database connection parameters (host, port, user, password, database name)
2. Environment type (development, testing, production)

Different environments can have different seed data and configuration parameters.