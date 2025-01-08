# app.py

import os
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
import pandas as pd
from database_manager import DatabaseManager
from langchain_community.chat_models import ChatOllama
from visualization import create_visualization, generate_viz_description
from dotenv import load_dotenv

def init_session_state():
    """Initialize session state variables"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            AIMessage(content="Hello! I'm your Data Assistant. Ask me questions about personnel data.")
        ]
    
    if "db_manager" not in st.session_state:
        load_dotenv()
        connection_params = {
            "user": os.environ['DB_USER'],
            "password": os.environ['DB_PASSWORD'],
            "host": "localhost",
            "port": 5432,
            "database": os.environ['DB_NAME']
        }
        st.session_state.db_manager = DatabaseManager(connection_params)

def get_response(question: str) -> tuple:
    """Generate response for user question"""
    try:
        # Generate and execute query
        query, df_results = st.session_state.db_manager.process_question(question)
        
        if df_results is None:
            return "Sorry, I couldn't process that question properly.", None, None
        
        # Generate visualization
        viz_result = create_visualization(df_results, question)
        viz_description = generate_viz_description(viz_result, df_results)
        
        # Generate analysis
        llm = ChatOllama(model="llama3.2", temperature=0.1)
        analysis_prompt = f"""Analyze the following data and provide insights:
        Data: {df_results.to_string()}
        Visualization: {viz_description}
        
        Focus on:
        1. Key patterns and trends
        2. Notable statistics
        3. Important relationships
        4. Potential implications
        
        Keep the analysis concise but informative."""
        
        analysis = llm.predict(analysis_prompt)
        
        # Format response
        response = f"""Based on your question, here's what I found:

Query Used:
```sql
{query}
```

Analysis:
{analysis}

{viz_description if viz_description else ''}

Would you like to explore any specific aspect of these results in more detail?"""
        
        return response, df_results, viz_result
        
    except Exception as e:
        return f"An error occurred: {str(e)}", None, None

def main():
    st.set_page_config(page_title="Personnel Data Assistant", page_icon="👤")
    st.title("Personnel Data Assistant")
    
    init_session_state()
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message("AI" if isinstance(message, AIMessage) else "User"):
            st.markdown(message.content)
    
    # Get user input
    user_query = st.chat_input("Ask a question about personnel data...")
    
    if user_query:
        # Add user message to history
        st.session_state.chat_history.append(HumanMessage(content=user_query))
        with st.chat_message("User"):
            st.markdown(user_query)
        
        # Generate and display response
        with st.chat_message("AI"):
            response, df_results, viz_result = get_response(user_query)
            st.markdown(response)
            
            if df_results is not None and not df_results.empty:
                st.write("Query Results:")
                st.dataframe(df_results)
                
                if viz_result and viz_result.get('success'):
                    st.write("Data Visualization:")
                    st.plotly_chart(viz_result['figure'], use_container_width=True)
        
        # Add AI response to history
        st.session_state.chat_history.append(AIMessage(content=response))

if __name__ == "__main__":
    main()