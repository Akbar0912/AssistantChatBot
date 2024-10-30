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

# def detect_numeric_columns(df):
#     """
#     Mendeteksi kolom yang kemungkinan berisi data numerik
#     berdasarkan sampling dan pattern matching
#     """
#     potential_numeric_columns = []
    
#     for column in df.columns:
#         # Skip kolom yang sudah numerik
#         if pd.api.types.is_numeric_dtype(df[column]):
#             potential_numeric_columns.append(column)
#             continue
            
#         # Ambil sample non-null values
#         sample_values = df[column].dropna().head(100).astype(str)
        
#         if len(sample_values) == 0:
#             continue
        
#         # Pattern untuk mendeteksi string yang mungkin numerik
#         # Mencakup: angka biasa, format mata uang, persentase, dll
#         numeric_pattern = re.compile(r'^[Rp.,\s]*[\d.,]+[%]?$')
        
#         # Hitung berapa banyak nilai yang match dengan pattern
#         matches = sum(1 for val in sample_values if numeric_pattern.match(str(val).strip()))
        
#         # Jika lebih dari 80% sample match dengan pattern numerik
#         if matches / len(sample_values) > 0.8:
#             potential_numeric_columns.append(column)
    
#     return potential_numeric_columns

# def clean_numeric_string(value):
#     """
#     Membersihkan string menjadi nilai numerik
#     """
#     if pd.isna(value):
#         return np.nan
#     if isinstance(value, (int, float)):
#         return float(value)
    
#     try:
#         # Convert to string and clean
#         value_str = str(value)
        
#         # Remove currency symbols and common prefixes
#         value_str = re.sub(r'^[Rp\$€£¥]', '', value_str)
        
#         # Remove percentage signs
#         value_str = value_str.replace('%', '')
        
#         # Remove thousands separators and normalize decimal point
#         value_str = re.sub(r'[.,\s](?=\d{3})', '', value_str)
        
#         # Convert last comma to decimal point if present
#         if ',' in value_str and '.' not in value_str:
#             value_str = value_str.replace(',', '.')
        
#         # Remove any remaining non-numeric characters except decimal point
#         value_str = ''.join(char for char in value_str if char.isdigit() or char == '.')
        
#         # Convert to float
#         return float(value_str) if value_str else np.nan
#     except:
#         return np.nan

def prepare_numeric_columns(df):
    """
    Mempersiapkan kolom numerik dengan penanganan error yang lebih baik
    """
    numeric_columns = []
    df = df.copy()
    
    for col in df.columns:
        # Simpan data original
        original_values = df[col].copy()
        try:
            # Jika kolom berisi string, bersihkan karakter non-numerik
            if df[col].dtype == object:
                # Bersihkan string dari karakter khusus kecuali titik dan minus
                cleaned_values = df[col].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                # Konversi ke numerik
                df[col] = pd.to_numeric(cleaned_values, errors='coerce')
            else:
                # Coba konversi langsung untuk tipe data non-object
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Periksa apakah kolom memiliki nilai numerik valid
            if not df[col].isna().all() and df[col].notna().any():
                numeric_columns.append(col)
            else:
                # Kembalikan ke nilai original jika semua nilai NaN
                df[col] = original_values
        except Exception as e:
            # Kembalikan ke nilai original jika terjadi error
            df[col] = original_values
            continue
    
    return df, numeric_columns

# def parse_date(date_str):
#     """
#     Parse berbagai format tanggal yang mungkin diterima
#     """
#     try:
#         # Coba beberapa format tanggal umum
#         for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%Y%m%d'):
#             try:
#                 return pd.to_datetime(date_str, format=fmt)
#             except ValueError:
#                 continue
#         # Jika format di atas gagal, biarkan pandas mencoba parse secara otomatis
#         return pd.to_datetime(date_str)
#     except:
#         return None

