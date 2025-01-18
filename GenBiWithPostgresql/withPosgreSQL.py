import os
import streamlit as st 
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.utilities import SQLDatabase
import re
from dotenv import load_dotenv
import pandas as pd
from visualization import create_visualization, generate_viz_description
from database.connection import init_database
from llm.chain_manager import LlamaService

load_dotenv()
llama_service = LlamaService()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")

def clean_sql_query(query: str) -> str:
    """Membersihkan query SQL dari kata kunci dan karakter yang tidak diinginkan"""
    # Convert ke lowercase untuk pengecekan
    cleaned = query.strip().lower()
    
    cleaned = re.sub(r'^sql\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+sql\s+', ' ', cleaned, flags=re.IGNORECASE)
    
    # Hapus kata 'sql' di awal query dengan lebih teliti
    if cleaned.startswith('sql'):
        cleaned = query[3:].strip()
    else:
        cleaned = query.strip()
    
    # Hapus backticks
    cleaned = cleaned.replace('`', '')
    
    # Hapus semicolon dan komentar
    cleaned = re.sub(r';.*$', '', cleaned)
    cleaned = re.sub(r'--.*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    
    # Hapus multiple spaces
    cleaned = ' '.join(cleaned.split())
    
    return cleaned

def format_error_message(error: Exception) -> str:
    """Format error message for user display."""
    return f"Maaf, terjadi kesalahan dalam memproses permintaan Anda. Detail: {str(error)}"


def execute_query(db: SQLDatabase, query: str) -> pd.DataFrame:
    """Execute SQL query and return results as DataFrame"""
    try:
        if 'sql' in query.lower().split():
            query = clean_sql_query(query)
        
        # Get the underlying SQLAlchemy engine
        engine = db._engine
        # Execute query and return DataFrame
        return pd.read_sql_query(query, engine)
    except Exception as e:
        st.error(f"Error executing query: {str(e)}")
        return pd.DataFrame()

def get_response(user_query: str, db: SQLDatabase, chat_history: list) -> tuple:
    """Mendapatkan respons untuk pertanyaan user"""
    try:
        # Generate SQL query
        sql_query = llama_service.generate_sql_query(user_query)  
        print(f"Generated query: {sql_query}")
        
        # Eksekusi query dan dapatkan hasil
        df_results = execute_query(db, sql_query)
        
        # Initialize default values for visualization
        viz_result = {'success': False, 'figure': None}
        viz_description = ""
        
        # Only attempt visualization if we have valid results
        if not df_results.empty:
            viz_result = create_visualization(df_results, user_query)
            viz_description = generate_viz_description(viz_result, df_results)
        
        response = llama_service.generate_full_response(user_query, df_results, viz_description, chat_history)
        
        return response, df_results, viz_result
    
    except Exception as e:
        # Return a tuple with three elements to match the expected return type
        return (
            llama_service.format_error_message(e),
            pd.DataFrame(),
            {'success': False, 'figure': None}
        )

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
      AIMessage(content="Hello! I'm a Data assistant. Ask me a question about your AdventureWorks :bike: personel data."),
    ]

st.set_page_config(page_title="Chat with Postgres", page_icon=":thought_balloon:")

st.title("Chat with your data for visualization")


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
        response, df_results, viz_result = get_response(user_query, st.session_state.db, st.session_state.chat_history)
        st.markdown(response)
        
        if df_results is not None and not df_results.empty:
            st.write("Query Results:")
            st.dataframe(df_results)
            
            if viz_result['success']:
                st.write("Data Visualization:")
                st.plotly_chart(viz_result['figure'], use_container_width=True)
            
            df_content = f"\nData Results:\n```\n{df_results.to_string()}\n```"
            full_response = response + df_content
            
    st.session_state.chat_history.append(AIMessage(content=response))