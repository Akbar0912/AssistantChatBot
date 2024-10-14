import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
import json
import pydeck as pdk
import requests

# Inisialisasi klien OpenAI
client = OpenAI()

# URL API statis
API_URL = "http://127.0.0.1:8000/api/kinerja"

# Fungsi untuk mengambil data dari API
def fetch_data_from_api():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        if data['status'] and 'data' in data:
            return pd.json_normalize(data['data'])
        else:
            st.error("Data tidak ditemukan dalam respons API")
            return None
    except requests.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
        return None
    
# Fungsi untuk menganalisis permintaan pengguna menggunakan OpenAI Assistant
def analyze_user_request(data, user_query):
    system_message = f"""
    You are an AI assistant expert in data analysis and visualization.
    Available data:
    {data.to_json(orient='records')}
    
    Available columns: {', '.join(data.columns)}
    
    Your task is to analyze the user's request and provide an answer based on the data.
    If asked to create a visualization, provide instructions in JSON format with the following structure:
    {{
        "type": "visualization",
        "chart_type": "chart_type",
        "x_column": "x_column_name",
        "y_column": "y_column_name",
        "title": "chart_title",
        "description": "short_description"
    }}
    If asked to create a map, use:
    {{
        "type": "visualization",
        "chart_type": "map",
        "latitude_column": "latitude_column_name",
        "longitude_column": "longitude_column_name",
        "title": "map_title",
        "description": "short_description"
    }}
    For analysis questions that don't require visualization, provide an answer in JSON format:
    {{
        "type": "analysis",
        "answer": "your_analysis_answer"
    }}
    If the question is outside the context of the data, provide a general answer in the format:
    {{
        "type": "general",
        "answer": "your_general_answer"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_query}
            ]
        )
        result = response.choices[0].message.content
        # Pastikan hasil dapat di-parse sebagai JSON
        json.loads(result)
        return result
    except json.JSONDecodeError:
        # Jika hasil bukan JSON valid, bungkus dalam format yang benar
        return json.dumps({
            "type": "error",
            "answer": "Maaf, terjadi kesalahan dalam memproses permintaan Anda. Mohon coba lagi."
        })

# Fungsi asisten untuk pertanyaan umum dan terkait data
def question_assistant(data, user_question):
    system_message = f"""
    Anda adalah asisten AI yang ahli dalam analisis data dan menjawab pertanyaan umum.
    Data yang tersedia:
    {data.to_json(orient='records', lines=True)}
    
    Kolom yang tersedia: {', '.join(data.columns)}
    
    Tugas Anda adalah menjawab pertanyaan pengguna berdasarkan data yang tersedia atau pengetahuan umum.
    Berikan jawaban yang informatif dan akurat.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_question}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Terjadi kesalahan dalam memproses pertanyaan: {str(e)}"
    return response.choices[0].message.content

# Fungsi untuk membuat visualisasi
def create_visualization(df, viz_instructions):
    chart_type = viz_instructions['chart_type']
    x_column = viz_instructions['x_column']
    y_column = viz_instructions['y_column']
    title = viz_instructions['title']
    
    if chart_type == 'map':
        return create_map_visualization(df, viz_instructions)
    
    elif chart_type == 'bar':
        chart_data = df.set_index(x_column)[[y_column]]
        st.bar_chart(chart_data, stack=False)
    
    elif chart_type == 'scatter':
        st.scatter_chart(
            df,
            x=x_column,
            y=y_column,
            use_container_width=True
        )
        
    elif chart_type in ['line', 'area']:
        chart_func = st.line_chart if chart_type == 'line' else st.area_chart
        chart_func(df.set_index(x_column)[y_column], use_container_width=True)
    
    elif chart_type == 'histogram':
        fig, ax = plt.subplots()
        ax.hist(df[x_column], bins=20)
        ax.set_xlabel(x_column)
        ax.set_ylabel('Frequency')
        ax.set_title(f'Histogram of {x_column}')
        st.pyplot(fig)
    
    elif chart_type == 'box':
        fig, ax = plt.subplots()
        df.boxplot(column=y_column, by=x_column, ax=ax)
        ax.set_title(f'Box Plot of {y_column} by {x_column}')
        ax.set_ylabel(y_column)
        st.pyplot(fig)
    
    elif chart_type == 'pie':
        fig, ax = plt.subplots()
        df[y_column].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax)
        ax.set_title(f'Pie Chart of {y_column}')
        st.pyplot(fig)
    
    st.write(f"### {title}")
    st.write(f"X-axis: {x_column}")
    st.write(f"Y-axis: {y_column}")

    return None


def clean_and_prepare_data(df):
    # Konversi latitude dan longitude ke float, ganti nilai null dengan NaN
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # Hapus baris dengan nilai NaN di latitude atau longitude
    df = df.dropna(subset=['latitude', 'longitude'])
    
    return df
# Fungsi untuk membuat visualisasi peta menggunakan pydeck
def create_map_visualization(df, viz_instructions):
    
    df = clean_and_prepare_data(df)
    
    lat_column = viz_instructions.get('latitude_column', 'latitude')
    lon_column = viz_instructions.get('longitude_column', 'longitude')
    
    if df.empty:
        st.error("Tidak ada data valid untuk divisualisasikan.")
        return None
    
    view_state = pdk.ViewState(
        latitude=df[lat_column].mean(),
        longitude=df[lon_column].mean(),
        zoom=11,
        pitch=50,
    )
    
    layer = [
            pdk.Layer(
                "HexagonLayer",
                df,
                get_position="[longitude, latitude]",
                radius=1000,
                elevation_scale=10,
                elevation_range=[0, 3000],
                pickable=True,
                extruded=True,
                auto_highlight=True,

            ),
            pdk.Layer(
                "ScatterplotLayer",
                df,
                get_position='[longitude, latitude]',
                get_color='[200, 30, 0, 160]',
                elevation_scale=51,
                get_radius=1000,
                pickable=True,
            )
        ]
    
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v9',
        tooltip={
                "html": "<b>Nama:</b> {name}<br><b>Alamat:</b> {alamat}<br><b>Jabatan:</b> {nama_jabatan}<br><b>Departemen:</b> {nama_departemen}<br><b>Jumlah Pekerjaan:</b> {jumlah_proyek}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            },
    )

st.set_page_config(layout="wide")
st.title("AI-Powered Data Analysis and Visualization")

# Fetch data from API
data = fetch_data_from_api()

if data is not None:
    st.write("Data Preview:")
    st.dataframe(data)

    st.header("Visualization")
    viz_query = st.text_input("Describe the visualization you want:")
    if viz_query:
        try:
            ai_response = json.loads(analyze_user_request(data, viz_query))
            if ai_response['type'] == 'visualization':
                st.write("Visualization Instructions:")
                st.json(ai_response)
                if ai_response['chart_type'] =='map':
                    map_chart = create_map_visualization(data, ai_response)
                    if map_chart:
                        st.pydeck_chart(map_chart)
                    else:
                        st.error("Tidak dapat membuat visualisasi")
                else:
                    create_visualization(data, ai_response)
                st.write(ai_response['description'])
            else:
                st.write("AI Response:")
                st.write(ai_response['answer'])
        except Exception as e:
            st.error(f"Terjadi kesalahan: {str(e)}")

    st.header("Ask a Question")
    user_question = st.text_input("Ask your question:")
    
    if user_question:
        try:
            ai_response = question_assistant(data, user_question)
            st.write("AI Response:")
            st.write(ai_response)
        except Exception as e:
                st.error(f"Terjadi kesalahan dalam memproses pertanyaan: {str(e)}")

