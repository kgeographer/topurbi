"""
Database connection utility for TopUrbi/Alcedo scripts.
Reads connection parameters from .env in the project root.
"""
import os
from typing import Optional
import psycopg
from dotenv import load_dotenv

load_dotenv()


def db_connect(schema: Optional[str] = None) -> psycopg.Connection:
    conn = psycopg.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "topurbi"),
        user=os.environ.get("PGUSER"),
        password=os.environ.get("PGPASSWORD"),
    )
    if schema:
        conn.execute(f"SET search_path TO {schema}, public")
    return conn
