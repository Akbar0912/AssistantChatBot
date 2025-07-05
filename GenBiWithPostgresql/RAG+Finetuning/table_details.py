from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq 
import streamlit as st
import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

# llm = ChatOllama(model="llama3.2", temperature=0)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# CHANGE: Use ChatGroq instead of ChatOllama
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.1-8b-instant",  # or "llama-3.1-8b-instant"
    temperature=0
)

@st.cache_data
def get_table_details():
    table_description = pd.read_csv("database_table_descriptions.csv")
    table_details = ""
    for index, row in table_description.iterrows():
        table_details += f"Table name: {row['Table']}\nTable Description: {row['Description']}\n\n"
    return table_details

class Table(BaseModel):
    """Table in SQL database"""
    name: str = Field(description="Name of table in SQL database")
    
def get_tables(output: str) -> List[str]:
    import re
    valid_tables = ['customers', 'payments', 'orders', 'products', 'productlines', 'employees', 'offices', 'orderdetails']
    matches = re.findall(r'\b(' + '|'.join(valid_tables) + r')\b', output, re.IGNORECASE)
    if matches:
        return [match.lower() for match in set(matches)]
    return ['customers']

table_details = get_table_details()
table_details_prompt = f"""Kamu adalah sistem untuk memilih tabel dari MySQL database berdasarkan pertanyaan user.
Berikut adalah daftar tabel yang tersedia dalam database beserta deskripsinya:
{table_details}

Tugasmu adalah menentukan tabel mana yang relevan untuk pertanyaan user.
Pilih hanya tabel yang benar-benar diperlukan:
- Untuk pertanyaan tentang data pelanggan (nama, kota, negara, kredit limit, telepon, alamat), gunakan HANYA tabel 'customers'.
- Untuk pertanyaan tentang pembayaran, gunakan HANYA tabel 'payments'.
- Untuk pertanyaan tentang pesanan, gunakan 'orders' atau 'orderdetails' jika detail pesanan diperlukan.
- Untuk pertanyaan tentang produk, gunakan 'products' atau 'productlines'.
- Untuk pertanyaan tentang karyawan atau kantor, gunakan 'employees' atau 'offices'.
- Jika pertanyaan membutuhkan relasi antar tabel, sebutkan semua tabel yang relevan untuk JOIN (misalnya, 'customers, orders').
- Jika pertanyaan tidak jelas atau tidak relevan dengan database, pilih tabel yang paling mungkin (default: 'customers').
Berikan jawabannya dalam satu kalimat, menyebutkan nama tabel yang relevan (misalnya, 'customers' atau 'customers, orders').
Gunakan bahasa Indonesia.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", table_details_prompt),
    ("human", "{question}")
])

parser = StrOutputParser()

table_chain = prompt | llm | parser | get_tables