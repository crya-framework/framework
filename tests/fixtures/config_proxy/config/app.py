from dataclasses import dataclass


@dataclass
class AppConfig:
    app_name: str
    debug: bool


app_config = AppConfig(app_name="CryaTest", debug=True)
