import psycopg2
from typing import Optional

class DatabaseConnection:
    def __init__(self, dbname: str, user: str, password: str, host: str, port: str):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> psycopg2.extensions.connection:
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            return self.conn
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {str(e)}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def execute_query(self, query: str) -> list:
        """Execute SQL query and return results"""
        if not self.conn:
            self.connect()
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            raise Exception(f"Query execution failed: {str(e)}")