def create_enhanced_filter(df, filter_instructions):
    """
    Fungsi filter yang lebih akurat dengan validasi yang lebih baik
    """
    if not filter_instructions or 'conditions' not in filter_instructions:
        return df
    
    try:
        df_filtered = df.copy()
        for condition in filter_instructions['conditions']:
            column = condition.get('column')
            operation = condition.get('operation')
            value = condition.get('value')
            
            if not column or column not in df.columns:
                continue
                
            # Konversi nilai ke numerik jika kolom numerik
            if column in st.session_state.get('numeric_columns', []):
                if isinstance(value, str):
                    try:
                        value = float(value.replace(',', ''))
                    except:
                        continue
                
                df_filtered[column] = pd.to_numeric(df_filtered[column], errors='coerce')
                
            # Aplikasikan filter
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
        
        return df_filtered
        
    except Exception as e:
        st.error(f"Error dalam penerapan filter: {str(e)}")
        return df

# def evaluate_complex_condition(df, condition):
#     """
#     Evaluasi kondisi kompleks dengan operator logika
#     """
#     if 'operator' in condition:
#         operator = condition['operator'].lower()
#         conditions = condition.get('conditions', [])
        
#         if not conditions:
#             return pd.Series(True, index=df.index)
        
#         if operator == 'and':
#             result = pd.Series(True, index=df.index)
#             for subcond in conditions:
#                 result &= evaluate_complex_condition(df, subcond)
#             return result
        
#         elif operator == 'or':
#             result = pd.Series(False, index=df.index)
#             for subcond in conditions:
#                 result |= evaluate_complex_condition(df, subcond)
#             return result
        
#         elif operator == 'not':
#             return ~evaluate_complex_condition(df, conditions[0])
        
#     else:
#         return apply_single_condition(df, condition)

# def apply_single_condition(df, condition):
#     """
#     Evaluasi kondisi tunggal dengan berbagai tipe operasi
#     """
#     column = condition.get('column')
#     operation = condition.get('operation')
#     value = condition.get('value')
#     # n = condition.get('n')
    
#     if not column or column not in df.columns:
#         return pd.Series(True, index=df.index)
    
#     try:
#         series = df[column]
#         # numeric_columns = st.session_state.get('numeric_columns', [])
        
#         # Handle numeric conversions more carefully
#         if operation in ['>', '>=', '<', '<=', '==', '!=']:
#             # Convert to numeric if needed
#             if not pd.api.types.is_numeric_dtype(series):
#                 series = pd.to_numeric(series, errors='coerce')
            
#             # Convert value to numeric if it's a string
#             if isinstance(value, str):
#                 try:
#                     value = float(value)
#                 except:
#                     pass
            
#             op_map = {
#                 '>': lambda x, y: x > y,
#                 '>=': lambda x, y: x >= y,
#                 '<': lambda x, y: x < y,
#                 '<=': lambda x, y: x <= y,
#                 '==': lambda x, y: x == y,
#                 '!=': lambda x, y: x != y
#             }
#             return op_map[operation](series, value)
        
#         # Handle string operations
#         elif operation == 'contains':
#             return series.astype(str).str.contains(str(value), case=False, na=False)
#         elif operation == 'equals':
#             return series.astype(str).str.lower() == str(value).lower()
            
#     except Exception as e:
#         st.error(f"Error applying filter on column {column}: {str(e)}")
#         return pd.Series(True, index=df.index)
    
#     return pd.Series(True, index=df.index)

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
            ]
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
    
    Pastikan semua kolom yang direferensikan ada dalam dataset.
    """

# def get_enhanced_system_message(data):
#     return f"""
#     You are an AI assistant expert in data analysis and visualization.
    
#     Available data structure:
#     {data.columns.tolist()}
    
#     Your task is to analyze the user's request and provide detailed visualization instructions.
    
#     When processing user requests, consider these aspects:
#     1. Complex filtering conditions including:
#         - Multiple conditions with AND/OR logic
#         - Nested conditions
#         - Date-based filtering
#         - Text matching (contains, starts_with, ends_with)
#         - Numeric comparisons
#         - NULL checks
#     2. Required columns for visualization
#     3. Appropriate chart type based on the data and request
#     4. Clear title and description
    
