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
        
        # Proses untuk mengekstrak JSON dengan lebih robust
        start = text.find('{')
        end = text.rfind('}')
        
        if start == -1 or end == -1:
            st.error("Tidak dapat menemukan struktur JSON yang valid")
            return None
        
        text = text[start:end+1]
        
        # Parse JSON dari teks
        parsed_json = json.loads(text)
        
        # Validasi struktur JSON
        if not isinstance(parsed_json, dict) or 'type' not in parsed_json:
            st.error("Struktur JSON tidak sesuai format yang diharapkan")
            return None
        
        return parsed_json
    
    except json.JSONDecodeError as e:
        st.error(f"Gagal parsing JSON: {e}")
        st.error(f"Raw text received: {text}")
        return None
    except Exception as e:
        st.error(f"Error umum dalam parsing: {e}")
        return None

# Advanced Visualization Functions with Plotly
def transform_data(df, transform_config):
    """
    Fungsi untuk melakukan transformasi data
    """
    try:
        transform_type = transform_config.get('type')
        
        if transform_type == 'group':
            # Agregasi data berdasarkan kolom
            by_columns = transform_config.get('by', [])
            agg_function = transform_config.get('agg_function', 'count')
            
            if agg_function == 'count':
                df_transformed = df.groupby(by_columns).size().reset_index(name='count')
            elif agg_function in ['sum', 'mean', 'max', 'min', 'median']:
                df_transformed = df.groupby(by_columns).agg(
                    {by_columns[-1]: agg_function}
                ).reset_index()
            
            return df_transformed
        
        # Tambahkan jenis transformasi lain jika diperlukan
        return df
    
    except Exception as e:
        st.error(f"Error dalam transformasi data: {e}")
        return df

def create_enhanced_filter(df, filter_config):
    """ 
    Fungsi untuk membuat filter yang lebih kompleks
    """
    try:
        conditions = filter_config.get('conditions', [])
        
        for condition in conditions:
            column = condition.get('column')
            operation = condition.get('operation')
            value = condition.get('value')
            
            if column and operation and value is not None:
                if operation == '==':
                    df = df[df[column] == value]
                elif operation == '>':
                    df = df[df[column] > value]
                elif operation == '>=':
                    df = df[df[column] >= value]
                elif operation == '<':
                    df = df[df[column] < value]
                elif operation == '<=':
                    df = df[df[column] <= value]
                elif operation == 'contains':
                    df = df[df[column].str.contains(str(value), case=False)]
                elif operation == 'in':
                    df = df[df[column].isin(value)]
        
        return df
    
    except Exception as e:
        st.error(f"Error dalam filter data: {e}")
        return df

def apply_limit_to_data(df, limit_config):
    """
    Fungsi untuk membatasi dan mengurutkan data
    """
    try:
        limit_type = limit_config.get('type')
        limit_value = limit_config.get('value', 3)
        sort_column = limit_config.get('sort_column')
        
        if sort_column and sort_column in df.columns:
            # Konversi kolom ke numerik jika memungkinkan
            df[sort_column] = pd.to_numeric(df[sort_column], errors='coerce')
            
            if limit_type == 'top':
                df = df.sort_values(by=sort_column, ascending=False).head(limit_value)
            elif limit_type == 'bottom':
                df = df.sort_values(by=sort_column).head(limit_value)
        
        return df
    
    except Exception as e:
        st.error(f"Error dalam pembatasan data: {e}")
        return df

