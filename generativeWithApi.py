import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
import json
import pydeck as pdk
import requests
import plotly.express as px
import numpy as np
import re
from datetime import datetime

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
            df= pd.json_normalize(data['data'])
            df, numeric_columns = prepare_numeric_columns(df)
            st.session_state['numeric_columns'] = numeric_columns
            
            return df
        else:
            st.error("Data tidak ditemukan dalam respons API")
            return None
    except requests.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
        return None

def preprocess_dataframe(df):
    """
    Fungsi preprocessing yang lebih robust untuk mempersiapkan DataFrame
    """
    df = df.copy()
    
    # Deteksi kolom numerik
    numeric_columns = []
    for col in df.columns:
        try:
            # Bersihkan string numerik dari karakter khusus
            if df[col].dtype == object:
                df[col] = df[col].str.replace(r'[^\d.-]', '', regex=True)
            # Konversi ke numerik
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if not df[col].isna().all():  # Pastikan tidak semua nilai NaN
                numeric_columns.append(col)
        except:
            continue
    
    # Simpan kolom numerik di session state
    st.session_state['numeric_columns'] = numeric_columns
    
    # Deteksi dan konversi kolom tanggal
    date_columns = []
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                df[col] = pd.to_datetime(df[col])
                date_columns.append(col)
            except:
                continue
    
    st.session_state['date_columns'] = date_columns
    
    return df

def detect_numeric_columns(df):
    """
    Mendeteksi kolom yang berpotensi berisi data numerik
    """
    numeric_columns = []
    for col in df.columns:
        # Cek apakah kolom sudah bertipe numerik
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_columns.append(col)
            continue
            
        # Jika kolom bertipe object/string, cek apakah bisa dikonversi ke numerik
        if df[col].dtype == object:
            # Ambil sample non-null untuk pengujian
            sample = df[col].dropna().head(100)
            if len(sample) == 0:
                continue
                
            # Coba konversi sample ke numerik
            try:
                # Bersihkan string dari karakter non-numerik
                cleaned = sample.astype(str).str.replace(r'[^\d.-]', '', regex=True)
                pd.to_numeric(cleaned, errors='raise')
                numeric_columns.append(col)
            except:
                continue
                
    return numeric_columns

