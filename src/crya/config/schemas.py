from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    url: str


class TemplatingConfig(BaseModel):
    templates_path: str = "templates"
    cache_path: str = "cache/templates"
