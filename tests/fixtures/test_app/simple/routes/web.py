from crya import Route

from ..app.handlers import home, welcome

Route.get("/", home).name("home")
Route.get("/welcome", welcome).name("welcome")
