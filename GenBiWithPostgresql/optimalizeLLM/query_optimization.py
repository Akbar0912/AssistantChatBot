# query_optimization.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
import re

@dataclass
class DatabaseSchema:
    """Enhanced database schema representation"""
    table_name: str
    columns: Dict[str, str]
    description: str
    example_queries: List[str]
    relationships: Dict[str, str]

@dataclass
class QueryContext:
    """Context tracking for query generation"""
    intent: str
    required_columns: List[str]
    filters: Dict[str, any]
    aggregations: List[str]

class QueryPatternLibrary:
    """Library of common query patterns and optimizations"""
    
    @staticmethod
    def get_aggregation_pattern(columns: List[str], grouping: List[str]) -> str:
        return f"""
        SELECT 
            {', '.join(grouping)},
            {', '.join(columns)}
        FROM {{table}}
        GROUP BY {', '.join(grouping)}
        """
    
    @staticmethod
    def get_filtering_pattern(conditions: List[str]) -> str:
        return f"""
        SELECT {{columns}}
        FROM {{table}}
        WHERE {' AND '.join(conditions)}
        """
    
    @staticmethod
    def get_join_pattern(main_table: str, join_table: str, join_condition: str) -> str:
        return f"""
        SELECT {{columns}}
        FROM {main_table}
        JOIN {join_table} ON {join_condition}
        """

class EnhancedQueryGenerator:
    def __init__(self):
        self.schema_registry: Dict[str, DatabaseSchema] = {}
        self.query_patterns = QueryPatternLibrary()
        self.llm = ChatOllama(model="llama3.2", temperature=0.1)
        
    def register_schema(self, schema: DatabaseSchema) -> None:
        """Register database schema with enhanced metadata"""
        self.schema_registry[schema.table_name] = schema
        
    def create_enhanced_system_prompt(self) -> str:
        """Generate comprehensive system prompt with schema context"""
        prompt_template = """You are an expert SQL analyst working with a PostgreSQL database.

        SCHEMA CONTEXT:
        {schema_details}

        QUERY GENERATION RULES:
        1. Always start queries with SELECT
        2. Never use backticks (`)
        3. Use proper column names from schema
        4. Prefer explicit column selection over SELECT *
        5. Include appropriate JOINs based on relationships
        6. Add meaningful aliases for readability
        7. Use proper aggregation functions when needed
        8. Include ORDER BY for better readability
        9. Use appropriate GROUP BY with aggregations
        10. Optimize for performance with proper indexing hints

        STANDARDIZED PATTERNS:
        - Aggregations: Use COUNT, SUM, AVG with GROUP BY
        - Filtering: Apply WHERE clauses efficiently
        - Sorting: Include ORDER BY for meaningful presentation
        - Joins: Use appropriate JOIN types based on relationships
        - Subqueries: Optimize with proper correlation

        EXAMPLE QUERIES:
        {example_queries}
        """
        
        schema_details = "\n".join(
            f"Table: {schema.table_name}\n"
            f"Description: {schema.description}\n"
            f"Columns: {', '.join(f'{k}: {v}' for k, v in schema.columns.items())}\n"
            f"Relationships: {schema.relationships}\n"
            for schema in self.schema_registry.values()
        )
        
        example_queries = "\n".join(
            query for schema in self.schema_registry.values()
            for query in schema.example_queries
        )
        
        return prompt_template.format(
            schema_details=schema_details,
            example_queries=example_queries
        )

    def analyze_query_intent(self, question: str) -> QueryContext:
        """Analyze user question to determine query intent and requirements"""
        intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """Analyze the following question and extract:
            1. Main intent (aggregation, filtering, joining, etc.)
            2. Required columns
            3. Filter conditions
            4. Required aggregations
            
            Format the response as:
            Intent: <intent>
            Columns: <column1>, <column2>
            Filters: <filter1>, <filter2>
            Aggregations: <agg1>, <agg2>"""),
            ("user", "{question}")
        ])
        
        chain = intent_prompt | self.llm | StrOutputParser()
        result = chain.invoke({"question": question})
        
        # Parse the response into QueryContext
        lines = result.split('\n')
        context_dict = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                context_dict[key.strip()] = [x.strip() for x in value.strip().split(',')]
        
        return QueryContext(
            intent=context_dict.get('Intent', [''])[0],
            required_columns=context_dict.get('Columns', []),
            filters={f: None for f in context_dict.get('Filters', [])},
            aggregations=context_dict.get('Aggregations', [])
        )

    def generate_optimized_query(self, question: str) -> str:
        """Generate optimized SQL query based on analyzed intent"""
        context = self.analyze_query_intent(question)
        
        query_template = ChatPromptTemplate.from_messages([
            ("system", self.create_enhanced_system_prompt()),
            ("user", """
            Question: {question}
            
            Required Information:
            - Intent: {intent}
            - Required Columns: {required_columns}
            - Filters: {filters}
            - Aggregations: {aggregations}
            
            Generate an optimized SQL query that:
            1. Precisely matches the user's intent
            2. Uses only necessary columns
            3. Applies appropriate optimizations
            4. Follows all schema rules and patterns
            """)
        ])
        
        chain = query_template | self.llm | StrOutputParser()
        
        return chain.invoke({
            "question": question,
            "intent": context.intent,
            "required_columns": ", ".join(context.required_columns),
            "filters": ", ".join(f"{k}={v}" for k, v in context.filters.items()),
            "aggregations": ", ".join(context.aggregations)
        })

    def validate_query(self, query: str) -> bool:
        """Validate generated SQL query"""
        patterns = [
            (r'^SELECT', "Query must start with SELECT"),
            (r'`', "Query contains invalid backticks"),
            (r'\*(?!\s*FROM)', "Avoid using SELECT * except in specific cases"),
            (r'GROUP BY.*HAVING|HAVING.*GROUP BY', "Check HAVING clause usage"),
        ]
        
        for pattern, message in patterns:
            if bool(re.search(pattern, query, re.IGNORECASE)) != (pattern == r'^SELECT'):
                print(f"Validation failed: {message}")
                return False
        return True