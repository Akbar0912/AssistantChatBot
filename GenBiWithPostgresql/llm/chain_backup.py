from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.vectorstores.pgvector import PGVector
from langchain.embeddings import OllamaEmbeddings
import pandas as pd
import re
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import execute_values

class LlamaService:
    def __init__(self, connection_string: str):
        """
        Initialize LlamaService with shared LLM instances and database connection
        
        Args:
            connection_string: PostgreSQL connection string including pgvector database
        """
        # Initialize LLM models
        self.llm_vision = ChatOllama(
            model="llama3.2-vision", 
            temperature=0.1, 
            n_gpu_layers=-1,
        )
        self.llm_base = ChatOllama(
            model="llama3.2", 
            temperature=0.1, 
            n_gpu_layers=-1,
        )
        
        # Initialize database connection
        self.connection_string = connection_string
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        # Initialize PGVector
        self.vector_store = PGVector(
            connection_string=connection_string,
            embedding_function=self.embeddings,
            collection_name="schema_knowledge",
            pre_delete_collection=False  # Prevent deleting existing data
        )
        
        # Cache for schema information
        self._schema_cache = None
        
        # Initialize schema knowledge
        self._init_schema_knowledge()
    
    def _init_schema_knowledge(self):
        """Initialize schema knowledge from database"""
        try:
            # Check if knowledge base exists
            schema_exists = self.vector_store.similarity_search("test", k=1)
            if not schema_exists:
                self.update_schema_knowledge()
        except:
            # If error (e.g. collection doesn't exist), create new knowledge base
            self.update_schema_knowledge()
    
    def _get_db_connection(self):
        """Create and return a database connection"""
        return psycopg2.connect(self.connection_string)

    def update_schema_knowledge(self):
        """Update vector store with current schema information"""
        schema_info = self.get_detailed_schema()
        
        # Create embeddings for schema information
        texts = [
            schema_info.split('\n'),  # Split by sections
        ]
        
        # Store in vector database
        self.vector_store.add_texts(texts)
        
    def get_relevant_schema_info(self, query: str) -> str:
        """Get relevant schema information based on query context"""
        results = self.vector_store.similarity_search(query, k=2)
        return "\n".join([doc.page_content for doc in results])

    def validate_sql_query(self, query: str) -> bool:
        """Validate SQL query"""
        valid_starts = ['SELECT', 'WITH']
        query = query.strip().upper()
        return any(query.startswith(keyword) for keyword in valid_starts)
    
    def clean_sql_query(self, query: str) -> str:
        """Clean SQL query from unwanted keywords and characters"""
        cleaned = query.strip().lower()
        
        # Remove SQL keywords and clean up
        cleaned = re.sub(r'^sql\s+', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+sql\s+', ' ', cleaned, flags=re.IGNORECASE)
        
        if cleaned.startswith('sql'):
            cleaned = query[3:].strip()
        else:
            cleaned = query.strip()
        
        # Remove potentially harmful characters and comments
        cleaned = cleaned.replace('`', '')
        cleaned = re.sub(r';.*$', '', cleaned)
        cleaned = re.sub(r'--.*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned = ' '.join(cleaned.split())
        
        return cleaned

    def validate_column_names(self, query: str) -> bool:
        """Validate column names in query using cached schema information"""
        if not self._schema_cache:
            self._schema_cache = self.get_schema_from_db()
            
        query = query.lower()
        for view, columns in self._schema_cache.items():
            if view in query:
                column_matches = re.findall(r'select\s+(.+?)\s+from', query)
                if not column_matches:
                    continue
                    
                cols_in_query = column_matches[0].split(',')
                cols_in_query = [c.strip() for c in cols_in_query]
                
                if '*' in cols_in_query:
                    return True
                    
                return all(any(col in c for c in cols_in_query) for col in columns)
        return False
        
    def get_schema_from_db(self) -> Dict[str, List[str]]:
        """Get schema information directly from database"""
        with self._get_db_connection() as conn:
            with conn.cursor() as cur:
                # Query to get view columns
                cur.execute("""
                    SELECT table_name, column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'vw_%'
                """)
                
                schema_info = {}
                for table_name, column_name in cur.fetchall():
                    if table_name not in schema_info:
                        schema_info[table_name] = []
                    schema_info[table_name].append(column_name)
                    
        return schema_info

    def generate_sql_query(self, question: str) -> str:
        """Generate SQL query based on user question with context-aware schema information"""
        # Get relevant schema information for the question
        relevant_schema = self.get_relevant_schema_info(question)
        
        system_prompt = relevant_schema + """
        ATURAN WAJIB:
        1. JANGAN PERNAH menulis kata 'sql' di awal atau di tengah query
        2. Query HARUS dimulai langsung dengan kata SELECT
        3. Gunakan nama kolom yang tepat dari skema
        4. Gunakan COUNT, GROUP BY, ORDER BY untuk hasil yang informatif
        5. Untuk jenis kelamin gunakan legend khusus dengan double stack
        6. Selalu sertakan ORDER BY untuk hasil yang terurut
        7. Jika menggunakan nama_pangkat, gunakan last_pangkat dari view personel analytic
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", question)
        ])
        
        chain = prompt | self.llm_vision | StrOutputParser()
        sql = chain.invoke({"question": question})
        cleaned_sql = self.clean_sql_query(sql)
        
        # Validate and retry if necessary
        if not self.validate_sql_query(sql) or not self.validate_column_names(sql):
            specific_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", f"Query tidak valid. Buat query baru untuk: {question}")
            ])
            
            chain = specific_prompt | self.llm_vision | StrOutputParser()
            sql = chain.invoke({"question": question})
            cleaned_sql = self.clean_sql_query(sql)
            
        return cleaned_sql

    def get_analysis_response(self, df_results: pd.DataFrame, viz_description: str) -> str:
        """Generate analysis response with context"""
        context = f"""
        Data yang dianalisis:
        {df_results.to_string() if not df_results.empty else 'Tidak ada data'}
        
        Deskripsi visualisasi:
        {viz_description}
        
        Berikan analisis komprehensif dengan mempertimbangkan:
        1. Tren utama dalam data
        2. Distribusi nilai
        3. Anomali atau pola menarik
        4. Rekomendasi berdasarkan analisis
        """
        
        return self.llm_base.predict(context)

    def generate_full_response(self, user_query: str, df_results: pd.DataFrame, 
                             viz_description: str, chat_history: list) -> str:
        """Generate complete response with improved context awareness"""
        template = """
        Analisis Data Personel:
        
        Pertanyaan: {question}
        
        Data Hasil Query:
        {raw_data}
        
        Visualisasi:
        {viz_description}
        
        Analisis Komprehensif:
        {analysis}
        
        Rekomendasi Tindak Lanjut:
        Berdasarkan analisis di atas, berikut beberapa rekomendasi yang dapat dipertimbangkan:
        1. {recommendations}
        
        Apakah Anda membutuhkan informasi lebih detail tentang aspek tertentu?
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", template),
            ("user", user_query)
        ])
        
        chain = RunnablePassthrough.assign(
            raw_data=lambda x: df_results.to_string() if not df_results.empty else "Data tidak ditemukan",
            viz_description=lambda x: viz_description,
            analysis=lambda x: self.get_analysis_response(df_results, viz_description),
            recommendations=lambda x: self.llm_base.predict("Berikan 3 rekomendasi berdasarkan data")
        ) | prompt | self.llm_base | StrOutputParser()
        
        return chain.invoke({
            "question": user_query,
            "query_result": f"Query yang digunakan: {self.generate_sql_query(user_query)}",
            "chat_history": chat_history
        })

def format_error_message(error: Exception) -> str:
    """Format error message for user display"""
    return f"Maaf, terjadi kesalahan dalam memproses permintaan Anda. Detail: {str(error)}"