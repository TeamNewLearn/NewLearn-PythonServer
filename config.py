import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_USER = os.getenv("DB_USER")
DATABASE_PASSWORD = os.getenv("DB_PASSWORD")
DATABASE_HOST = os.getenv("DB_HOST")
DATABASE_PORT = os.getenv("DB_PORT")
DATABASE_NAME = os.getenv("DB_NAME")
DART_API_KEY = os.getenv("DART_API_KEY")

def get_db_config():
    return {
        'user': DATABASE_USER,
        'password': DATABASE_PASSWORD,
        'host': DATABASE_HOST,
        'port': int(DATABASE_PORT),
        'database': DATABASE_NAME
    }
