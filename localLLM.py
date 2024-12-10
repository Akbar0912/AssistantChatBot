# Import Library
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px
import pydeck as pdk
import json
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Konfigurasi LangSmith untuk Tracking
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")

# URL API
API_URL = "http://127.0.0.1:8000/api/kinerja"

# Fungsi untuk Mengambil Data dari API
@st.cache_data
def fetch_data():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()
            if data["status"]:  # Jika status API sukses
                return pd.DataFrame(data["data"])  # Mengembalikan data kinerja sebagai list
            else:
                st.error(f"Pesan API: {data['message']}")
        else:
            st.error(f"Error {response.status_code}: Gagal mengambil data dari API.")
    except Exception as e:
        st.error(f"Terjadi error: {e}")
    return pd.DataFrame()

def parse_visualization_instruction(text):
    try:
        # Trim any leading/trailing whitespace
        text = text.strip()
        
        # Check if text starts with { and ends with }
        if not (text.startswith('{') and text.endswith('}')):
            # Try to extract JSON from between first { and last }
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]
        
        # Parse JSON from output text
        parsed_json = json.loads(text)
        
        return parsed_json
    except json.JSONDecodeError as e:
        st.error(f"Gagal parsing JSON: {e}")
        st.error(f"Raw text received: {text}")
        return None

# Advanced Visualization Functions with Plotly
def create_dynamic_visualization(df, viz_instruction):
    """
    Create dynamic visualization using Plotly Express
    """
    # Ensure column names are valid
    x_column = viz_instruction.x_column
    y_column = viz_instruction.y_column
    title = viz_instruction.title

    # Create Plotly visualizations
    if viz_instruction.visualization_type == 'bar_chart':
        fig = px.bar(
            df, 
            x=x_column, 
            y=y_column, 
            title=title,
            labels={x_column: x_column.replace('_', ' ').title(), 
                    y_column: y_column.replace('_', ' ').title()},
            color=y_column,
            color_continuous_scale='viridis'
        )
    
    elif viz_instruction.visualization_type == 'scatter_plot':
        # Check if there's a third column for color/size
        color_column = viz_instruction.additional_instructions.get('color_column')
        size_column = viz_instruction.additional_instructions.get('size_column')
        
        fig = px.scatter(
            df, 
            x=x_column, 
            y=y_column, 
            title=title,
            labels={x_column: x_column.replace('_', ' ').title(), 
                    y_column: y_column.replace('_', ' ').title()},
            color=color_column if color_column in df.columns else None,
            size=size_column if size_column in df.columns else None,
            hover_data=df.columns.tolist()
        )
    
    elif viz_instruction.visualization_type == 'line_chart':
        fig = px.line(
            df, 
            x=x_column, 
            y=y_column, 
            title=title,
            labels={x_column: x_column.replace('_', ' ').title(), 
                    y_column: y_column.replace('_', ' ').title()},
            markers=True
        )
    
    elif viz_instruction.visualization_type == 'pie_chart':
        fig = px.pie(
            df, 
            names=x_column, 
            values=y_column, 
            title=title
        )
    
    # Additional styling
    fig.update_layout(
        height=600,
        width=800,
        template='plotly_white'
    )
    
    return fig

