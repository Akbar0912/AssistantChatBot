import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
import json
import pydeck as pdk
import pdfplumber
import openpyxl

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
def analyze_user_request(data, user_query, is_dataframe):
    if is_dataframe:
        system_message = f"""
        Anda adalah asisten AI yang ahli dalam analisis data dan visualisasi.
        Data yang tersedia:
        {data.head().to_json()}
        
        Kolom yang tersedia: {', '.join(data.columns)}
        
        Tugas Anda adalah menganalisis permintaan pengguna dan memberikan jawaban berdasarkan data.
        Jika diminta untuk membuat visualisasi, berikan instruksi dalam format JSON.
        Untuk pertanyaan analisis, berikan jawaban langsung berdasarkan data tanpa menjelaskan cara membuat grafik atau memberikan kode.
        Jika pertanyaan di luar konteks data, berikan jawaban umum sesuai dengan pengetahuan Anda.
        
        Tugas Anda adalah menganalisis permintaan pengguna dan memberikan instruksi untuk membuat visualisasi yang sesuai.
        Harap berikan respons dalam format JSON dengan struktur berikut:
        {{
            "chart_type": "jenis_grafik",
            "x_column": "nama_kolom_x",
            "y_column": "nama_kolom_y",
            "title": "judul_grafik",
            "description": "deskripsi_singkat"
        }}
        Jika diminta untuk membuat peta, gunakan "chart_type": "map" dan tentukan kolom latitude dan longitude, 
        # jika diminta untuk membuat chart tampilkan sesuai dengan yang sudah ditentukan.
        # jika pertanyaan di luar konteks atau pengetahuan umum berikan jawaban sesuai dengan kemampuan model
        # yang anda miliki.
        # Untuk pertanyaan analisis, berikan jawaban langsung berdasarkan data tanpa menjelaskan cara membuat grafik.
        # jika diberikan pertanyaan diluar dari tampilkan visualisasi chart berikan jawaban terkait dengan isi data file sesuai dengan isi data tersebut.
        """
    else:
        system_message = f"""
        Anda adalah asisten AI yang ahli dalam analisis teks dan menjawab pertanyaan.
        Konten dokumen:
        {data[:1000]}  # Menggunakan 1000 karakter pertama sebagai konteks

        Tugas Anda adalah menjawab pertanyaan pengguna berdasarkan konten dokumen atau pengetahuan umum jika pertanyaan di luar konteks dokumen.
        Berikan jawaban langsung tanpa kode atau instruksi tambahan.
        """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_query}
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
                "html": "<b>Name:</b> {host_name}<br><b>Place:</b> {neighbourhood}<br><b>Price:</b> ${price}<br><b>Description:</b> {name}<br><b>Place:</b> {neighbourhood_group}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            },
    )

st.set_page_config(layout="wide")
st.title("AI-Powered Data Analysis and Visualization")

col1, col2 = st.columns([1,6])
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
    if is_dataframe:
        st.header("Visualization")
        viz_query = st.text_input("Describe the visualization you want:")
        if viz_query:
            viz_instructions = json.loads(analyze_user_request(data, viz_query, is_dataframe))
            st.write("Visualization Instructions:")
            st.json(viz_instructions)
            
            if viz_instructions['chart_type'] == 'map':
                st.pydeck_chart(create_map_visualization(data, viz_instructions))
            # else:
            #     fig = create_visualization(data, viz_instructions)
            #     st.pyplot(fig)
            
            create_visualization(data, viz_instructions)
            
            st.write(viz_instructions['description'])
    
    st.header("Ask a Question")
    user_question = st.text_input("Ask a question about the data or any general question:")
    if user_question:
        answer = analyze_user_request(data, user_question, is_dataframe)    
        st.write("AI Response:")
        st.write(answer)

