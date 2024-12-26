import re

class SQLCleaner:
    @staticmethod
    def clean_query(query: str) -> str:
        """Clean and validate the SQL query"""
        # Remove markdown code blocks
        query = re.sub(r'```sql\n?(.*?)\n?```', r'\1', query, flags=re.DOTALL)
        
        # Remove natural language prefixes/suffixes
        query = re.sub(r'^.*?(SELECT|INSERT|UPDATE|DELETE)', r'\1', query, flags=re.DOTALL | re.IGNORECASE)
        query = re.sub(r';.*$', ';', query, flags=re.DOTALL)
        
        # Clean whitespace
        query = ' '.join(query.split())
        
        # Validate basic SQL structure
        if not re.match(r'^(SELECT|INSERT|UPDATE|DELETE)', query, re.IGNORECASE):
            raise ValueError("Generated query doesn't start with a valid SQL command")
        
        # Add semicolon if missing
        if not query.strip().endswith(';'):
            query += ';'
        
        return query