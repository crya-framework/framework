from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    url: str


db_config = DatabaseConfig(url="sqlite+aiosqlite:///db.sqlite3")
