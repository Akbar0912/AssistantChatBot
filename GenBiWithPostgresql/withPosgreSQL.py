import psycopg2
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain.chains import LLMChain
import re

def setup_database_connection():
    conn = psycopg2.connect(
        dbname="Data_Dumy",
        user="postgres",
        password="password",
        host="localhost",
        port="5432"
    )
    print("koneksi berhasil")
    return conn

def get_table_schema(conn):
    """Get database schema information for all tables"""
    cursor = conn.cursor()
    schema_query = """
    SELECT 
        t.table_name,
        array_agg(
            c.column_name || ' ' || c.data_type || 
            CASE 
                WHEN c.data_type IN ('character varying', 'text', 'char', 'varchar') 
                THEN ' (case-insensitive)'
                ELSE ''
            END
        ) as columns
    FROM 
        information_schema.tables t
        JOIN information_schema.columns c ON t.table_name = c.table_name
    WHERE 
        t.table_schema = 'public'
        AND t.table_type = 'BASE TABLE'
    GROUP BY 
        t.table_name;
    """
    cursor.execute(schema_query)
    schemas = cursor.fetchall()
    cursor.close()
    
    schema_str = ""
    for table, columns in schemas:
        schema_str += f"\nTable: {table}\nColumns: {', '.join(columns)}\n"
    return schema_str

def create_sql_generation_prompt():
    """Create a detailed prompt template for SQL generation"""
    template = """You are a SQL expert. Given the database schema and a question in natural language,
your task is to generate a valid PostgreSQL query. For string comparisons, ALWAYS use case-insensitive 
comparisons with ILIKE or LOWER() function to ensure matching regardless of letter case.

Database Schema:
{schema}

Examples:
1. Question: "Show all employees with salary greater than 50000"
   SQL: SELECT * FROM employees WHERE salary > 50000;

2. Question: "Find the total sales by product category in 2023"
   SQL: SELECT category, SUM(amount) as total_sales 
   FROM sales 
   JOIN products ON sales.product_id = products.id 
   WHERE EXTRACT(YEAR FROM sale_date) = 2023 
   GROUP BY category;

3. Question: "Show all products with category Electronics"
   SQL: SELECT * FROM products WHERE LOWER(category) = LOWER('Electronics');

4. Question: "Find employees with position containing word manager"
   SQL: SELECT * FROM employees WHERE position ILIKE '%manager%';

Important Rules:
1. ALWAYS use ILIKE or LOWER() for text comparisons to make them case-insensitive
2. For exact matches, use: LOWER(column) = LOWER('value')
3. For partial matches, use: column ILIKE '%value%'
4. Remember that ILIKE is case-insensitive by default

Current Question: {question}

Generate only the SQL query without any additional text or markdown formatting.
The query should be a valid PostgreSQL query that answers the question.

SQL Query:"""

    return PromptTemplate(
        input_variables=["schema", "question"],
        template=template
    )

def setup_llm_chain(schema):
    # Initialize Ollama with specific parameters for better SQL generation
    llm = Ollama(
        model="llama3.2-vision",
        temperature=0.1,  # Lower temperature for more consistent output
        top_p=0.95,
        top_k=40,
        repeat_penalty=1.1
    )
    
    # Create prompt template
    prompt = create_sql_generation_prompt()
    
    # Create LLM chain
    chain = LLMChain(
        llm=llm,
        prompt=prompt,
        verbose=True  # Enable verbose mode for debugging
    )
    
    return chain

def clean_sql_query(query):
    """Clean and validate the SQL query"""
    # Remove any markdown code blocks
    query = re.sub(r'```sql\n?(.*?)\n?```', r'\1', query, flags=re.DOTALL)
    
    # Remove any natural language prefixes/suffixes
    query = re.sub(r'^.*?(SELECT|INSERT|UPDATE|DELETE)', r'\1', query, flags=re.DOTALL | re.IGNORECASE)
    query = re.sub(r';.*$', ';', query, flags=re.DOTALL)
    
    # Clean up whitespace
    query = ' '.join(query.split())
    
    # Validate basic SQL structure
    if not re.match(r'^(SELECT|INSERT|UPDATE|DELETE)', query, re.IGNORECASE):
        raise ValueError("Generated query doesn't start with a valid SQL command")
    
    # Add semicolon if missing
    if not query.strip().endswith(';'):
        query += ';'
    
    return query

def text_to_sql(text, chain, conn, schema):
    try:
        # Generate SQL query using the chain
        response = chain.invoke({
            "schema": schema,
            "question": text
        })
        
        # Extract and clean the SQL query
        sql_query = clean_sql_query(response['text'])
        
        print(f"\nGenerated SQL Query: {sql_query}\n")  # Debug output
        
        # Execute the query
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        cursor.close()
        
        return results
    except Exception as e:
        print(f"\nError Details: {str(e)}\nGenerated Query: {response['text'] if 'response' in locals() else 'No query generated'}\n")
        return f"Error: {str(e)}"

def main():
    try:
        # Setup database connection
        conn = setup_database_connection()
        
        # Get database schema
        schema = get_table_schema(conn)
        
        # Setup LLM chain
        chain = setup_llm_chain(schema)
        print("Isi Chain :", chain)

        while True:
            # Get user input
            prompt = input("\nEnter your question (or 'exit' to quit): ")
            
            if prompt.lower() == 'exit':
                break
            
            # Convert text to SQL and execute
            results = text_to_sql(prompt, chain, conn, schema)
            print("Query Results:", results)

    except Exception as e:
        print(f"Setup error: {str(e)}")
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()