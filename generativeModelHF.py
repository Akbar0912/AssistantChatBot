import streamlit as st
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import json
import pydeck as pdk
import plotly.express as px
import requests
from dotenv import load_dotenv

hf_token = load_dotenv()

# Hugging Face Model Configuration
MODEL_NAME = "facebook/opt-125m"  # You can swap with other models

class HuggingFaceAssistant:
    def __init__(self, model_name):
        """
        Initialize Hugging Face model for text generation and analysis
        """
        try:
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                token="secret"
            )
            
            # Use pipeline for easier text generation
            self.generator = pipeline(
                'text-generation', 
                model=model_name, 
                torch_dtype=torch.float16,
                device_map='auto'  # Automatic device placement
            )
        except Exception as e:
            st.error(f"Model loading error: {e}")
            raise

    def generate_system_prompt(self, data_columns):
        """
        Create a robust system prompt for data analysis
        """
        return f"""
        You are an expert AI data analyst. You will help users analyze and visualize data.

        Available Data Columns: {', '.join(data_columns)}

        Guidelines:
        1. Analyze user queries precisely
        2. Provide clear, actionable insights
        3. Recommend appropriate visualization techniques
        4. Generate JSON response with visualization instructions
        5. Be concise and informative
        """

    def generate_visualization_instructions(self, df, query):
        """
        Generate visualization instructions using the language model
        """
        system_prompt = self.generate_system_prompt(df.columns)
        
        full_prompt = f"""
        {system_prompt}

        User Query: {query}

        Respond with a STRICT JSON format containing visualization instructions. 
        Use these example formats as reference:

        For Bar Chart:
        {{
            "type": "visualization",
            "chart_type": "bar",
            "title": "Chart Title",
            "x_column": "column_name",
            "y_column": "numeric_column"
        }}

        For Line Chart:
        {{
            "type": "visualization", 
            "chart_type": "line",
            "title": "Trend Analysis",
            "x_column": "time_column",
            "y_column": "numeric_column"
        }}

        Analyze the context of the query and select the most appropriate visualization.
        """

        try:
            # Generate response
            response = self.generator(
                full_prompt, 
                max_new_tokens=500, 
                num_return_sequences=1,
                temperature=0.7
            )[0]['generated_text']

            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            
        except Exception as e:
            st.error(f"Visualization instruction generation error: {e}")
        
        return None

    def analyze_query(self, df, query):
        """
        Analyze user query and provide insights
        """
        system_prompt = self.generate_system_prompt(df.columns)
        
        full_prompt = f"""
        {system_prompt}

        User Query: {query}

        Provide a comprehensive, data-driven analysis addressing the specific question.
        Be precise, use numerical evidence, and offer clear insights.
        """

        try:
            response = self.generator(
                full_prompt, 
                max_new_tokens=500, 
                num_return_sequences=1,
                temperature=0.7
            )[0]['generated_text']

            return response
        except Exception as e:
            st.error(f"Query analysis error: {e}")
            return "Unable to process the query."

def fetch_data_from_api():
    # Your existing data fetching logic
    API_URL = "http://127.0.0.1:8000/api/kinerja"
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

def transform_data(df, transform_config):
    """
    Fungsi untuk melakukan transformasi data sesuai kebutuhan visualisasi
    """
    if not transform_config or 'type' not in transform_config:
        return df
        
    df_transformed = df.copy()
    transform_type = transform_config['type']
    
    try:
        if transform_type == 'group':
            by_columns = transform_config.get('by', [])
            agg_function = transform_config.get('agg_function', 'count')
            
            if agg_function == 'count':
                df_transformed = df_transformed.groupby(by_columns).size().reset_index(name='count')
            else:
                agg_column = transform_config.get('column')
                if agg_column:
                    df_transformed = df_transformed.groupby(by_columns).agg({agg_column: agg_function}).reset_index()
                    
        elif transform_type == 'pivot':
            index = transform_config.get('index')
            columns = transform_config.get('columns')
            values = transform_config.get('values')
            agg_function = transform_config.get('agg_function', 'sum')
            
            if all([index, columns, values]):
                df_transformed = df_transformed.pivot_table(
                    index=index,
                    columns=columns,
                    values=values,
                    aggfunc=agg_function
                ).reset_index()
                
        elif transform_type == 'melt':
            id_vars = transform_config.get('id_vars', [])
            value_vars = transform_config.get('value_vars', [])
            
            if id_vars and value_vars:
                df_transformed = pd.melt(
                    df_transformed,
                    id_vars=id_vars,
                    value_vars=value_vars
                )
                
        return df_transformed
        
    except Exception as e:
        st.error(f"Error dalam transformasi data: {str(e)}")
        return df

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
                    # Untuk operasi numerik, konversi kolom ke numerik
                    if operation in ['>', '>=', '<', '<=']:
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
                    
                    # Untuk operasi string equality (==), gunakan string comparison
                    elif operation == '==':
                        if isinstance(value, str):
                            # Konversi kolom ke string dan gunakan string comparison case-insensitive
                            df_filtered = df_filtered[df_filtered[column].astype(str).str.lower() == value.lower()]
                        else:
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
                    # Konversi kolom pengurutan ke numerik hanya jika diperlukan
                    if df_filtered[sort_column].dtype not in ['int64', 'float64']:
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

def create_visualization(df, viz_instructions):
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
            return
        
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
                return
                
            fig = px.histogram(df_viz, x=value_column, nbins=bins, title=title)
            st.plotly_chart(fig, use_container_width=True)
            
        elif chart_type in ['bar', 'line', 'scatter']:
            x_col = viz_instructions.get('x_column')
            y_col = viz_instructions.get('y_column')
            
            if not x_col or not y_col or x_col not in df_viz.columns or y_col not in df_viz.columns:
                st.error("Kolom yang diperlukan tidak ditemukan")
                return
                
            # Konversi dan bersihkan data numerik
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

def main():
    st.set_page_config(layout="wide")
    st.title("Open-Source AI Data Analysis")

    # Initialize Hugging Face Assistant
    try:
        assistant = HuggingFaceAssistant(MODEL_NAME)
    except Exception as e:
        st.error(f"Model initialization failed: {e}")
        return

    # Fetch data
    data = fetch_data_from_api()

    if data is not None:
        st.write("Data Preview:")
        st.dataframe(data)

        # Visualization Section
        st.header("AI-Powered Visualization")
        viz_query = st.text_input("Describe the visualization you want:")
        
        if st.button("Generate Visualization"):
            if viz_query:
                try:
                    viz_instructions = assistant.generate_visualization_instructions(data, viz_query)
                    if viz_instructions:
                        st.write("Generated Visualization Instructions:")
                        st.json(viz_instructions)
                        create_visualization(data, viz_instructions)
                    else:
                        st.warning("Could not generate visualization instructions.")
                except Exception as e:
                    st.error(f"Visualization generation error: {e}")

        # Query Analysis Section
        st.header("Data Query Analysis")
        user_query = st.text_input("Ask a question about the data:")
        
        if user_query:
            try:
                analysis_result = assistant.analyze_query(data, user_query)
                st.write("AI Analysis:")
                st.write(analysis_result)
            except Exception as e:
                st.error(f"Query analysis error: {e}")

if __name__ == "__main__":
    main()
