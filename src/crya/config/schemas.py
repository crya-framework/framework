from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    url: str


class TemplatingConfig(BaseModel):
    templates_path: str = "templates"
    cache_path: str = "storage/cache/compiled/templates"


class MiddlewareGroupMutation(BaseModel):
    model_config = {"extra": "forbid"}

    append: list = []
    prepend: list = []
    remove: list = []


class MiddlewareConfig(BaseModel):
    model_config = {"extra": "forbid"}

    web: MiddlewareGroupMutation = MiddlewareGroupMutation()
    api: MiddlewareGroupMutation = MiddlewareGroupMutation()