def create_map_visualization(df, viz_instructions):
    
    lat_column = viz_instructions.get('latitude_column', 'latitude')
    lon_column = viz_instructions.get('longitude_column', 'longitude')
    kinerja_column = viz_instructions.get('kinerja_column', 'nilai_kinerja')
    
    if lat_column not in df.columns or lon_column not in df.columns:
        st.error("Kolom latitude atau longitude tidak ditemukan")
        return None
    
    if kinerja_column not in df.columns:
        st.error("Kolom nilai kinerja tidak ditemukan")
        return None
            
    df[lat_column] = pd.to_numeric(df[lat_column], errors='coerce')
    df[lon_column] = pd.to_numeric(df[lon_column], errors='coerce')
    df[kinerja_column] = pd.to_numeric(df[kinerja_column], errors='coerce')
    df = df.dropna(subset=[lat_column, lon_column, kinerja_column])
    
    # Apply filtering if specified in visualization instructions
    if 'filter' in viz_instructions:
        filter_config = viz_instructions['filter']
        if 'limit' in filter_config:
            limit_config = filter_config['limit']
            if limit_config['type'] == 'top':
                # Get top N performers
                n = limit_config.get('value', 1)
                df = df.nlargest(n, kinerja_column)
                # Adjust view state to focus on filtered data
                initial_zoom = 13 if n == 1 else 11
            elif limit_config['type'] == 'bottom':
                n = limit_config.get('value', 1)
                df = df.nsmallest(n, kinerja_column)
                initial_zoom = 13 if n == 1 else 11
    else:
        initial_zoom = 11
    
    if df.empty:
        st.error("Tidak ada data valid untuk divisualisasikan.")
        return None
    
    # Definisikan batas nilai untuk kategorisasi kinerja
    COLOR_RANGES = [
        {'min': 0, 'max': 350, 'color': [255, 0, 0, 255]},      # Merah untuk 0-249
        {'min': 351, 'max': 599, 'color': [255, 255, 0, 255]},  # Kuning untuk 401-500
        {'min': 600, 'max': 1000, 'color': [0, 255, 0, 255]}    # Hijau untuk 501-1000
    ]
    
    # # Fungsi untuk mendapatkan warna berdasarkan nilai kinerja
    def get_color_by_value(value):
        for range_info in COLOR_RANGES:
            if range_info['min'] <= value <= range_info['max']:
                return range_info['color']
        return [128, 128, 128, 255]  # Default abu-abu jika di luar rentang
    
    df['color'] = df[kinerja_column].apply(get_color_by_value)
    
    # Buat array warna untuk colorRange HexagonLayer
    color_domain = [0, 800, 900, 1000]  # Definisi batas-batas nilai
    color_range = [
        [255, 0, 0, 255],    # Merah
        [255, 255, 0, 255],  # Kuning
        [0, 255, 0, 255],    # Hijau
    ]
    
    df['hover_info'] = df.apply(lambda row: {
        'nama': str(row.get('nama', 'Tidak tersedia')),
        'alamat': str(row.get('alamat', 'Tidak tersedia')),
        'nama_jabatan': str(row.get('nama_jabatan', 'Tidak tersedia')),
        'nama_departemen': str(row.get('nama_departemen', 'Tidak tersedia')),
        'nilai_kinerja': str(row.get('nilai_kinerja', 'Tidak tersedia')),
        'jumlah_proyek': str(row.get('jumlah_proyek', 'Tidak tersedia'))
    }, axis=1)
    
    print("Hover Info Sample:")
    print(df['hover_info'])
    
    view_state = pdk.ViewState(
        latitude=df[lat_column].mean(),
        longitude=df[lon_column].mean(),
        zoom=11,
        max_zoom=15,
        pitch=30,
    )
    
    layer = [
        pdk.Layer(
            "HexagonLayer",
            data=df,
            get_position=f"[{lon_column}, {lat_column}]",
            auto_highlight=True,
            elevation_scale=2,
            elevation_range=[0, 2000],
            get_color_weight=f"{kinerja_column}",
            extruded=True,
            coverage=2, 
            get_elevation_weight=f"{kinerja_column}",
            radius=500,
            stroked=True,
            colorRange=color_range,
            colorDomain=color_domain,
            material={"material": True, "ambient": 0.64, "roughness": 0.85},
        ),
        pdk.Layer(
            "ScatterplotLayer",
            df,
            get_position='[longitude, latitude]',
            get_color="color",
            elevation_scale=10,
            get_radius=100,
            pickable=True,
            opacity=0.8,
            radiusScale=5,
            radiusMinPixels=5,
            radiusMaxPixels=100,
        )
    ]
    
    if len(df) <= 5:  # Only show labels for small number of points
        layer.append(
            pdk.Layer(
                "TextLayer",
                df,
                get_position=f"[{lon_column}, {lat_column}]",
                get_text="nama",
                get_size=16,
                get_color=[0, 0, 0, 255],
                get_angle=0,
                text_anchor="middle",
                text_baseline="bottom",
                pick_enable=False,
                offset=[0, -20]
            )
        )
    
    tooltip_html = """
        <div style="background-color: steelblue; color: white; padding: 10px; border-radius: 5px;">
            <b>Nama:</b> {nama}<br>
            <b>Alamat:</b> {alamat}<br>
            <b>Jabatan:</b> {nama_jabatan}<br>
            <b>Departemen:</b> {nama_departemen}<br>
            <b>Nilai Kinerja:</b> {nilai_kinerja}<br>
            <b>Jumlah Pekerjaan:</b> {jumlah_proyek}
        </div>
    """
    
    return pdk.Deck(
        layers=layer,
        initial_view_state=view_state,
        tooltip={"html": tooltip_html},
        # map_style="mapbox://styles/mapbox/streets-v11"
        map_style="mapbox://styles/mapbox/light-v9"
    )

