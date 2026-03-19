# Crya

A modern async Python framework.

**Work in progress**: do not use in production (yet).

Objective: having a modern async batteries-included framework with a nice DX.

A lot of inspiration comes from Laravel, a bit from FastAPI and Django.

Uses:

- [Starlette](https://starlette.dev/) (for routing and ASGI)
- [Oxyde](https://github.com/mr-fatalyst/oxyde) for the ORM
- [Pydantic](https://docs.pydantic.dev/latest/) for data validation

Overview:

| Feature                   | Status |
| ---                       | ---    |
| Basic routing             | ✅     |
| Grouping routes (prefix)  | ✅     |
| URL Generation            |        |
| CORS                      | ✅     |
| ORM shadowing             | ✅     |
| Templating (blade-like)   | ✅     |
| Middlewares               | ✅     |
| Security                  |        |
| CSRF Protection           |        |
| Vite plugin               | ✅     |
| Logging                   |        |
| Caching                   |        |
| Mailing                   |        |
| Events / Signals          |        |
| Localization              |        |
| Rate limiting             |        |
| Testing tools             | ✅     |
| Pytest plugin (Pest-like) | ✅     |

## Why this name?

Because [Cr[i|y]as](https://en.wikipedia.org/wiki/Cria) are amazing.

[Come on Crya!](https://www.youtube.com/watch?v=6Y3fmsULu_U) ❤️
