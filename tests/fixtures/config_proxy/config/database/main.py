from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    url: str


db_config = DatabaseConfig(url="sqlite:///db.sqlite3")
