import os
import streamlit as st 
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SQLDatabase
import re
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

pwd = os.environ['DB_PASSWORD']
uid = os.environ['DB_USER']
server = "localhost"
db = os.environ['DB_NAME']
port = 5432

def get_detailed_schema():
    """Mendapatkan informasi detail skema database"""
    return """Anda adalah ahli SQL yang bekerja dengan database PostgreSQL. 
    
    PENTING: 
    - JANGAN gunakan backtick (`)
    - JANGAN tambahkan kata 'sql' di awal query
    - Gunakan nama kolom yang tepat
    - Query harus dimulai langsung dengan SELECT
    - Gunakan COUNT, GROUP BY, ORDER BY untuk hasil yang informatif
    - Tambahkan alias untuk nama kolom yang lebih jelas
    - Urutkan hasil untuk mempermudah pembacaan
    
    Database memiliki dua view utama:

    1. public.vw_personel_analytic
    Kolom-kolom penting:
    - personelid (integer) - ID unik personel
    - nama (varchar) - Nama lengkap personel
    - nrp (varchar) - Nomor registrasi personel
    - satuan (varchar) - Nama satuan kerja
    - matra (varchar) - Matra (AD/AL/AU)
    - jabatan_terakhir_nama_jabatan (varchar) - Nama jabatan terakhir
    - last_pangkat (varchar) - Pangkat terakhir
    - pendidikan_terakhir_nama_sekolah (varchar) - Nama sekolah terakhir
    - pendidikan_terakhir_tahun_lulus (integer) - Tahun lulus
    - gaji_terakhir_gaji_pokok (numeric) - Gaji pokok terakhir

    2. public.vw_umur_personel
    Kolom-kolom:
    - personelid (integer) - ID unik personel
    - nama (varchar) - Nama lengkap
    - tgllahir (date) - Tanggal lahir
    - umur (integer) - Umur dalam tahun
    - nrp (varchar) - Nomor registrasi personel

    Contoh Query Valid:
    1. Mencari personel berdasarkan satuan:
    SELECT nama, nrp, jabatan_terakhir_nama_jabatan, pangkat
    FROM public.vw_personel_analytic 
    WHERE satuan = 'Kementerian Pertahanan'

    2. Mencari data umur personel:
    SELECT nama, umur, nrp
    FROM public.vw_umur_personel
    ORDER BY umur DESC

    3. Mencari personel berdasarkan matra:
    SELECT nama, nrp, pangkat, satuan
    FROM public.vw_personel_analytic
    WHERE matra = 'AD'
    """

def validate_sql_query(query: str) -> bool:
    """Validasi query SQL"""
    valid_starts = ['SELECT', 'WITH']
    query = query.strip().upper()
    return any(query.startswith(keyword) for keyword in valid_starts)

