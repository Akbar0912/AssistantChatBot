class SchemaManager:
    @staticmethod
    def get_schema(conn) -> str:
        """Get database schema information for all tables"""
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
        
        with conn.cursor() as cursor:
            cursor.execute(schema_query)
            schemas = cursor.fetchall()
        
        return SchemaManager._format_schema(schemas)
    
    @staticmethod
    def _format_schema(schemas: list) -> str:
        """Format schema information into a readable string"""
        return "\n".join(
            f"Table: {table}\nColumns: {', '.join(columns)}\n"
            for table, columns in schemas
        )