#     Response format should include complex filter structures like:
#     {{
#         "type": "visualization",
#         "chart_type": "bar|line|scatter|pie|map|histogram",
#         "x_column": "column_name",
#         "y_column": "column_name",
#         "title": "chart_title",
#         "description": "detailed_analysis",
#         "filter": {{
#             "operator": "and|or|not",
#             "conditions": [
#                 {{
#                     "column": "column_name",
#                     "operation": "top|bottom|>|>=|<|<=|==|!=|contains|starts_with|ends_with|between|in|not_in|is_null|is_not_null|date_between|date_after|date_before",
#                     "value": "single_value_or_list_or_range",
#                     "n": "number_for_top_bottom_filters"
#                 }},
#                 {{
#                     "operator": "or",
#                     "conditions": [
#                         {{
#                             "column": "another_column",
#                             "operation": "==",
#                             "value": "some_value"
#                         }},
#                         {{
#                             "column": "another_column",
#                             "operation": "contains",
#                             "value": "text_to_search"
#                         }}
#                     ]
#                 }}
#             ]
#         }}
#     }}
    
#     dan untuk tampilan visualisasinya untuk y_column jika itu menandakan nilai mulai dari 0 sesuai dengan ketentuan umum dari pembuatan grafik
#     If asked to create a map, use:
#     {{
#         "type": "visualization",
#         "chart_type": "map",
#         "latitude_column": "latitude_column_name",
#         "longitude_column": "longitude_column_name",
#         "title": "map_title",
#         "description": "long_description and detail resume"
#         "filter": {{
#             "type": "top|bottom|threshold|range|category",
#             "conditions": [
#                 {{
#                     "column": "column_name",
#                     "operation": ">=|<=|>|<|==|between|in",
#                     "value": single_value_or_list_or_range,
#                     "n": number_for_top_bottom_filters
#                 }}
#             ]
#         }}
#     }}
    
#     For pie chart, use:
#     {{
#         "type": "visualization",
#         "chart_type": "pie",
#         "value_column": "column_name",
#         "names_column": "column_name",
#         "title": "chart_title",
#         "description": "long_description and detail resume"
#         "filter": {{
#             "type": "top|bottom|threshold|range|category",
#             "conditions": [
#                 {{
#                     "column": "column_name",
#                     "operation": ">=|<=|>|<|==|between|in",
#                     "value": single_value_or_list_or_range,
#                     "n": number_for_top_bottom_filters
#                 }}
#             ]
#         }}
#     }}
    
#     For histograms, use:
#     {{
#         "type": "visualization",
#         "chart_type": "histogram",
#         "column": "column_name",
#         "bins": number_of_bins,
#         "title": "chart_title",
#         "description": "long_description and detail resume"
#         "filter": {{
#             "type": "top|bottom|threshold|range|category",
#             "conditions": [
#                 {{
#                     "column": "column_name",
#                     "operation": ">=|<=|>|<|==|between|in",
#                     "value": single_value_or_list_or_range,
#                     "n": number_for_top_bottom_filters
#                 }}
#             ]
#         }}
#     }}
    
#     For analysis questions that don't require visualization, provide an answer in JSON format:
#     {{
#         "type": "analysis",
#         "answer": "detailed_analysis_response"
#     }}
    
#     """

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

# def apply_filter_condition(df, condition):
#     column = condition.get('column')
#     operation = condition.get('operation')
#     value = condition.get('value')
#     n = condition.get('n')
    
#     if not column or column not in df.columns:
#         return df
    
#     try:
#         # Check if column should be treated as numeric
#         numeric_columns = st.session_state.get('numeric_columns', [])
        
#         if column in numeric_columns:
#             # Ensure column is numeric for operations that require it
#             if not pd.api.types.is_numeric_dtype(df[column]):
#                 df[column] = pd.to_numeric(df[column], errors='coerce')
        
