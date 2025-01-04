import re
from typing import Optional

class QueryProcessor:
    """Handles SQL query processing and validation"""
    
    @staticmethod
    def clean_query(query: str) -> Optional[str]:
        """Clean and validate SQL query"""
        try:
            # Remove markdown code blocks
            query = re.sub(r'```sql\n?(.*?)\n?```', r'\1', query, flags=re.DOTALL)
            
            # Validate query type
            QueryProcessor._validate_query_type(query)
            
            # Clean whitespace
            query = ' '.join(query.split())
            
            # Add LIMIT if needed
            query = QueryProcessor._add_limit(query)
            
            # Ensure semicolon
            if not query.strip().endswith(';'):
                query += ';'
            
            return query
        except Exception as e:
            raise ValueError(f"Query cleaning error: {str(e)}")

    @staticmethod
    def _validate_query_type(query: str):
        """Validate query type and prevent dangerous operations"""
        dangerous_keywords = ['DROP', 'TRUNCATE', 'DELETE', 'UPDATE', 'INSERT']
        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', query.upper()):
                raise ValueError(f"Unauthorized {keyword} command in query")
        
        if not re.match(r'^\s*SELECT', query, re.IGNORECASE):
            raise ValueError("Only SELECT queries are allowed")

    @staticmethod
    def _add_limit(query: str) -> str:
        """Add LIMIT clause if not present"""
        if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
            query = f"{query.rstrip(';')} LIMIT 1000;"
        return query