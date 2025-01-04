from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    dbname: str = "postgres"
    user: str = "postgres"
    password: str = "password"
    host: str = "localhost"
    port: str = "5432"