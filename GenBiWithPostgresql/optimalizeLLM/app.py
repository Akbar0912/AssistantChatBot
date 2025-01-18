from typing import List, Dict, Tuple
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
import json
import re

class QueryTrainingSystem:
    def __init__(self, llm_model="llama3.2"):
        self.llm = ChatOllama(
            model=llm_model, 
            temperature=0.1,
            n_gpu_layers=-1
        )
        self.training_data = self.load_training_data()
        
    def load_training_data(self) -> List[Dict]:
        """Load training data from JSON file"""
        try:
            with open('query_training_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def save_training_data(self):
        """Save training data to JSON file"""
        with open('query_training_data.json', 'w') as f:
            json.dump(self.training_data, f, indent=2)
    
    def add_training_example(self, question: str, query: str, metadata: Dict = None):
        """Add new training example"""
        example = {
            "question": question,
            "query": query,
            "metadata": metadata or {},
            "variations": self.generate_question_variations(question)
        }
        self.training_data.append(example)
        self.save_training_data()
    
    def generate_question_variations(self, question: str) -> List[str]:
        """Generate variations of the question using LLM"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Buatkan 5 variasi pertanyaan yang bermakna sama dengan pertanyaan asli.
            Fokus pada:
            1. Variasi kata kunci
            2. Susunan kata berbeda
            3. Tingkat formalitas berbeda
            4. Tambahan detail kecil
            
            Format output: satu pertanyaan per baris"""),
            ("user", question)
        ])
        
        response = self.llm.invoke(prompt.format_messages(question=question))
        variations = [v.strip() for v in response.content.split('\n') if v.strip()]
        return variations
    
    def find_best_match(self, question: str) -> Tuple[str, float]:
        """Find best matching query from training data"""
        best_score = 0
        best_query = None
        
        for example in self.training_data:
            # Check main question
            score = self.calculate_similarity(question, example["question"])
            if score > best_score:
                best_score = score
                best_query = example["query"]
            
            # Check variations
            for variation in example["variations"]:
                score = self.calculate_similarity(question, variation)
                if score > best_score:
                    best_score = score
                    best_query = example["query"]
        
        return best_query, best_score
    
    def calculate_similarity(self, question1: str, question2: str) -> float:
        """Calculate similarity between two questions"""
        # Preprocessing
        q1 = self.preprocess_question(question1)
        q2 = self.preprocess_question(question2)
        
        # Get common words
        words1 = set(q1.split())
        words2 = set(q2.split())
        common_words = words1.intersection(words2)
        
        # Calculate Jaccard similarity
        if not words1 or not words2:
            return 0
        
        return len(common_words) / len(words1.union(words2))
    
    def preprocess_question(self, question: str) -> str:
        """Preprocess question for comparison"""
        # Lowercase
        question = question.lower()
        
        # Remove punctuation
        question = re.sub(r'[^\w\s]', '', question)
        
        # Remove stop words (bisa ditambahkan stop words bahasa Indonesia)
        stop_words = {'yang', 'di', 'ke', 'dari', 'pada', 'dalam', 'untuk', 'dengan', 'dan', 'atau', 'ini', 'itu'}
        words = question.split()
        words = [w for w in words if w not in stop_words]
        
        return ' '.join(words)
    
    def validate_query(self, query: str) -> bool:
        """Validate SQL query syntax and structure"""
        # Basic validation
        if not query.strip().upper().startswith('SELECT'):
            return False
            
        # Check for required keywords
        required_keywords = ['FROM', 'ORDER BY']
        for keyword in required_keywords:
            if keyword.upper() not in query.upper():
                return False
                
        return True
    
    def analyze_query_pattern(self, query: str) -> Dict:
        """Analyze query pattern for metadata"""
        pattern = {
            "tables_used": [],
            "aggregations": [],
            "grouping": [],
            "ordering": []
        }
        
        # Extract tables
        tables = re.findall(r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', query, re.IGNORECASE)
        pattern["tables_used"] = tables
        
        # Extract aggregations
        aggs = re.findall(r'(COUNT|SUM|AVG|MIN|MAX)\s*\(', query, re.IGNORECASE)
        pattern["aggregations"] = aggs
        
        # Extract GROUP BY columns
        if 'GROUP BY' in query.upper():
            group_by = re.findall(r'GROUP BY\s+(.+?)(?:ORDER BY|HAVING|$)', query, re.IGNORECASE)
            if group_by:
                pattern["grouping"] = [col.strip() for col in group_by[0].split(',')]
        
        # Extract ORDER BY columns
        if 'ORDER BY' in query.upper():
            order_by = re.findall(r'ORDER BY\s+(.+?)$', query, re.IGNORECASE)
            if order_by:
                pattern["ordering"] = [col.strip() for col in order_by[0].split(',')]
        
        return pattern

    def generate_sql_query(self, question: str) -> str:
        """Generate SQL query based on training data"""
        query, confidence = self.find_best_match(question)
        
        if confidence > 0.7:  # Threshold bisa disesuaikan
            return query
            
        # Jika tidak ada match yang baik, gunakan LLM
        return None  # Implement fallback to LLM if needed

# Contoh penggunaan:
training_system = QueryTrainingSystem()

# Menambahkan contoh training
training_system.add_training_example(
    question="Berapa jumlah personel berdasarkan pangkat?",
    query="SELECT last_pangkat, COUNT(*) as jumlah_personel FROM vw_personel_analytic GROUP BY last_pangkat ORDER BY jumlah_personel DESC",
)

# Menggunakan sistem
query = training_system.generate_sql_query("Tolong tampilkan data personel per pangkat")


# from langchain_ollama import OllamaEmbeddings

# embeddings = OllamaEmbeddings(
#     model="nomic-embed-text",
# )

# input_text = "The meaning of life is 42"
# vector = embeddings.embed_query(input_text)
# print(vector[:3])


# import os
# from typing import List, Dict, Optional
# from langchain_community.embeddings import OllamaEmbeddings
# from langchain_community.vectorstores.pgvector import PGVector
# from langchain_community.llms import Ollama
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.chains import RetrievalQA
# from langchain.schema import Document
# import psycopg2
# from tqdm import tqdm
# import logging
# from datetime import date, datetime
# import json
# import concurrent.futures
# from decimal import Decimal

# class DecimalEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, Decimal):
#             return str(obj)
#         return super(DecimalEncoder, self).default(obj)

# class LargeScaleRAG:
#     def __init__(
#         self,
#         connection_string: str,
#         collection_name: str = "enterprise_knowledge_base",
#         model_name: str = "llama3.2",
#         model_embed: str = "nomic-embed-text",
#         config_path: Optional[str] = None
#     ):
#         self.connection_string = connection_string
#         self.collection_name = collection_name
#         self.embeddings = OllamaEmbeddings(model=model_embed)
#         self.llm = Ollama(model=model_name)
#         self.vector_store = None
#         self.config_path = config_path
        
#         logging.basicConfig(
#             level=logging.INFO,
#             format='%(asctime)s - %(levelname)s - %(message)s',
#             filename='rag_processing.log'
#         )
#         self.logger = logging.getLogger(__name__)

#     def get_database_schema(self) -> Dict:
#         """Mendapatkan informasi schema database."""
#         schema_info = {
#             'tables': [],
#             'views': []
#         }
        
#         conn = psycopg2.connect(self.connection_string)
#         try:
#             cur = conn.cursor()
            
#             # Ambil daftar tabel
#             cur.execute("""
#                 SELECT table_name, column_name, data_type 
#                 FROM information_schema.columns 
#                 WHERE table_schema = 'public' 
#                 AND table_name NOT LIKE 'pg_%'
#                 AND table_name NOT LIKE 'langchain%'
#             """)
            
#             for row in cur.fetchall():
#                 table_name, column_name, data_type = row
#                 if table_name not in [t['name'] for t in schema_info['tables']]:
#                     schema_info['tables'].append({
#                         'name': table_name,
#                         'columns': []
#                     })
                
#                 table_idx = next(i for i, t in enumerate(schema_info['tables']) 
#                                if t['name'] == table_name)
#                 schema_info['tables'][table_idx]['columns'].append({
#                     'name': column_name,
#                     'type': data_type
#                 })
            
#             # Ambil daftar view
#             cur.execute("""
#                 SELECT viewname, definition 
#                 FROM pg_views 
#                 WHERE schemaname = 'public'
#             """)
            
#             for row in cur.fetchall():
#                 view_name, definition = row
#                 schema_info['views'].append({
#                     'name': view_name,
#                     'definition': definition
#                 })
            
#             return schema_info
            
#         finally:
#             conn.close()

#     def generate_table_configs(self, schema_info: Dict) -> List[Dict]:
#         """Generate konfigurasi untuk setiap tabel dan view."""
#         configs = []
        
#         # Fungsi helper untuk mendeteksi kolom teks
#         def is_text_column(data_type):
#             return data_type.lower() in ['text', 'varchar', 'char', 'character varying']
        
#         # Konfigurasi untuk tabel
#         for table in schema_info['tables']:
#             text_columns = [col['name'] for col in table['columns'] 
#                           if is_text_column(col['type'])]
            
#             if text_columns:  # Hanya proses tabel dengan kolom teks
#                 metadata_columns = [col['name'] for col in table['columns'] 
#                                  if not is_text_column(col['type'])]
                
#                 configs.append({
#                     "table_name": table['name'],
#                     "query": f"""
#                         SELECT {', '.join(text_columns + metadata_columns)}
#                         FROM {table['name']}
#                     """,
#                     "content_fields": text_columns,
#                     "metadata_fields": metadata_columns,
#                     "source_type": "table"
#                 })
        
#         # Konfigurasi untuk views
#         for view in schema_info['views']:
#             configs.append({
#                 "table_name": view['name'],
#                 "query": f"SELECT * FROM {view['name']}",
#                 "content_fields": ["*"],  # Akan diupdate saat runtime
#                 "metadata_fields": [],    # Akan diupdate saat runtime
#                 "source_type": "view"
#             })
        
#         return configs

#     def process_table_batch(self, config: Dict, batch_size: int = 1000) -> List[Document]:
#         """Proses satu tabel atau view dalam batch."""
#         documents = []
#         conn = psycopg2.connect(self.connection_string)
        
#         try:
#             cur = conn.cursor()
            
#             # Eksekusi query dengan batching
#             cur.execute(f"""
#                 DECLARE table_cursor CURSOR FOR {config['query']}
#             """)
            
#             while True:
#                 cur.execute(f"FETCH {batch_size} FROM table_cursor")
#                 rows = cur.fetchall()
                
#                 if not rows:
#                     break
                
#                 # Get column names if not already set
#                 if config['content_fields'] == ["*"]:
#                     column_names = [desc[0] for desc in cur.description]
#                     config['content_fields'] = [col for col in column_names 
#                                             if cur.description[column_names.index(col)].type_code 
#                                             in [25, 1043]]  # text & varchar type codes
#                     config['metadata_fields'] = [col for col in column_names 
#                                             if col not in config['content_fields']]
                
#                 for row in rows:
#                     row_dict = dict(zip([desc[0] for desc in cur.description], row))
                    
#                     for key, value in row_dict.items():
#                         if isinstance(value, Decimal):
#                             row_dict[key] = str(value)
#                         elif isinstance(value, datetime, date):
#                             row_dict[key] = value.isoformat()
                    
#                     # Combine content fields
#                     content = " ".join(str(row_dict.get(field, "")) 
#                                      for field in config['content_fields'])
                    
#                     # Prepare metadata
#                     metadata = {
#                         "source_table": config["table_name"],
#                         "source_type": config["source_type"],
#                         "processed_at": datetime.now().isoformat()
#                     }
                    
#                     for field in config['metadata_fields']:
#                         if field in row_dict:
#                             metadata[field] = row_dict[field]
                    
#                     documents.append(Document(
#                         page_content=content,
#                         metadata=metadata
#                     ))
            
#             cur.execute("CLOSE table_cursor")
#             return documents
            
#         finally:
#             conn.close()
    
#     def create_vector_store(self, documents: List[Document], batch_size: int = 100):
#         """Buat atau update vector store dengan batching."""
#         try:
#             if not self.vector_store:
#                 self.vector_store = PGVector.from_documents(
#                     documents=documents[:1],  # Initialize with first document
#                     embedding=self.embeddings,
#                     collection_name=self.collection_name,
#                     connection_string=self.connection_string,
#                 )
            
#             # Process remaining documents in batches
#             for i in tqdm(range(0, len(documents), batch_size)):
#                 batch = documents[i:i + batch_size]
#                 self.vector_store.add_documents(batch)
                
#         except Exception as e:
#             self.logger.error(f"Error in create_vector_store: {e}")
#             raise

#     def process_all_data(self):
#         """Proses semua tabel dan view."""
#         try:
#             # Get schema info
#             schema_info = self.get_database_schema()
#             self.logger.info(f"Found {len(schema_info['tables'])} tables and {len(schema_info['views'])} views")
            
#             # Generate configs
#             configs = self.generate_table_configs(schema_info)
#             self.logger.info(f"Generated {len(configs)} configurations")
            
#             # Process each table/view
#             all_documents = []
#             for config in tqdm(configs, desc="Processing tables/views"):
#                 try:
#                     documents = self.process_table_batch(config)
#                     all_documents.extend(documents)
#                     self.logger.info(f"Processed {config['table_name']}: {len(documents)} documents")
#                 except Exception as e:
#                     self.logger.error(f"Error processing {config['table_name']}: {e}")
#                     continue
            
#             # Create vector store
#             self.create_vector_store(all_documents)
#             self.logger.info("Vector store creation completed")
            
#         except Exception as e:
#             self.logger.error(f"Error in process_all_data: {e}")
#             raise

#     def query(self, question: str, source_type: str = None) -> dict:
#         """Query the system."""
#         if not self.vector_store:
#             self.vector_store = PGVector(
#                 connection_string=self.connection_string,
#                 collection_name=self.collection_name,
#                 embedding_function=self.embeddings,
#             )
        
#         search_kwargs = {"k": 5}
#         if source_type:
#             search_kwargs["filter"] = {"source_type": source_type}
        
#         qa_chain = RetrievalQA.from_chain_type(
#             llm=self.llm,
#             retriever=self.vector_store.as_retriever(search_kwargs=search_kwargs),
#             return_source_documents=True
#         )
        
#         return qa_chain({"query": question})

# # Contoh penggunaan
# if __name__ == "__main__":
#     # Konfigurasi koneksi
#     connection_string = "postgresql://postgres:password@localhost:5432/dumy"
    
#     # Inisialisasi sistem
#     rag_system = LargeScaleRAG(connection_string)
    
#     # Proses semua data
#     rag_system.process_all_data()
    
#     # Interface sederhana untuk query
#     while True:
#         question = input("\nMasukkan pertanyaan (atau 'quit' untuk keluar): ")
#         if question.lower() == 'quit':
#             break
        
#         result = rag_system.query(question)
#         print("\nJawaban:", result["result"])
#         print("\nSumber:")
#         for doc in result["source_documents"]:
#             print(f"- Dari: {doc.metadata['source_table']}")
#             print(f"  Tipe: {doc.metadata['source_type']}")
#             print(f"  Content: {doc.page_content[:200]}...")
#             print()