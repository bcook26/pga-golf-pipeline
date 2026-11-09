from sqlalchemy.engine import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

def engine():
    DATABASE_URL = (
        f"postgresql+psycopg://postgres:{os.getenv('DB_PASSWORD')}"
        "@localhost:5432/pga_golf_etl"
    )
    try:
        engine = create_engine(DATABASE_URL)
    except Exception as e:
        print(f"Error connecting to postgres instance: {e}")
    return engine
