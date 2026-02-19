import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


# Establish a connection to the PostgreSQL database
def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)
