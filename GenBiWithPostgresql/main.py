import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from typing import Optional, Tuple, Dict, Any
import traceback

from database.connection import DatabaseConnection
from database.schema import SchemaManager
from llm.chain_manager import ChainManager
from visualization.chart_manager import ChartManager

class SQLVisualizerApp:
    def __init__(self):
        self.db_conn = DatabaseConnection()
        
        if 'query_history' not in st.session_state:
            st.session_state.query_history = []
        if 'error_count' not in st.session_state:
            st.session_state.error_count = 0

    def initialize(self) -> bool:
        try:
            conn = self.db_conn.connect()
            if not conn:
                st.error("Could not connect to database")
                return False
            
            self.schema_manager = SchemaManager(conn)
            self.chain_manager = ChainManager(self.schema_manager)
            self.chain = self.chain_manager.create_chain()
            
            return True
            
        except Exception as e:
            st.error(f"Initialization error: {str(e)}")
            return False

    def process_query(self, question: str) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[str]]:
        """Process user query with enhanced metadata awareness"""
        try:
            # Generate SQL and visualization config using enhanced chain manager
            result = self.chain_manager.process_query(question)
            if not result:
                return None, None, None
            
            # Process SQL query
            sql_query = result['query']
            
            # Execute query
            df = pd.read_sql_query(sql_query, self.db_conn.conn)
            
            # Save to query history with metadata
            self._save_to_history(
                question=question,
                query=sql_query,
                result_count=len(df),
                viz_config=result['visualization'],
                tables_used=result.get('metadata', {}).get('tables_used', [])
            )
            
            # Handle empty results
            if df.empty:
                st.warning("Query returned no results.")
                return None, None, sql_query
            
            # Create visualization with enhanced metadata
            chart_html = ChartManager.create_chart(
                df, 
                result['visualization'],
                # self.schema_manager.get_column_info  # Pass callback for metadata lookup
            )
            
            # Reset error count on successful query
            st.session_state.error_count = 0
            
            return df, chart_html, sql_query
            
        except Exception as e:
            st.session_state.error_count += 1
            self._handle_error(e)
            return None, None, None

    def _save_to_history(self, question: str, query: str, result_count: int, 
                        viz_config: Dict[str, Any]):
        """Save query to history with enhanced metadata"""
        history_entry = {
            # 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'question': question,
            'query': query,
            'result_count': result_count,
            'visualization': viz_config,
        }
        st.session_state.query_history.append(history_entry)

    def _handle_error(self, error: Exception):
        """Handle and display errors appropriately"""
        error_msg = str(error)
        st.error(error_msg)
        
        if st.session_state.error_count >= 3:
            st.error("""
            Having trouble with complex queries? Try:
            1. Breaking down your question into simpler parts
            2. Being more specific about what you want to see
            3. Checking if the columns you're referring to exist in the database
            """)
            
        # Show debug info in expanded section
        with st.expander("Debug Information"):
            st.code(traceback.format_exc())

    def _show_query_history(self):
        """Display enhanced query history with metadata insights"""
        with st.expander("Query History"):
            for entry in reversed(st.session_state.query_history[-10:]):
                with st.container():
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"""
                        **Time:** {entry['timestamp']}  
                        **Question:** {entry['question']}  
                        **Results:** {entry['result_count']} rows  
                        **Tables Used:** {', '.join(entry['tables_used'])}
                        """)
                    with col2:
                        if st.button("Rerun", key=f"rerun_{entry['timestamp']}"):
                            st.session_state.rerun_query = entry['question']
                            st.rerun()
                    
                    with st.expander("Show Query"):
                        st.code(entry['query'], language="sql")
                    
                    st.markdown("---")
    
    def _show_metadata_insights(self, df: pd.DataFrame):
        """Display metadata-based insights about the query results"""
        st.subheader("Data Insights")
        
        # Show basic metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            st.metric("Fields", len(df.columns))
        with col3:
            non_null_counts = df.count()
            completeness = (non_null_counts.sum() / (len(df) * len(df.columns))) * 100
            st.metric("Data Completeness", f"{completeness:.1f}%")
        
        # Show column summary
        with st.expander("Column Details"):
            for col in df.columns:
                st.write(f"**{col}**")
                col_stats = {
                    "Type": str(df[col].dtype),
                    "Non-null Count": df[col].count(),
                    "Null Count": df[col].isna().sum(),
                }
                if df[col].dtype in ['int64', 'float64']:
                    col_stats.update({
                        "Mean": df[col].mean(),
                        "Min": df[col].min(),
                        "Max": df[col].max()
                    })
                elif df[col].dtype == 'object':
                    col_stats.update({
                        "Unique Values": df[col].nunique(),
                        "Most Common": df[col].mode().iloc[0] if not df[col].empty else None
                    })
                
                st.json(col_stats)

    def run(self):
        """Run the application"""
        st.title("SQL Query Visualizer")
        
        if not self.initialize():
            return
        
        try:
            
            # Create main query input
            col1, col2 = st.columns([3, 1])
            with col1:
                question = st.text_input(
                    "Enter your question:",
                    placeholder="e.g., Show monthly sales trends for 2023"
                )
            with col2:
                if st.button("Clear History"):
                    st.session_state.query_history = []
                    st.rerun()
            
            if hasattr(st.session_state, 'rerun_query'):
                question = st.session_state.rerun_query
                delattr(st.session_state, 'rerun_query')
            
            # Process query if provided
            if question:
                with st.spinner("Processing your query..."):
                    df, chart_html, sql_query = self.process_query(question)
                    
                    if sql_query:
                        st.subheader("Generated SQL Query")
                        st.code(sql_query, language="sql")
                    
                    if df is not None:
                        # Show data summary
                        st.subheader("Data Summary")
                        # col1, col2, col3 = st.columns(3)
                        # with col1:
                        #     st.metric("Rows", len(df))
                        # with col2:
                        #     st.metric("Columns", len(df.columns))
                        # with col3:
                        #     numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
                        #     st.metric("Numeric Columns", len(numeric_cols))
                        self._show_metadata_insights(df)
                        
                        # Show results
                        st.subheader("Query Results")
                        st.dataframe(df)
                        
                        # Show visualization if available
                        if chart_html:
                            st.subheader("Visualization")
                            components.html(chart_html, height=500)
            
            # Show query history
            self._show_query_history()
            
        except Exception as e:
            st.error(f"Application error: {str(e)}")
            st.error(f"Debug info: {traceback.format_exc()}")
        
        finally:
            if hasattr(self, 'db_conn'):
                self.db_conn.close()

def main():
    """Application entry point"""
    app = SQLVisualizerApp()
    app.run()

if __name__ == "__main__":
    main()