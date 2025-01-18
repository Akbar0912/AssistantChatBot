import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
import pandas as pd

def detect_visualization_type(df: pd.DataFrame, question: str) -> str:
    """
    Mendeteksi tipe visualisasi yang sesuai berdasarkan data dan pertanyaan
    """
    question = question.lower()
    
    time_keywords = ['trend', 'waktu', 'periode', 'bulan', 'tahun', 'tanggal', 'tmt', 'tgl']
    comparison_keywords = ['bandingkan', 'perbandingan', 'compare', 'ratio', 'distribusi', 'jumlah', 'total']
    correlation_keywords = ['hubungan', 'korelasi', 'pengaruh', 'dampak']
    distribution_keywords = ['sebaran', 'distribusi', 'range', 'rentang']
    
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    categorical_cols = df.select_dtypes(include=['object']).columns
    
    # Deteksi berdasarkan keywords dan struktur data
    if any(keyword in question for keyword in time_keywords) and len(df) > 1:
        return 'line'
    elif any(keyword in question for keyword in correlation_keywords) and len(numeric_cols) >= 2:
        return 'scatter'
    elif any(keyword in question for keyword in comparison_keywords):
        if 'jenis_kelamin' in df.columns:
            return 'bar_stacked'
        elif len(df) <= 10:
            return 'pie'
        else:
            return 'bar'
    elif len(df) > 10 and len(numeric_cols) >= 1:
        return 'bar'
    else:
        return 'bar'

def create_visualization(df: pd.DataFrame, question: str) -> Dict[str, Any]:
    """
    Membuat visualisasi yang sesuai berdasarkan data dan pertanyaan
    """
    viz_type = detect_visualization_type(df, question)
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    categorical_cols = df.select_dtypes(include=['object']).columns
    
    try:
        if viz_type == 'line':
            fig = px.line(df, 
                         x=df.columns[0],
                         y=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1],
                         title='Analisis Trend',
                         color=categorical_cols[1] if len(categorical_cols) > 1 else None)
            
        elif viz_type == 'bar_stacked':
            # Khusus untuk visualisasi berdasarkan jenis kelamin
            fig = px.bar(df,
                        x=categorical_cols[0] if len(categorical_cols) > 0 else df.columns[0],
                        y=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1],
                        color='jenis_kelamin',
                        title='Analisis Perbandingan berdasarkan Jenis Kelamin',
                        barmode='stack')
            
        elif viz_type == 'bar':
            if len(categorical_cols) >= 2:
                fig = go.Figure()
                categories = df[categorical_cols[1]].unique()
                colors = px.colors.qualitative.Set3
                
                for idx, category in enumerate(categories):
                    category_data = df[df[categorical_cols[1]] == category]
                    fig.add_trace(go.Bar(
                        name=str(category),
                        x=category_data[categorical_cols[0]],
                        y=category_data[numeric_cols[0]] if len(numeric_cols) > 0 else category_data[df.columns[1]],
                        text=category_data[numeric_cols[0]] if len(numeric_cols) > 0 else category_data[df.columns[1]],
                        textposition='auto',
                        marker_color=colors[idx % len(colors)]
                    ))
                
                fig.update_layout(
                    barmode='group',
                    title='Analisis Perbandingan (Berkelompok)',
                    xaxis_title=categorical_cols[0],
                    yaxis_title=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1],
                )
            else:
                fig = px.bar(df,
                            x=categorical_cols[0] if len(categorical_cols) > 0 else df.columns[0],
                            y=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1],
                            title='Analisis Perbandingan',
                            color=categorical_cols[0] if len(categorical_cols) > 0 else None,
                            text=numeric_cols[0] if len(numeric_cols) > 0 else None)
            
        elif viz_type == 'pie':
            fig = px.pie(df,
                        names=categorical_cols[0] if len(categorical_cols) > 0 else df.columns[0],
                        values=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1],
                        title='Analisis Distribusi',
                        color=categorical_cols[0] if len(categorical_cols) > 0 else None)
            
        elif viz_type == 'scatter':
            fig = px.scatter(df,
                           x=numeric_cols[0],
                           y=numeric_cols[1] if len(numeric_cols) > 1 else df.columns[1],
                           title='Analisis Korelasi',
                           color=categorical_cols[0] if len(categorical_cols) > 0 else None)
            
        elif viz_type == 'box':
            fig = px.box(df,
                        y=numeric_cols[0] if len(numeric_cols) > 0 else df.columns[0],
                        x=categorical_cols[0] if len(categorical_cols) > 0 else None,
                        title='Distribusi Statistik',
                        color=categorical_cols[0] if len(categorical_cols) > 0 else None)
        
        # Enhanced layout dengan tema yang lebih profesional
        fig.update_layout(
            template='plotly_white',
            title_x=0.5,
            margin=dict(t=100, l=50, r=50, b=50),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1
            ),
            height=500,
            font=dict(family="Helvetica Neue, Arial", size=12),
            plot_bgcolor='black',
            paper_bgcolor='black'
        )
        
        # Tambahkan template hover yang informatif
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>" +
                         "%{y:,.2f}<br>" +
                         "<extra></extra>"
        )
        
        return {
            'figure': fig,
            'type': viz_type,
            'success': True,
            'message': f'Berhasil membuat visualisasi {viz_type}'
        }
        
    except Exception as e:
        return {
            'figure': None,
            'type': None,
            'success': False,
            'message': f'Error dalam membuat visualisasi: {str(e)}'
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
    elif viz_type == 'bar_stacked':
        desc += "Grafik batang bertumpuk menampilkan perbandingan berdasarkan jenis kelamin.\n"
    elif viz_type == 'bar':
        if len(df.select_dtypes(exclude=['int64', 'float64']).columns) >= 2:
            desc += "Grafik batang berkelompok menampilkan perbandingan nilai antar kategori.\n"
        else:
            desc += "Grafik batang menampilkan perbandingan nilai antar kategori.\n"
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