def create_dynamic_visualization(df, viz_instructions):
    """
    Fungsi visualisasi yang ditingkatkan dengan penanganan filter yang lebih baik
    """
    try:
        df_viz = df.copy()
        
        # Terapkan transformasi jika ada
        if 'transform' in viz_instructions:
            df_viz = transform_data(df_viz, viz_instructions['transform'])
        
        # Terapkan filter
        if 'filter' in viz_instructions:
            if viz_instructions['filter'].get('conditions'):
                df_viz = create_enhanced_filter(df_viz, viz_instructions['filter'])
            if viz_instructions['filter'].get('limit'):
                df_viz = apply_limit_to_data(df_viz, viz_instructions['filter']['limit'])
        
        if df_viz.empty:
            st.warning("Tidak ada data yang memenuhi kriteria")
            return None
        
        chart_type = viz_instructions['chart_type']
        title = viz_instructions.get('title', 'Visualisasi')
        
        # Handle agregasi jika diperlukan
        if 'aggregation' in viz_instructions:
            agg_config = viz_instructions['aggregation']
            agg_type = agg_config.get('type')
            agg_column = agg_config.get('column')
            
            if agg_type and agg_column:
                if agg_type == 'count':
                    df_viz = df_viz.groupby(agg_column).size().reset_index(name='count')
                else:
                    df_viz = df_viz.groupby(agg_column).agg({agg_column: agg_type}).reset_index()
        
        # Buat visualisasi sesuai tipe
        if chart_type == 'histogram':
            value_column = viz_instructions.get('value_column')
            bins = viz_instructions.get('bins', 30)
            
            if not value_column or value_column not in df_viz.columns:
                st.error("Kolom untuk histogram tidak ditemukan")
                return None
                
            fig = px.histogram(df_viz, x=value_column, nbins=bins, title=title)
            
        elif chart_type in ['bar', 'line', 'scatter']:
            x_col = viz_instructions.get('x_column')
            y_col = viz_instructions.get('y_column')
            
            if not x_col or not y_col or x_col not in df_viz.columns or y_col not in df_viz.columns:
                st.error("Kolom yang diperlukan tidak ditemukan")
                return None
                
            # Konversi dan bersihkan data numerik
            df_viz[y_col] = pd.to_numeric(df_viz[y_col], errors='coerce')
            df_viz = df_viz.dropna(subset=[y_col])
            
            # Urutkan data untuk visualisasi yang lebih baik
            df_viz = df_viz.sort_values(by=y_col, ascending=False)
            
            if chart_type == 'bar':
                fig = px.bar(
                    df_viz, 
                    x=x_col, 
                    y=y_col, 
                    title=title,
                    color=y_col,  # Warna berdasarkan nilai
                    color_continuous_scale='Viridis'
                )
                # Tambahkan label pada bar
                fig.update_traces(texttemplate='%{y}', textposition='outside')
            elif chart_type == 'line':
                fig = px.line(df_viz, x=x_col, y=y_col, title=title)
            else:  # scatter
                fig = px.scatter(df_viz, x=x_col, y=y_col, title=title)
                
            fig.update_layout(
                title_x=0.5,
                margin=dict(t=100),
                xaxis_title=x_col,
                yaxis_title=y_col,
                xaxis_tickangle=-45  # Putar label sumbu x
            )
            
        elif chart_type == 'pie':
            # Lebih fleksibel dalam menentukan kolom
            names_column = viz_instructions.get('names_column')
            value_column = viz_instructions.get('value_column')
            
            # Jika names_column belum tepat, lakukan deteksi
            if not names_column:
                categorical_columns = df.select_dtypes(include=['object', 'category']).columns
                if categorical_columns.size > 0:
                    names_column = categorical_columns[0]
            
            # Jika value_column belum tepat, gunakan default
            if not value_column:
                # Pilih kolom numerik atau gunakan count
                numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns
                if numeric_columns.size > 0:
                    value_column = numeric_columns[0]
                else:
                    # Transformasi default menggunakan count
                    df_viz = df_viz.groupby(names_column).size().reset_index(name='count')
                    names_column = names_column
                    value_column = 'count'
            else:
                # Transformasi sesuai instruksi
                transform_config = viz_instructions.get('transform', {
                    "type": "group", 
                    "by": [names_column], 
                    "agg_function": "count"
                })
                
                # Terapkan transformasi
                if transform_config['type'] == 'group':
                    agg_func = transform_config.get('agg_function', 'count')
                    
                    if agg_func == 'count':
                        df_viz = df_viz.groupby(names_column).size().reset_index(name='count')
                        value_column = 'count'
                    else:
                        # Agregasi berdasarkan fungsi yang ditentukan
                        df_viz = df_viz.groupby(names_column).agg({value_column: agg_func}).reset_index()
            
            # Validasi kolom
            if names_column not in df_viz.columns or value_column not in df_viz.columns:
                st.error(f"Kolom nama {names_column} atau value {value_column} tidak ditemukan")
                return None
            
            # Buat pie chart
            fig = px.pie(
                df_viz, 
                values=value_column, 
                names=names_column, 
                title=viz_instructions.get('title', 'Distribusi Data'),
                hole=0.3
            )
            
            fig.update_traces(
                texttemplate='%{label}<br>%{value} (%{percent})', 
                textposition='inside'
            )
            
            return fig
        else:
            st.error(f"Tipe chart {chart_type} tidak didukung")
            return None
        
        return fig
    
    except Exception as e:
        st.error(f"Error dalam pembuatan visualisasi: {str(e)}")
        return None