#         # Handle top N filter
#         if operation == 'top' and n:
#             if isinstance(n, str):
#                 n = int(n)
#             sorted_df = df.sort_values(by=column, ascending=False)
#             return sorted_df.head(n)
        
#         # Handle bottom N filter
#         elif operation == 'bottom' and n:
#             if isinstance(n, str):
#                 n = int(n)
#             sorted_df = df.sort_values(by=column, ascending=True)
#             return sorted_df.head(n)
        
#         # Handle other numeric comparisons
#         elif operation in ['>', '>=', '<', '<=']:
#             if isinstance(value, str):
#                 value = float(value)
#             if operation == '>':
#                 return df[df[column] > value]
#             elif operation == '>=':
#                 return df[df[column] >= value]
#             elif operation == '<':
#                 return df[df[column] < value]
#             elif operation == '<=':
#                 return df[df[column] <= value]
        
#         # Handle equality
#         elif operation == '==':
#             return df[df[column] == value]
        
#         # Handle between range
#         elif operation == 'between' and isinstance(value, list) and len(value) == 2:
#             value = [float(v) if isinstance(v, str) else v for v in value]
#             return df[(df[column] >= value[0]) & (df[column] <= value[1])]
        
#         # Handle in list
#         elif operation == 'in' and isinstance(value, list):
#             return df[df[column].isin(value)]
            
#     except Exception as e:
#         st.error(f"Error applying filter on column {column}: {str(e)}")
#         st.error(f"Current column type: {df[column].dtype}")
#         st.error(f"Sample values: {df[column].head()}")
#         return df
    
#     return df

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

# Fungsi untuk membuat visualisasi
def create_visualization(df, viz_instructions):
    """
    Fungsi visualisasi yang ditingkatkan dengan validasi data yang lebih baik
    """
    try:
        # Terapkan filter jika ada
        if 'filter' in viz_instructions:
            df = create_enhanced_filter(df, viz_instructions['filter'])
            
        if df.empty:
            st.warning("Tidak ada data yang memenuhi kriteria filter")
            return
            
        chart_type = viz_instructions['chart_type']
        title = viz_instructions.get('title', 'Visualisasi')
        
        if chart_type == 'map':
            map_chart = create_map_visualization(df, viz_instructions)
            if map_chart:
                st.pydeck_chart(map_chart)
            
        elif chart_type in ['bar', 'line', 'scatter']:
            x_col = viz_instructions.get('x_column')
            y_col = viz_instructions.get('y_column')
            
            if not x_col or not y_col or x_col not in df.columns or y_col not in df.columns:
                st.error(f"Kolom yang diperlukan tidak ditemukan: {x_col} atau {y_col}")
                return
                
            # Pastikan data numerik valid untuk sumbu y
            df[y_col] = pd.to_numeric(df[y_col], errors='coerce')
            df = df.dropna(subset=[y_col])
            
            if chart_type == 'bar':
                fig = px.bar(df, x=x_col, y=y_col, title=title)
            elif chart_type == 'line':
                fig = px.line(df, x=x_col, y=y_col, title=title)
            else:  # scatter
                fig = px.scatter(df, x=x_col, y=y_col, title=title)
            
            fig.update_layout(
                title_x=0.5,
                margin=dict(t=100),
                xaxis_title=x_col,
                yaxis_title=y_col
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        elif chart_type == 'pie':
            values = viz_instructions.get('value_column')
            names = viz_instructions.get('names_column')
            
            if not values or not names or values not in df.columns or names not in df.columns:
                st.error("Kolom yang diperlukan untuk pie chart tidak ditemukan")
                return
                
            df[values] = pd.to_numeric(df[values], errors='coerce')
            df = df.dropna(subset=[values])
            
            fig = px.pie(df, values=values, names=names, title=title)
            st.plotly_chart(fig, use_container_width=True)
            
        # Tampilkan deskripsi dan data
        if 'description' in viz_instructions:
            st.markdown("### Analisis")
            st.write(viz_instructions['description'])
            
        st.markdown("### Data yang Divisualisasikan:")
        st.dataframe(df)
        
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