# Template Prompt untuk Model
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """
        You are an advanced AI data visualization assistant. 
        Given a dataset and a user question, generate precise visualization instructions.
            {{
                "type": "visualization",
                "chart_type": "bar|line|scatter|pie|histogram|map",
                "title": "Judul yang Deskriptif",
                "description": "Analisis detail tentang visualisasi",
                
                "x_column": "nama_kolom",
                "y_column": "nama_kolom",
                
                "value_column": "nama_kolom",
                "names_column": "nama_kolom",
                
                "value_column": "nama_kolom",
                "bins": jumlah_bins, // opsional
                
                "aggregation": {{
                    "type": "count|sum|mean|median",
                    "column": "nama_kolom"
                }},
                
                "filter": {{
                    "conditions": [
                        {{
                            "column": "nama_kolom",
                            "operation": ">|>=|<|<=|==|contains|in",
                            "value": nilai_yang_sesuai
                        }}
                    ],
                    "limit": {{
                        "type": "top|bottom",
                        "value": jumlah_data,
                        "sort_column": "nama_kolom"
                    }}
                }},
                
                "transform": {{
                    "type": "group|pivot|melt",
                    "by": ["kolom1", "kolom2"],
                    "agg_function": "count|sum|mean"
                }}
            }}
            
            Petunjuk khusus untuk jenis-jenis pertanyaan:
            
            1. Untuk pertanyaan tentang nilai tertinggi/terendah:
            - Gunakan filter dengan limit
            - Tentukan sort_column yang relevan
            - Pilih chart_type yang sesuai (bar untuk perbandingan, pie untuk proporsi)
            
            2. Untuk pertanyaan tentang distribusi:
            - Gunakan histogram untuk data numerik kontinyu
            - Gunakan bar chart untuk data kategorik
            - Sertakan aggregation jika diperlukan
            
            3. Untuk pertanyaan tentang persentase:
            - Gunakan pie chart
            - Pastikan value_column dan names_column sesuai
            - Tambahkan transformasi data jika diperlukan
            
            4. Untuk pertanyaan tentang perbandingan antar kategori:
            - Gunakan bar chart
            - Sertakan agregasi yang sesuai
            - Tentukan x_column (kategori) dan y_column (nilai) dengan benar
            
            5. Untuk pertanyaan tentang tren:
            - Gunakan line chart
            - Urutkan data berdasarkan waktu/urutan yang sesuai
            
        IMPORTANT: Always respond in strict JSON format:
        {{  
            1. Untuk visualisasi gaji tiap pegawai:
            {{
                "type": "visualization",
                "chart_type": "bar",
                "title": "Gaji dan Jumlah Pegawai",
                "x_column": "nama_jabatan",
                "y_column": "gaji",
                "transform": {{
                    "type": "group",
                    "by": ["nama_jabatan"],
                    "agg_function": "count"
                }}
            }}
            
            2. Untuk visualisasi distribusi umur:
            {{
                "type": "visualization",
                "chart_type": "line",
                "title": "Distribusi Umur Pegawai",
                "x_column": "nama_kolom",
                "y_column": "nama_kolom",
                "filter": {{
                    "limit": {{
                        "type": "both",
                        "value": 10,
                        "sort_column": "umur"
                    }}
                }}
            }}
            
            3. Untuk visualisasi jumlah pegawai per departemen:
            {{
                "type": "visualization",
                "chart_type": "bar",
                "title": "Jumlah Pegawai per Departemen",
                "transform": {{
                    "type": "group",
                    "by": ["nama_departemen"],
                    "agg_function": "count"
                }},
                "x_column": "nama_departemen",
                "y_column": "count"
            }}
            
            {{
                "type": "visualization",
                "chart_type": "map",
                "title": "Visualisasi Lokasi Pegawai",
                "latitude_column": "latitude",
                "longitude_column": "longitude",
                "names_column": "nama_kolom",
                "filter": {{
                    "limit": {{
                        "type": "top",
                        "value": 1,
                        "sort_column": "nama_kolom"
                    }}
                }}
            }}
        }}

        Available Columns: {columns}
        
        Visualization Guidelines:
        - Choose columns that directly answer the user's question
        - Ensure columns exist in the dataset
        - Select most meaningful visualization type
        """),
        ("human", "User Question: {question}")
])

