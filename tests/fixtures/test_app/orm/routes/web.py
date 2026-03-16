from crya import Route

from ..app.handlers import create_post, delete_post, get_post, list_posts

Route.get("/posts", list_posts)
Route.post("/posts", create_post)
Route.get("/posts/{id}", get_post)
Route.delete("/posts/{id}", delete_post)