def create_map_visualization(df, viz_instructions):
    
    lat_column = viz_instructions.get('latitude_column', 'latitude')
    lon_column = viz_instructions.get('longitude_column', 'longitude')
    kinerja_column = viz_instructions.get('kinerja_column', 'nilai_kinerja')
    names_column = viz_instructions.get('names_column', 'nama')
    
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
            - SELALU gunakan filter dengan limit untuk membatasi data
            - Tentukan sort_column yang relevan
            - Pastikan data diurutkan dari tertinggi/terendah sebelum divisualisasikan
            
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
            Contoh JSON yang baik untuk top 3 kinerja:
            {{
                "type": "visualization",
                "chart_type": "bar",
                "title": "Top 3 Kinerja Pegawai",
                "x_column": "nama",
                "y_column": "nilai_kinerja",
                "filter": {{
                    "limit": {{
                        "type": "top",
                        "value": 3,
                        "sort_column": "nilai_kinerja"
                    }}
                }}
            }}
            
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

def generate_general_response(question):
    """
    Fungsi untuk menjawab pertanyaan umum menggunakan LLM
    """
    try:
        # Konfigurasi LLM untuk pertanyaan umum
        llm_general = ChatOllama(model="llama3.2-vision")
        
        # Template prompt untuk pertanyaan umum
        general_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            Kamu adalah asisten AI yang membantu menjawab pertanyaan dengan informatif dan ramah. 
            Jawab pertanyaan secara komprehensif, jelas, dan sesuai konteks.
            
            Beberapa panduan:
            - Berikan jawaban yang akurat dan dapat dimengerti
            - Gunakan bahasa yang mudah dipahami
            - Jika pertanyaan membutuhkan penjelasan teknis, sederhanakan
            - Berikan konteks tambahan jika diperlukan
            - Hindari jawaban yang bersifat spekulatif
            """),
            ("human", "Pertanyaan: {question}")
        ])
        
        # Buat chain untuk menjawab pertanyaan
        chain_general = general_prompt | llm_general | StrOutputParser()
        
        # Dapatkan respon
        response = chain_general.invoke({"question": question})
        
        return response
    except Exception as e:
        st.error(f"Gagal menghasilkan jawaban umum: {e}")
        return "Maaf, saya tidak dapat menjawab pertanyaan saat ini."

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
    # st.dataframe(df)
    
    if df.empty:
        st.error("No data available. Please check your API connection.")
        return

    st.header("Ajukan Pertanyaan")
    
    # Input untuk pertanyaan umum dan data
    question_type = st.radio(
        "Pilih Jenis Pertanyaan", 
        ["Pertanyaan Umum", "Pertanyaan Seputar Visualisasi Data"]
    )
    
    user_prompt = st.text_input("Tulis pertanyaan Anda:")
    
    if st.button("Dapatkan Jawaban"):
        with st.spinner("Memproses pertanyaan..."):
            if question_type == "Pertanyaan Umum":
                # Jawab pertanyaan umum
                general_answer = generate_general_response(user_prompt)
                st.write(general_answer)
            else:
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
                        
                        print("ini viz instruction", viz_instruction)
                        
                        if viz_instruction is None:
                            st.warning("Tidak dapat membuat instruksi visualisasi")
                            return
                    
                        # Cetak instruksi untuk debugging
                        st.write("Visualization Instruction:", viz_instruction)
                        
                        if viz_instruction['chart_type'] == 'map':
                            fig = create_map_visualization(df, viz_instruction)
                            if fig:
                                st.pydeck_chart(fig, use_container_width=True)
                                
                        # Proses visualisasi
                        fig = create_dynamic_visualization(df, viz_instruction)
                        
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Tampilkan deskripsi jika ada
                            if 'description' in viz_instruction:
                                st.markdown("### Analisis")
                                st.write(viz_instruction['description'])
                        else:
                            st.warning("Tidak dapat membuat visualisasi")
                    
                    except Exception as e:
                        st.warning(f"Gagal membuat visualisasi AI: {e}")
                        fallback_visualization(df, user_prompt)
                
                except Exception as e:
                    st.error(f"Error umum: {e}")
                    fallback_visualization(df, user_prompt)
if __name__ == "__main__":
    main()