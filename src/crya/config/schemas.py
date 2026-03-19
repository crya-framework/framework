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


class CorsConfig(BaseModel):
    paths: list[str] = ["/api/*"]
    allowed_origins: list[str] = ["*"]
    allowed_origins_patterns: list[str] = []
    allowed_methods: list[str] = ["*"]
    allowed_headers: list[str] = ["*"]
    exposed_headers: list[str] = []
    supports_credentials: bool = False
    max_age: int = 0
