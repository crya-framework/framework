from crya import Route

from ..app.handlers import home

Route.get("/", home).name("home")
