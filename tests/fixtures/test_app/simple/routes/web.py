from crya import Router

from ..app.handlers import home, welcome

router = Router()
router.get("/", home).name("home")
router.get("/welcome", welcome).name("welcome")
