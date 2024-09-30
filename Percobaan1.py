import openai
import os
import re  # Untuk melakukan pemanggilan API custom
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import plotly.express as px
from langchain.llms import OpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent

# Memuat variabel lingkungan
load_dotenv()

# Mendapatkan API key dari lingkungan
apikey = os.getenv("API_KEY")

# Layout Streamlit
st.title("AI Assistant for Data Science 🤖")
st.subheader("Masukkan pesan untuk asisten")

llm = OpenAI(temperature=0)

with st.sidebar:
    st.write("*Your Data Science Adventure Begins with a CSV Upload*")
    st.caption('''You may already know that every exciting data science journey starts with a dataset. That's why I'd love for you to upload a CSV file. Once we have your data in hand, we'll dive into understanding it and have some fun exploring it. Then, we'll work together to shape your business challenge into a data science framework. I'll introduce you to the coolest machine learning models, and we'll use them to tackle your problem. Sounds fun right?''')

user_csv = st.file_uploader("upload your file here")

df = None
if user_csv is not None:
    user_csv.seek(0)
    df = pd.read_csv(user_csv, low_memory=False)

@st.cache_data
def function_agent(df):
    if df is not None:
        pandas_agent = create_pandas_dataframe_agent(llm, df, verbose=True, allow_dangerous_code=True)
        
        st.write("**Data Overview**")
        st.write("The first rows of your dataset look like this:")
        st.write(df)
        st.write("**Data Cleaning**")
        columns_df = pandas_agent.run("What are the meaning of the columns?")
        st.write(columns_df)
        missing_values = pandas_agent.run("How many missing values does this dataframe have? Start the answer with 'There are'")
        st.write(missing_values)
        duplicates = pandas_agent.run("Are there any duplicate values and if so where?")
        st.write(duplicates)
        st.write("**Data Summarisation**")
        st.write(df.describe())
        correlation_analysis = pandas_agent.run("Calculate correlations between numerical variables to identify potential relationships.")
        st.write(correlation_analysis)
        outliers = pandas_agent.run("Identify outliers in the data that may be erroneous or that may have a significant impact on the analysis.")
        st.write(outliers)
        new_features = pandas_agent.run("What new features would be interesting to create?")
        st.write(new_features)
    else:
        st.write("Silakan unggah file CSV untuk memulai analisis.")

# Fungsi untuk memvisualisasikan data
def visualize_data(df):
    numeric_columns = df.select_dtypes(include='number').columns  # Memilih hanya kolom numerik
    df_melted = df.melt(var_name='Variable', value_name='Value', value_vars=numeric_columns)  # Mengubah bentuk DataFrame
    fig = px.bar(df_melted, x='Variable', y='Value', title='Grafik Batang Semua Data', 
                color='Variable', barmode='group')  # Grafik batang dengan beberapa warna berdasarkan variabel
    st.plotly_chart(fig)  

def is_data_related_question(question, df):
    """
    Mengecek apakah pertanyaan terkait dengan data yang di-upload dengan memeriksa kolom atau kata kunci terkait data.
    """
    # Mengambil nama kolom dari data
    column_names = df.columns.tolist() if df is not None else []
    
    # Kata kunci yang sering muncul dalam pertanyaan terkait data
    data_keywords = ['data', 'missing values', 'duplikat', 'grafik', 'outlier', 'summary', 'correlation'] + column_names
    
    # Cek apakah ada kata kunci terkait data dalam pertanyaan
    for keyword in data_keywords:
        if re.search(r'\b' + re.escape(keyword) + r'\b', question, re.IGNORECASE):
            return True
    return False

# Menjalankan fungsi untuk analisis data
function_agent(df)

# Memilih kolom untuk visualisasi
if df is not None:
    st.subheader("Visualisasi Semua Data")
    if st.button("Tampilkan Semua Grafik"):
        visualize_data(df)
        
# Input pengguna untuk pertanyaan
user_question_variabel = st.text_input("Pesan :", "")
        
if st.button("Kirim Pesan"):
    if df is not None and user_question_variabel:
        # Mengidentifikasi apakah pertanyaan terkait data atau pengetahuan umum
        if is_data_related_question(user_question_variabel, df):
            st.write("**Pertanyaan terkait data. Menganalisis data...**")
            
            # Menggunakan Langchain agent untuk menjawab pertanyaan terkait data
            pandas_agent = create_pandas_dataframe_agent(llm, df, verbose=True, allow_dangerous_code=True)
            response = pandas_agent.run(user_question_variabel)
            st.write(f"**Respons dari data:** {response}")
        else:
            st.write("**Pertanyaan umum. Menjawab dengan pengetahuan umum...**")
            # Menggunakan OpenAI untuk menjawab pertanyaan umum
            response = llm(user_question_variabel)
            st.write(f"**Respons Pengetahuan Umum:** {response}")
    else:
        st.write("Silakan unggah file CSV dan masukkan pertanyaan.")
