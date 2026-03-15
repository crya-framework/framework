from crya import Request, Response


async def home(request: Request):
    print(request)

    return Response("hello world", status_code=200)
