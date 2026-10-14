"""Read-only SQLite execution shared by query APIs."""
from contextlib import closing
from pathlib import Path
import sqlite3
import pandas as pd

db_path = Path(__file__).resolve().with_name("employee_events.db")


class QueryMixin:
    def __init__(self, database=None):
        self.db_path = Path(database) if database else db_path

    def pandas_query(self, sql_query, parameters=()):
        with closing(sqlite3.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            return pd.read_sql_query(sql_query, connection, params=parameters)

    def query(self, sql_query, parameters=()):
        with closing(sqlite3.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            return connection.execute(sql_query, parameters).fetchall()