from crya import Request, Response, view


async def home(request: Request):
    return Response("hello world", status_code=200)


async def welcome(request: Request):
    return view("welcome.loom", {"name": "crya"})
