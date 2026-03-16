from crya import Router

from ..app.handlers import create_post, delete_post, get_post, list_posts

router = Router()
router.get("/posts", list_posts)
router.post("/posts", create_post)
router.get("/posts/{id}", get_post)
router.delete("/posts/{id}", delete_post)
