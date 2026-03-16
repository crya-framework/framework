from crya import Request
from crya.orm import NotFoundError
from starlette.responses import JSONResponse

from .models import Post


async def list_posts(request: Request):
    posts = await Post.objects.all()
    return JSONResponse([p.model_dump() for p in posts])


async def create_post(request: Request):
    data = await request.json()
    post = await Post.objects.create(**data)
    return JSONResponse(post.model_dump(), status_code=201)


async def get_post(request: Request, id: int):
    try:
        post = await Post.objects.get(id=id)
    except NotFoundError:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(post.model_dump())


async def delete_post(request: Request, id: int):
    await Post.objects.filter(id=id).delete()
    return JSONResponse(None, status_code=204)
