from langchain.prompts import PromptTemplate

def get_sql_prompt() -> PromptTemplate:
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
1. ALWAYS use ILIKE or LOWER() for text comparisons
2. For exact matches, use: LOWER(column) = LOWER('value')
3. For partial matches, use: column ILIKE '%value%'

Current Question: {question}

Generate only the SQL query without any additional text or markdown formatting.
The query should be a valid PostgreSQL query that answers the question.

SQL Query:"""

    return PromptTemplate(
        input_variables=["schema", "question"],
        template=template
    )