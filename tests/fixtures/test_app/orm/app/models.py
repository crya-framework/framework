from crya.orm import Field, Model


class Post(Model):
    id: int | None = Field(default=None, db_pk=True)
    title: str
    content: str

    class Meta:
        is_table = True
        table_name = "posts"
