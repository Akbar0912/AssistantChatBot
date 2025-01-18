import os
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv

load_dotenv()

def init_database():
    pwd = os.environ['DB_PASSWORD']
    uid = os.environ['DB_USER']
    server = "localhost"
    db = os.environ['DB_NAME']
    port = 5432
    
    db_uri = f"postgresql://{uid}:{pwd}@{server}:{port}/{db}"
    return SQLDatabase.from_uri(db_uri, schema="public", view_support=True)