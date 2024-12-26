import streamlit as st
from database.connection import DatabaseConnection
from database.schema import SchemaManager
from llm.chain import LLMChainManager
from utils.sql_cleaner import SQLCleaner

def initialize_connection():
    """Initialize database connection with credentials"""
    return DatabaseConnection(
        dbname="Data_Dumy",
        user="postgres",
        password="password",
        host="localhost",
        port="5432"
    )

def process_query(prompt: str, db_conn: DatabaseConnection, llm_chain, schema: str):
    """Process natural language query and return results"""
    try:
        # Generate SQL query
        response = llm_chain.invoke({
            "schema": schema,
            "question": prompt
        })
        
        # Clean the generated SQL
        sql_query = SQLCleaner.clean_query(response['text'])
        
        # Execute query and get results
        results = db_conn.execute_query(sql_query)
        
        return sql_query, results
    except Exception as e:
        return None, f"Error: {str(e)}"

def main():
    st.title("SQL Query Generator")
    st.write("Convert your natural language questions into SQL queries")
    
    # Initialize database connection
    try:
        db_conn = initialize_connection()
        conn = db_conn.connect()
        
        # Get schema
        schema = SchemaManager.get_schema(conn)
        
        # Setup LLM chain
        llm_chain = LLMChainManager.setup_chain(schema)
        
        # Create text input for user question
        user_question = st.text_area("Enter your question:", height=100)
        
        if st.button("Generate Query"):
            if user_question:
                with st.spinner("Generating SQL query..."):
                    sql_query, results = process_query(user_question, db_conn, llm_chain, schema)
                    
                    if sql_query:
                        st.subheader("Generated SQL Query:")
                        st.code(sql_query, language="sql")
                        
                        st.subheader("Query Results:")
                        st.write(results)
            else:
                st.warning("Please enter a question.")
        
        # Optional: Show schema
        if st.checkbox("Show Database Schema"):
            st.code(schema)
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        
    finally:
        if 'db_conn' in locals():
            db_conn.close()

if __name__ == "__main__":
    main()