def prepare_numeric_columns(df):
    """
    Mempersiapkan kolom numerik dengan penanganan error yang lebih baik
    """
    # Buat copy dari DataFrame untuk menghindari modifikasi data asli
    df_processed = df.copy()
    
    # Deteksi kolom numerik
    numeric_columns = detect_numeric_columns(df)
    
    # Proses setiap kolom numerik
    for col in numeric_columns:
        try:
            # Simpan nilai original
            df_processed[f'{col}_original'] = df_processed[col].copy()
            
            # Jika kolom bertipe object, lakukan pembersihan
            if df_processed[col].dtype == object:
                # Bersihkan string dari karakter non-numerik
                cleaned_values = df_processed[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                # Konversi ke numerik
                df_processed[col] = pd.to_numeric(cleaned_values, errors='coerce')
            else:
                # Coba konversi langsung untuk tipe data non-object
                df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
            
            # Jika hasil konversi menghasilkan semua NaN, kembalikan ke nilai original
            if df_processed[col].isna().all():
                df_processed[col] = df_processed[f'{col}_original']
                numeric_columns.remove(col)
            
            # Hapus kolom temporary
            df_processed.drop(f'{col}_original', axis=1, inplace=True)
            
        except Exception as e:
            st.warning(f"Error saat memproses kolom {col}: {str(e)}")
            numeric_columns.remove(col)
            continue
    
    return df_processed, numeric_columns

def create_enhanced_filter(df, filter_instructions):
    """
    Fungsi filter yang ditingkatkan dengan validasi dan penanganan error yang lebih baik
    """
    try:
        df_filtered = df.copy()
        
        # Terapkan filter kondisional jika ada
        if 'conditions' in filter_instructions:
            for condition in filter_instructions['conditions']:
                column = condition.get('column')
                operation = condition.get('operation')
                value = condition.get('value')
                
                if not all([column, operation, value is not None]) or column not in df_filtered.columns:
                    continue
                
                try:
                    if operation in ['>', '>=', '<', '<=', '==']:
                        df_filtered[column] = pd.to_numeric(df_filtered[column], errors='coerce')
                        if isinstance(value, str):
                            value = float(value.replace(',', ''))
                    
                    if operation == '>':
                        df_filtered = df_filtered[df_filtered[column] > value]
                    elif operation == '>=':
                        df_filtered = df_filtered[df_filtered[column] >= value]
                    elif operation == '<':
                        df_filtered = df_filtered[df_filtered[column] < value]
                    elif operation == '<=':
                        df_filtered = df_filtered[df_filtered[column] <= value]
                    elif operation == '==':
                        df_filtered = df_filtered[df_filtered[column] == value]
                    elif operation == 'contains':
                        df_filtered = df_filtered[df_filtered[column].astype(str).str.contains(str(value), case=False, na=False)]
                except Exception as e:
                    st.warning(f"Error applying filter on column {column}: {str(e)}")
                    continue
        
        # Terapkan limit jika ada
        if 'limit' in filter_instructions:
            limit_config = filter_instructions['limit']
            limit_type = limit_config.get('type')
            limit_value = limit_config.get('value')
            sort_column = limit_config.get('sort_column')
            
            if all([limit_type, limit_value, sort_column]) and sort_column in df_filtered.columns:
                try:
                    df_filtered[sort_column] = pd.to_numeric(df_filtered[sort_column], errors='coerce')
                    if limit_type == 'top':
                        df_filtered = df_filtered.nlargest(limit_value, sort_column)
                    elif limit_type == 'bottom':
                        df_filtered = df_filtered.nsmallest(limit_value, sort_column)
                except Exception as e:
                    st.warning(f"Error applying limit on column {sort_column}: {str(e)}")
        
        if df_filtered.empty:
            st.warning("Filter resulted in empty dataset")
            return df
            
        return df_filtered
        
    except Exception as e:
        st.error(f"Error in filter application: {str(e)}")
        return df

def get_improved_system_message():
    """
    Sistem prompt yang lebih baik untuk menghasilkan respons yang lebih akurat
    """
    return """
    Anda adalah asisten AI ahli dalam analisis data dan visualisasi.
    
    Saat memberikan instruksi visualisasi, pastikan untuk:
    1. Memvalidasi tipe data yang sesuai untuk setiap jenis visualisasi
    2. Memberikan filter yang spesifik dan sesuai dengan tipe data
    3. Memberikan deskripsi yang detail dan informatif
    4. Memastikan konsistensi antara tipe chart dan data yang digunakan
    
    Format respons untuk visualisasi harus mengikuti struktur berikut:
    {
        "type": "visualization",
        "chart_type": "bar|line|scatter|pie|map",
        "title": "Judul yang Deskriptif",
        "description": "Analisis detail tentang visualisasi",
        "x_column": "nama_kolom" (untuk chart bar/line/scatter),
        "y_column": "nama_kolom" (untuk chart bar/line/scatter),
        "value_column": "nama_kolom" (untuk pie chart),
        "names_column": "nama_kolom" (untuk pie chart),
        "filter": {
            "conditions": [
                {
                    "column": "nama_kolom",
                    "operation": ">|>=|<|<=|==|contains",
                    "value": nilai_yang_sesuai
                }
            ],
            "limit": {
                "type": "top|bottom",
                "value": jumlah_data,
                "sort_column": "nama_kolom"
            }
        }
    }
    
    Ketika user meminta untuk menampilkan sejumlah data tertentu:
    1. Selalu sertakan konfigurasi "limit" dalam filter
    2. Pastikan "sort_column" sesuai dengan kolom yang akan diurutkan
    3. Gunakan "top" untuk nilai tertinggi dan "bottom" untuk nilai terendah
    4. "value" harus berupa angka sesuai jumlah data yang diminta
    
    Contoh untuk menampilkan 3 data tertinggi:
    {
        "type": "visualization",
        "chart_type": "bar",
        "title": "3 Data Tertinggi",
        "x_column": "nama",
        "y_column": "nilai",
        "filter": {
            "limit": {
                "type": "top",
                "value": 3,
                "sort_column": "nilai"
            }
        }
    }
    
    Untuk visualisasi peta, gunakan format:
    {
        "type": "visualization",
        "chart_type": "map",
        "title": "Judul Peta",
        "description": "Deskripsi detail",
        "latitude_column": "latitude",
        "longitude_column": "longitude"
    }
    
    Available filter operations:
    - Numeric comparisons: >, >=, <, <=, ==, !=
    - Text operations: contains, starts_with, ends_with
    - List operation: in (value should be a list)
    
    For map visualizations, use:
    {
        "type": "visualization",
        "chart_type": "map",
        "title": "Map Title",
        "description": "Detailed description",
        "latitude_column": "latitude",
        "longitude_column": "longitude",
        "filter": {
            "conditions": [
                {
                    "column": "column_name",
                    "operation": "operation",
                    "value": value
                }
            ],
            "limit": {
                "type": "top|bottom",
                "value": jumlah_data,
                "sort_column": "nama_kolom"
            }
        }
    }
    Untuk visualisasi peta, gunakan format yang sama dengan penambahan:
    {
        "type": "visualization",
        "chart_type": "map",
        "title": "Judul Peta",
        "description": "Deskripsi detail",
        "latitude_column": "latitude",
        "longitude_column": "longitude"
    }
    
    Available filter operations:
    - Numeric comparisons: >, >=, <, <=, ==, !=
    - Text operations: contains, starts_with, ends_with
    - List operation: in (value should be a list)
    
    Limit options:
    - "type": "top" untuk N tertinggi
    - "type": "bottom" untuk N terendah
    - "value": jumlah data yang diinginkan
    - "sort_column": kolom yang digunakan untuk pengurutan
    
    Pastikan semua kolom yang direferensikan ada dalam dataset.
    """

# Fungsi untuk menganalisis permintaan pengguna menggunakan OpenAI Assistant
def analyze_user_request(df, user_query):
    """
    Fungsi analisis permintaan pengguna yang ditingkatkan
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": get_improved_system_message()},
                {"role": "user", "content": f"Data memiliki kolom: {', '.join(df.columns)}. {user_query}"}
            ]
        )
        
        result = response.choices[0].message.content
        
        # Validasi hasil JSON
        try:
            parsed_result = json.loads(result)
            # Validasi struktur respons
            if parsed_result['type'] not in ['visualization', 'analysis']:
                raise ValueError("Tipe respons tidak valid")
                
            return result
            
        except json.JSONDecodeError:
            return json.dumps({
                "type": "error",
                "message": "Format respons tidak valid"
            })
            
    except Exception as e:
        return json.dumps({
            "type": "error",
            "message": f"Error dalam pemrosesan permintaan: {str(e)}"
        })

# Fungsi untuk memfilter data berdasarkan instruksi
def filter_data(df, filter_instructions):
    """
    Fungsi filter yang ditingkatkan dengan validasi yang lebih baik
    """
    if not filter_instructions or not isinstance(filter_instructions, dict):
        return df
    
    try:
        filtered_df = df.copy()
        
        # Pastikan ada conditions dalam filter
        conditions = filter_instructions.get('conditions', [])
        if not conditions or not isinstance(conditions, list):
            return df
            
        # Terapkan setiap kondisi filter
        for condition in conditions:
            if not isinstance(condition, dict):
                continue
                
            column = condition.get('column')
            operation = condition.get('operation')
            value = condition.get('value')
            
            # Validasi parameter filter
            if not all([column, operation, value is not None]):
                continue
            
            if column not in filtered_df.columns:
                continue
            
            # Konversi kolom ke numerik jika diperlukan
            if operation in ['>', '>=', '<', '<=', '==']:
                try:
                    filtered_df[column] = pd.to_numeric(filtered_df[column], errors='coerce')
                    if isinstance(value, str):
                        value = float(value.replace(',', ''))
                except:
                    continue
            
            # Terapkan filter berdasarkan operasi
            try:
                if operation == '>':
                    filtered_df = filtered_df[filtered_df[column] > value]
                elif operation == '>=':
                    filtered_df = filtered_df[filtered_df[column] >= value]
                elif operation == '<':
                    filtered_df = filtered_df[filtered_df[column] < value]
                elif operation == '<=':
                    filtered_df = filtered_df[filtered_df[column] <= value]
                elif operation == '==':
                    filtered_df = filtered_df[filtered_df[column] == value]
                elif operation == 'contains':
                    filtered_df = filtered_df[filtered_df[column].astype(str).str.contains(str(value), case=False, na=False)]
            except Exception as e:
                st.warning(f"Error saat menerapkan filter pada kolom {column}: {str(e)}")
                continue
        
        # Jika hasil filter kosong, kembalikan DataFrame original
        if filtered_df.empty:
            st.warning("Filter menghasilkan dataset kosong. Mengembalikan data original.")
            return df
            
        return filtered_df
        
    except Exception as e:
        st.error(f"Error dalam penerapan filter: {str(e)}")
        return df

# Fungsi asisten untuk pertanyaan umum dan terkait data
def question_assistant(data, user_question):
    system_message = f"""
    Anda adalah asisten AI yang ahli dalam analisis data dan menjawab pertanyaan umum.
    Data yang tersedia:
    {data.to_json(orient='records', lines=True)}
    
    Kolom yang tersedia: {', '.join(data.columns)}
    
    Tugas Anda adalah menjawab pertanyaan kritis pengguna berdasarkan data yang tersedia atau pengetahuan umum.
    Berikan jawaban yang informatif, akurat, relevan dan hasil yang memuaskan.
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

def apply_limit_to_data(df, limit_config):
    """
    Fungsi baru untuk menerapkan limit pada dataset
    """
    try:
        if not limit_config or not isinstance(limit_config, dict):
            return df
            
        limit_type = limit_config.get('type')
        limit_value = limit_config.get('value')
        sort_column = limit_config.get('sort_column')
        
        if not all([limit_type, limit_value, sort_column]):
            return df
            
        if sort_column not in df.columns:
            st.warning(f"Kolom pengurutan '{sort_column}' tidak ditemukan")
            return df
            
        # Konversi kolom ke numerik jika belum
        if df[sort_column].dtype not in ['int64', 'float64']:
            df[sort_column] = pd.to_numeric(df[sort_column], errors='coerce')
            
        # Hapus baris dengan nilai NaN setelah konversi
        df = df.dropna(subset=[sort_column])
        
        # Terapkan pengurutan dan limit
        if limit_type.lower() == 'top':
            return df.nlargest(int(limit_value), sort_column).reset_index(drop=True)
        elif limit_type.lower() == 'bottom':
            return df.nsmallest(int(limit_value), sort_column).reset_index(drop=True)
            
        return df
        
    except Exception as e:
        st.error(f"Error dalam menerapkan limit: {str(e)}")
        return df

# Fungsi untuk membuat visualisasi
def create_visualization(df, viz_instructions):
    """
    Fungsi visualisasi yang ditingkatkan dengan penanganan filter yang lebih baik
    """
    try:
        df_viz = df.copy()
        
        # Terapkan filter jika ada
        if 'filter' in viz_instructions:
            # Cek dan terapkan conditions jika ada
            if viz_instructions['filter'].get('conditions'):
                df_viz = create_enhanced_filter(df_viz, viz_instructions['filter'])
            
            # Terapkan limit jika ada, terlepas dari ada tidaknya conditions
            if viz_instructions['filter'].get('limit'):
                df_viz = apply_limit_to_data(df_viz, viz_instructions['filter']['limit'])
        
        if df_viz.empty:
            st.warning("Tidak ada data yang memenuhi kriteria filter")
            return
            
        chart_type = viz_instructions['chart_type']
        title = viz_instructions.get('title', 'Visualisasi')
        
        # Display filter summary if filters were applied
        if 'filter' in viz_instructions:
            st.subheader("Applied Filters:")
            # Tampilkan conditions jika ada
            if viz_instructions['filter'].get('conditions'):
                for condition in viz_instructions['filter']['conditions']:
                    st.write(f"- {condition['column']} {condition['operation']} {condition['value']}")
            
            # Tampilkan limit jika ada
            if viz_instructions['filter'].get('limit'):
                limit = viz_instructions['filter']['limit']
                st.write(f"- Showing {limit['value']} {limit['type']} records sorted by {limit['sort_column']}")
        
        if chart_type == 'map':
            map_chart = create_map_visualization(df_viz, viz_instructions)
            if map_chart:
                st.pydeck_chart(map_chart)
        
        elif chart_type in ['bar', 'line', 'scatter']:
            x_col = viz_instructions.get('x_column')
            y_col = viz_instructions.get('y_column')
            
            if not x_col or not y_col or x_col not in df_viz.columns or y_col not in df_viz.columns:
                st.error(f"Kolom yang diperlukan tidak ditemukan: {x_col} atau {y_col}")
                return
                
            # Pastikan data numerik valid untuk sumbu y
            df_viz[y_col] = pd.to_numeric(df_viz[y_col], errors='coerce')
            df_viz = df_viz.dropna(subset=[y_col])
            
            if chart_type == 'bar':
                fig = px.bar(df_viz, x=x_col, y=y_col, title=title)
            elif chart_type == 'line':
                fig = px.line(df_viz, x=x_col, y=y_col, title=title)
            else:  # scatter
                fig = px.scatter(df_viz, x=x_col, y=y_col, title=title)
            
            fig.update_layout(
                title_x=0.5,
                margin=dict(t=100),
                xaxis_title=x_col,
                yaxis_title=y_col
            )
            
            # Kustomisasi tampilan
            # fig.update_traces(
            #     texttemplate='%{text:.2f}',
            #     textposition='outside'
            # )
            
            st.plotly_chart(fig, use_container_width=True)
            
        elif chart_type == 'pie':
            values = viz_instructions.get('value_column')
            names = viz_instructions.get('names_column')
            
            if not values or not names or values not in df_viz.columns or names not in df_viz.columns:
                st.error("Kolom yang diperlukan untuk pie chart tidak ditemukan")
                return
                
            df_viz[values] = pd.to_numeric(df_viz[values], errors='coerce')
            df_viz = df_viz.dropna(subset=[values])
            
            fig = px.pie(df_viz, values=values, names=names, title=title)
            st.plotly_chart(fig, use_container_width=True)
            
        # Tampilkan deskripsi dan data
        if 'description' in viz_instructions:
            st.markdown("### Analisis")
            st.write(viz_instructions['description'])
            
        st.markdown("### Data yang Divisualisasikan:")
        st.dataframe(df_viz)
        
    except Exception as e:
        st.error(f"Error dalam pembuatan visualisasi: {str(e)}")


# def clean_and_prepare_data(df):
#     # Konversi latitude dan longitude ke float, ganti nilai null dengan NaN
#     df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
#     df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
#     # Hapus baris dengan nilai NaN di latitude atau longitude
#     df = df.dropna(subset=['latitude', 'longitude'])
    
#     return df
# Fungsi untuk membuat visualisasi peta menggunakan pydeck
def create_map_visualization(df, viz_instructions):
    
    # df = clean_and_prepare_data(df)
    
    lat_column = viz_instructions.get('latitude_column', 'latitude')
    lon_column = viz_instructions.get('longitude_column', 'longitude')
    
    if lat_column not in df.columns or lon_column not in df.columns:
            st.error("Kolom latitude atau longitude tidak ditemukan")
            return None
            
    # Konversi ke numerik dan bersihkan data
    df[lat_column] = pd.to_numeric(df[lat_column], errors='coerce')
    df[lon_column] = pd.to_numeric(df[lon_column], errors='coerce')
    df = df.dropna(subset=[lat_column, lon_column])
    
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
                # st.write(ai_response['description'])
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

