import psycopg2
from psycopg2.extensions import connection
from typing import Optional
import streamlit as st
from config.posgresql import DatabaseConfig

class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.conn: Optional[connection] = None
        self.config = DatabaseConfig()

    def connect(self) -> Optional[connection]:
        try:
            if not self.conn or self.conn.closed:
                self.conn = psycopg2.connect(
                    dbname=self.config.dbname,
                    user=self.config.user,
                    password=self.config.password,
                    host=self.config.host,
                    port=self.config.port
                )
            return self.conn
        except Exception as e:
            st.error(f"Database connection error: {str(e)}")
            return None

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()