def clean_sql_query(query: str) -> str:
    """Membersihkan query SQL dari potensi SQL injection"""
    # Hapus backticks
    cleaned = query.replace('`', '')
    # Hapus kata 'sql' di awal query jika ada
    cleaned = re.sub(r'^sql\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r';.*$', '', query)
    cleaned = re.sub(r'--.*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    cleaned = ' '.join(cleaned.split())
    return cleaned

def validate_column_names(query: str) -> bool:
    """Validasi nama kolom dalam query"""
    valid_columns = {
        'vw_personel_analytic': [
            'personelid', 'nama', 'nip_nrp', 'nrp', 'satuan', 'matra',
            'jabatan_terakhir_nama_jabatan', 'pangkat',
            'pendidikan_terakhir_nama_sekolah',
            'pendidikan_terakhir_tahun_lulus',
            'gaji_terakhir_gaji_pokok'
        ],
        'vw_umur_personel': [
            'personelid', 'nama', 'tgllahir', 'umur', 'nrp'
        ]
    }
    
    query = query.lower()
    for view, columns in valid_columns.items():
        if view in query:
            cols_in_query = re.findall(r'select\s+(.+?)\s+from', query)[0].split(',')
            cols_in_query = [c.strip() for c in cols_in_query]
            if '*' in cols_in_query:
                return True
            return all(any(col in c for c in cols_in_query) for col in columns)
    return False

def format_error_message(error: Exception) -> str:
    """Format error message for user display."""
    return f"Maaf, terjadi kesalahan dalam memproses permintaan Anda. Detail: {str(error)}"


def init_database() -> SQLDatabase:
  db_uri = f"postgresql://{uid}:{pwd}@{server}:{port}/{db}"
  return SQLDatabase.from_uri(
      db_uri, 
      schema="public",
      view_support=True,
      )

def generate_sql_query(question: str) -> str:
    """Menghasilkan query SQL berdasarkan pertanyaan user"""
    system_prompt = get_detailed_schema()
    
    llm = ChatOllama(model="llama3.2", temperature=0.1)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analisis pertanyaan berikut dan buat query SQL yang tepat:
        Pertanyaan: {question}
        
        INGAT:
        - JANGAN gunakan backtick (`)
        - JANGAN tambahkan kata 'sql' di awal
        - Mulai langsung dengan SELECT
        
        Hasilkan HANYA query SQL yang valid, tanpa penjelasan tambahan.
        Gunakan nama kolom yang tepat dari skema yang diberikan.""")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    # Generate query pertama
    sql = chain.invoke({"question": question})
    sql = clean_sql_query(sql)
    
    # Validasi query
    if not validate_sql_query(sql) or not validate_column_names(sql):
        # Jika validasi gagal, coba generate ulang dengan prompt yang lebih spesifik
        specific_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", f"""Query sebelumnya tidak valid. Buat query baru untuk pertanyaan:
            {question}
            
            PASTIKAN:
            1. Gunakan nama kolom yang tepat dari skema
            2. Gunakan view yang sesuai (vw_personel_analytic atau vw_umur_personel)
            3. Format query yang benar
            
            Hasilkan HANYA query SQL.""")
        ])
        
        chain = specific_prompt | llm | StrOutputParser()
        sql = chain.invoke({"question": question})
        sql = clean_sql_query(sql)
    
    return sql

def execute_query(db: SQLDatabase, query: str) -> pd.DataFrame:
    """Execute SQL query and return results as DataFrame"""
    try:
        # Get the underlying SQLAlchemy engine
        engine = db._engine
        # Execute query and return DataFrame
        return pd.read_sql_query(query, engine)
    except Exception as e:
        st.error(f"Error executing query: {str(e)}")
        return pd.DataFrame()

def get_response(user_query: str, db: SQLDatabase, chat_history: list) -> str:
    """Mendapatkan respons untuk pertanyaan user"""
    try:
        # Generate SQL query
        sql_query = generate_sql_query(user_query)  
        print(f"Generated query: {sql_query}")
        
        # Eksekusi query dan dapatkan hasil
        # query_result = db.run(sql_query)
        df_results = execute_query(db, sql_query)
        
        # Template untuk respons
        template = """
        Berdasarkan pertanyaan dan data yang tersedia:
        {question}

        DATA HASIL QUERY:
        {raw_data}
        
        ANALISIS:
        Berdasarkan data di atas, {analysis}
        
        Apakah Anda ingin informasi lebih detail tentang data tertentu?
        """
        
        prompt = ChatPromptTemplate.from_template(template)     
        llm = ChatOllama(model="llama3.2", temperature=0.1)
        
        chain = RunnablePassthrough.assign(
            raw_data=lambda x: df_results.to_string(),
            analysis=lambda x: llm.predict(f"Berikan analisis dari data berikut: {df_results.to_string()}")
        ) | prompt | llm | StrOutputParser()
        
        response = chain.invoke({
            "question": user_query,
            "query_result": f"Query yang digunakan: {sql_query}",
            "chat_history": chat_history
        })
        
        return response, df_results
        
    except Exception as e:
        return f"Maaf, terjadi kesalahan dalam memproses pertanyaan Anda. Detail: {str(e)}"

def format_query_result(result: str) -> str:
    """Format hasil query agar lebih mudah dibaca"""
    try:
        # Jika hasil adalah string kosong
        if not result:
            return "Tidak ada data yang ditemukan"
            
        # Jika hasil sudah dalam format yang bagus, kembalikan apa adanya
        if isinstance(result, str) and ('\n' in result or '\t' in result):
            return result
            
        # Jika hasil adalah string tapi perlu diformat
        lines = result.split('), (')
        formatted_lines = []
        for line in lines:
            # Bersihkan karakter special
            clean_line = line.replace('(', '').replace(')', '').replace("'", "")
            formatted_lines.append(clean_line)
            
        return '\n'.join(formatted_lines)
        
    except Exception as e:
        return f"Error saat memformat data: {str(e)}\nData asli: {result}"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
      AIMessage(content="Hello! I'm a Data assistant. Ask me a question about your AdventureWorks :bike: personel data."),
    ]

st.set_page_config(page_title="Chat with Postgres", page_icon=":thought_balloon:")

st.title("Chat with Postgres")


for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("User"):
            st.markdown(message.content)

# initialize the db
db = init_database()
st.session_state.db = db
st.success("Connected to database!")

user_query = st.chat_input("Type a question...")
if user_query is not None and user_query.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    
    with st.chat_message("User"):
        st.markdown(user_query)
        
    with st.chat_message("AI"):
        response, df_results = get_response(user_query, st.session_state.db, st.session_state.chat_history)
        st.markdown(response)
        
        if df_results is not None and not df_results.empty:
            st.write("Query Results:")
            st.dataframe(df_results)
            
            df_content = f"\nData Results:\n```\n{df_results.to_string()}\n```"
            full_response = response + df_content
            
    st.session_state.chat_history.append(AIMessage(content=response))