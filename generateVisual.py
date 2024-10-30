import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
import json
import pydeck as pdk
import pdfplumber

# Inisialisasi klien OpenAI
client = OpenAI()

# Fungsi untuk memuat data dari berbagai sumber
def load_data(file):
    file_extension = file.name.split('.')[-1].lower()
    if file_extension == 'csv':
        return pd.read_csv(file)
    elif file_extension == 'xlsx':
        return pd.read_excel(file)
    elif file_extension == 'pdf':
        with pdfplumber.open(file) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        return text
    else:
        raise ValueError("Unsupported file format")

# Fungsi untuk menganalisis permintaan pengguna menggunakan OpenAI Assistant
def analyze_visualization_request(data, user_query):
    system_message = f"""
    Anda adalah asisten AI yang ahli dalam analisis data dan visualisasi.
    Data yang tersedia:
    {data.head().to_json()}
    
    Kolom yang tersedia: {', '.join(data.columns)}
    
    Tugas Anda adalah menganalisis permintaan pengguna dan memberikan instruksi untuk membuat visualisasi yang sesuai.
    Harap berikan respons dalam format JSON dengan struktur berikut:
    {{
        "chart_type": "jenis_grafik",
        "x_column": "nama_kolom_x",
        "y_column": "nama_kolom_y",
        "title": "judul_grafik",
        "description": "deskripsi_singkat"
    }}
    Jika diminta untuk membuat peta, gunakan:
    {{
        "type": "visualization",
        "chart_type": "map",
        "latitude_column": "nama_kolom_latitude",
        "longitude_column": "nama_kolom_longitude",
        "title": "judul_peta",
        "description": "deskripsi_singkat"
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_query}
        ]
    )
    
    return response.choices[0].message.content

# Fungsi untuk menjawab pertanyaan umum dan terkait data menggunakan OpenAI Assistant
def answer_question(data, user_question, is_dataframe):
    if is_dataframe:
        system_message = f"""
        Anda adalah asisten AI yang ahli dalam analisis data dan menjawab pertanyaan.
        Data yang tersedia:
        {data.head().to_json()}
        
        Kolom yang tersedia: {', '.join(data.columns)}
        
        Tugas Anda adalah menjawab pertanyaan pengguna berdasarkan data yang tersedia.
        Jika pertanyaan terkait dengan data, berikan jawaban berdasarkan informasi dalam dataset.
        Jika pertanyaan adalah pertanyaan umum yang tidak terkait langsung dengan data, 
        berikan jawaban berdasarkan pengetahuan umum Anda.
        Berikan jawaban langsung tanpa kode atau instruksi tambahan.
        """
    else:
        system_message = f"""
        Anda adalah asisten AI yang ahli dalam menganalisis teks dan menjawab pertanyaan.
        Konten dokumen:
        {data[:1000]}  # Menggunakan 1000 karakter pertama sebagai konteks

        Tugas Anda adalah menjawab pertanyaan pengguna berdasarkan konten dokumen jika relevan.
        Jika pertanyaan tidak terkait langsung dengan konten dokumen, 
        berikan jawaban berdasarkan pengetahuan umum Anda.
        Berikan jawaban langsung tanpa kode atau instruksi tambahan.
        """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_question}
        ]
    )
    
    return response.choices[0].message.content

# Fungsi untuk membuat visualisasi
def create_visualization(df, viz_instructions):
    chart_type = viz_instructions['chart_type']
    x_column = viz_instructions['x_column']
    y_column = viz_instructions['y_column']
    title = viz_instructions['title']
    
    if chart_type == 'map':
        return create_map_visualization(df, viz_instructions)
    
    elif chart_type == 'line':
        st.line_chart(df.set_index(x_column)[y_column], use_container_width=True)
    
    elif chart_type == 'bar':
        st.bar_chart(df.set_index(x_column)[y_column], use_container_width=True)
    
    elif chart_type == 'scatter':
        st.scatter_chart(
            df,
            x=x_column,
            y=y_column,
            use_container_width=True
        )
        
    elif chart_type == 'area':
        st.area_chart(df.set_index(x_column)[y_column], use_container_width=True)
    
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

# Fungsi untuk membuat visualisasi peta menggunakan pydeck
def create_map_visualization(df, viz_instructions):
    lat_column = viz_instructions.get('latitude_column', 'latitude')
    lon_column = viz_instructions.get('longitude_column', 'longitude')
    
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
                tooltip={"text": "{name}, {host_name}"},

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
                "html": "<b>Name:</b> {host_name}<br><b>Place:</b> {neighbourhood}<br><b>Price:</b> ${price}<br><b>Description:</b> {name}<br><b>Place:</b> {neighbourhood_group}<br><b>Lokasi:<b>{latitude}{longitude}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            },
    )

st.set_page_config(layout="wide")
st.title("AI-Powered Data Analysis and Visualization")

# Aplikasi Streamlit
with st.sidebar:
    st.header("Data Upload")
    uploaded_file = st.file_uploader("Upload your file (CSV, Excel, or PDF)", type=['csv', 'xlsx', 'pdf'])

    if uploaded_file is not None:
        try:
            data = load_data(uploaded_file)
            is_dataframe = isinstance(data, pd.DataFrame)
            
            if is_dataframe:
                st.write("Data Preview:")
                st.dataframe(data)
            else:
                st.write("PDF Content Preview:")
                st.text(data[:500] + "...")  # Display first 500 characters of PDF
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")


if uploaded_file is not None:
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Visualization")
        viz_query = st.text_input("Describe the visualization you want:")
        if viz_query and is_dataframe:
            viz_instructions = json.loads(analyze_visualization_request(data, viz_query))
            st.write("Visualization Instructions:")
            st.json(viz_instructions)
            
            if viz_instructions['chart_type'] == 'map':
                st.pydeck_chart(create_map_visualization(data, viz_instructions))
            else:
                create_visualization(data, viz_instructions)
            
            st.write(viz_instructions['description'])
        elif viz_query and not is_dataframe:
            st.write("Visualizations are only available for CSV and Excel files.")
    
    with col2:
        st.header("Ask a Question")
        user_question = st.text_input("Ask a question about the data or any general question:")
        if user_question:
            answer = answer_question(data, user_question, is_dataframe)
            st.write("AI Response:")
            st.write(answer)