def fallback_visualization(df, user_prompt):
    """Fallback visualization jika AI gagal membuat instruksi"""
    st.warning("Tidak dapat membuat visualisasi otomatis. Membuat visualisasi default.")
    
    # Visualisasi default berdasarkan tipe data
    numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns
    categorical_columns = df.select_dtypes(include=['object', 'category']).columns
    
    if len(numeric_columns) >= 2:
        # Scatter plot dengan kolom numerik pertama
        fig = px.scatter(
            df, 
            x=numeric_columns[0], 
            y=numeric_columns[1], 
            title=f"Scatter Plot: {numeric_columns[0]} vs {numeric_columns[1]}"
        )
        st.plotly_chart(fig, use_container_width=True)
    elif len(categorical_columns) > 0 and len(numeric_columns) > 0:
        # Bar chart dengan kolom kategorik dan numerik
        fig = px.bar(
            df, 
            x=categorical_columns[0], 
            y=numeric_columns[0], 
            title=f"Bar Chart: {categorical_columns[0]} by {numeric_columns[0]}"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Tidak dapat membuat visualisasi dengan dataset yang tersedia.")

# Streamlit App
st.set_page_config(layout="wide")
def main():
    st.title("🤖 Dynamic Generative Business Intelligence")
    
    # Fetch data
    df = fetch_data()
    
    if df.empty:
        st.error("No data available. Please check your API connection.")
        return
    
    # User Input
    user_prompt = st.text_input("Ask a question about your data and get a visualization:")
    
    if st.button("Generate Visualization"):
        with st.spinner("Generating Intelligent Visualization..."):
            try:
                # LLM Configuration
                llm = ChatOllama(model="llama3.2-vision")
                
                # Create processing chain
                chain = prompt | llm | StrOutputParser()
                viz_instruction_str = chain.invoke({
                    'columns': ', '.join(df.columns), 
                    'question': user_prompt,
                })
                
                # In your main function, before parsing
                print("Raw LLM Response:", viz_instruction_str)
                
                try:
                    viz_instruction = parse_visualization_instruction(viz_instruction_str)
                    
                    if viz_instruction is None:
                        fallback_visualization(df, user_prompt)
                        return
                
                    # Cetak instruksi untuk debugging
                    st.write("Visualization Instruction:", viz_instruction)
                    
                    # Proses visualisasi
                    chart_type = viz_instruction.get('chart_type', 'bar')
                    
                    if chart_type in ['bar', 'scatter', 'line', 'pie']:
                        # Sesuaikan mapping nama chart
                        plotly_type = {
                            'bar': 'bar_chart',
                            'scatter': 'scatter_plot',
                            'line': 'line_chart',
                            'pie': 'pie_chart'
                        }.get(chart_type, 'bar_chart')
                        
                        # Buat objek sederhana untuk visualisasi
                        viz_obj = type('VizObj', (), {
                            'visualization_type': plotly_type,
                            'x_column': viz_instruction.get('x_column', df.columns[0]),
                            'y_column': viz_instruction.get('y_column', df.columns[1] if len(df.columns) > 1 else df.columns[0]),
                            'title': viz_instruction.get('title', 'Data Visualization'),
                            'additional_instructions': viz_instruction.get('additional_instructions', {})
                        })
                        
                        fig = create_dynamic_visualization(df, viz_obj)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == 'map':
                        map_chart = create_map_visualization(df, viz_instruction)
                        if map_chart:
                            st.pydeck_chart(map_chart)
                        else:
                            fallback_visualization(df, user_prompt)
                    
                    else:
                        fallback_visualization(df, user_prompt)
                
                except Exception as e:
                    st.warning(f"Gagal membuat visualisasi AI: {e}")
                    fallback_visualization(df, user_prompt)
            
            except Exception as e:
                st.error(f"Error umum: {e}")
                fallback_visualization(df, user_prompt)

if __name__ == "__main__":
    main()