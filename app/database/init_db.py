"""Non-destructive database initialization command."""

import argparse

from app.config import settings
from .db import get_schema_version, initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize or upgrade the Pushan database")
    parser.add_argument("--database-path", default=str(settings.database_path))
    arguments = parser.parse_args()
    initialize_database(arguments.database_path)
    print(f"Pushan database ready at {arguments.database_path}")
    print(f"Schema version: {get_schema_version(arguments.database_path)}")


if __name__ == "__main__":
    main()
