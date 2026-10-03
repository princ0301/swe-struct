from app.base import Base
from app.config import load_config

class Runner(Base):
    def run(self):
        return load_config("settings.cfg")