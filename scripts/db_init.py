"""Database initialization script.

This script provides command-line utilities for initializing and seeding the database.
It can be used to:
1. Initialize the database (create it if needed and apply migrations)
2. Seed the database with environment-specific data
3. Perform both initialization and seeding in one step

Usage:
    python -m scripts.db_init [--init] [--seed] [--all]

Options:
    --init    Initialize the database (create it if needed and apply migrations)
    --seed    Seed the database with environment-specific data
    --all     Perform both initialization and seeding (default if no options provided)
"""

import argparse
import asyncio
import sys

import logfire

from pat.utils.db_init import initialize_database, seed_database


async def main() -> int:
    """Run the database initialization script.

    Returns:
        int: Exit code (0 for success, non-zero for failure)

    """
    parser = argparse.ArgumentParser(description="Initialize and seed the database")
    parser.add_argument("--init", action="store_true", help="Initialize the database")
    parser.add_argument("--seed", action="store_true", help="Seed the database")
    parser.add_argument("--all", action="store_true", help="Initialize and seed the database")
    args = parser.parse_args()

    # If no options provided, default to --all
    if not (args.init or args.seed or args.all):
        args.all = True

    try:
        if args.init or args.all:
            logfire.info("Initializing database...")
            initialized = await initialize_database()
            if initialized:
                logfire.info("Database initialization completed successfully")
            else:
                logfire.info("Database was already initialized, no changes made")

        if args.seed or args.all:
            logfire.info("Seeding database...")
            seeded = await seed_database()
            if seeded:
                logfire.info("Database seeding completed successfully")
            else:
                logfire.info("No seed function found for the current environment or data already exists")
    except (OSError, ConnectionError, ValueError, TypeError) as e:
        logfire.exception("Error during database initialization or seeding", exception=str(e))
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
