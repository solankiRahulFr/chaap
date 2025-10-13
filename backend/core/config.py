import os 
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()
class Setting:
    SECRET_KEY=os.getenv("SECRET_KEY")
    ALGORITHM=os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES=os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")
    DATABASE_URL=os.getenv("DATABASE_URL")
    # ACCESS_TOKEN_EXPIRE = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # REFRESH_TOKEN_EXPIRE = timedelta(minutes=REFRESH_TOKEN_EXPIRE_DAYS)

setting = Setting()
