# visualization/chart_manager.py
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any

class ChartManager:
    @staticmethod
    def create_chart(df: pd.DataFrame, config: Dict[str, Any]) -> str:
        try:
            chart_type = config.get('type', 'table').lower()
            
            if chart_type == 'table':
                fig = go.Figure(data=[go.Table(
                    header=dict(values=list(df.columns),
                              fill_color='paleturquoise',
                              align='left'),
                    cells=dict(values=[df[col] for col in df.columns],
                             fill_color='lavender',
                             align='left'))
                ])
            elif chart_type == 'bar':
                fig = px.bar(df,
                           x=config.get('xAxis'),
                           y=config.get('yAxis'),
                           title=config.get('title'))
            elif chart_type == 'line':
                fig = px.line(df,
                            x=config.get('xAxis'),
                            y=config.get('yAxis'),
                            title=config.get('title'))
            elif chart_type == 'pie':
                fig = px.pie(df,
                           values=config.get('yAxis'),
                           names=config.get('xAxis'),
                           title=config.get('title'))
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")

            return fig.to_html(full_html=False)
            
        except Exception as e:
            print(f"Error creating chart: {str(e)}")
            return ""