import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
import pandas as pd

def detect_visualization_type(df: pd.DataFrame, question: str) -> str:
    """
    Mendeteksi tipe visualisasi yang sesuai berdasarkan data dan pertanyaan
    """
    question = question.lower()
    
    time_keywords = ['trend', 'waktu', 'periode', 'bulan', 'tahun', 'tanggal']
    comparison_keywords = ['bandingkan', 'perbandingan', 'compare', 'ratio', 'distribusi']
    aggregation_keywords = ['total', 'jumlah', 'rata-rata', 'average', 'sum', 'count']
    
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    
    if any(keyword in question for keyword in time_keywords):
        return 'line'
    elif any(keyword in question for keyword in comparison_keywords):
        if len(df) <= 10:
            return 'bar'
        else:
            return 'pie'
    elif any(keyword in question for keyword in aggregation_keywords):
        if len(numeric_cols) >= 2:
            return 'scatter'
        else:
            return 'bar'
    elif len(df) > 10 and len(numeric_cols) >= 1:
        return 'box'
    else:
        return 'bar'

def create_visualization(df: pd.DataFrame, question: str) -> Dict[str, Any]:
    """
    Membuat visualisasi yang sesuai berdasarkan data dan pertanyaan
    """
    viz_type = detect_visualization_type(df, question)
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    non_numeric_cols = df.select_dtypes(exclude=['int64', 'float64']).columns
    
    try:
        if viz_type == 'line':
            fig = px.line(df, 
                         x=df.columns[0],
                         y=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1],
                         title='Trend Analysis')
            
        elif viz_type == 'bar':
            fig = px.bar(df,
                        x=non_numeric_cols[0] if len(non_numeric_cols) > 0 else df.columns[0],
                        y=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1],
                        title='Comparative Analysis')
            
        elif viz_type == 'pie':
            fig = px.pie(df,
                        names=non_numeric_cols[0] if len(non_numeric_cols) > 0 else df.columns[0],
                        values=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1],
                        title='Distribution Analysis')
            
        elif viz_type == 'scatter':
            fig = px.scatter(df,
                           x=numeric_cols[0],
                           y=numeric_cols[1] if len(numeric_cols) > 1 else df.columns[1],
                           title='Correlation Analysis')
            
        elif viz_type == 'box':
            fig = px.box(df,
                        y=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[0],
                        title='Statistical Distribution')
        
        fig.update_layout(
            template='plotly_white',
            title_x=0.5,
            margin=dict(t=100, l=50, r=50, b=50),
            showlegend=True,
            height=500
        )
        
        return {
            'figure': fig,
            'type': viz_type,
            'success': True,
            'message': f'Successfully created {viz_type} visualization'
        }
        
    except Exception as e:
        return {
            'figure': None,
            'type': None,
            'success': False,
            'message': f'Error creating visualization: {str(e)}'
        }

def generate_viz_description(viz_result: Dict[str, Any], df: pd.DataFrame) -> str:
    """
    Menghasilkan deskripsi untuk visualisasi
    """
    if not viz_result['success']:
        return viz_result['message']
        
    viz_type = viz_result['type']
    desc = f"Visualisasi data ditampilkan dalam bentuk grafik {viz_type}.\n\n"
    
    if viz_type == 'line':
        desc += "Grafik menunjukkan trend/pola perubahan data sepanjang waktu.\n"
    elif viz_type == 'bar':
        desc += "Grafik menampilkan perbandingan nilai antar kategori.\n"
    elif viz_type == 'pie':
        desc += "Grafik menunjukkan distribusi/komposisi data dalam bentuk presentase.\n"
    elif viz_type == 'scatter':
        desc += "Grafik menampilkan hubungan/korelasi antar variabel.\n"
    elif viz_type == 'box':
        desc += "Grafik menunjukkan distribusi statistik data termasuk median, kuartil, dan outliers.\n"
        
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    if len(numeric_cols) > 0:
        desc += "\nStatistik dasar:\n"
        for col in numeric_cols:
            desc += f"- {col}:\n"
            desc += f"  Rata-rata: {df[col].mean():.2f}\n"
            desc += f"  Minimum: {df[col].min():.2f}\n"
            desc += f"  Maximum: {df[col].max():.2f}\n"
    
    return desc