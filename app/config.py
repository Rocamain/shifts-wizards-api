import os
from dotenv import load_dotenv

load_dotenv()  # l

class Config:
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY")
