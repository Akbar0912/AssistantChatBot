# database_manager.py

import os
from typing import Optional, Tuple
import pandas as pd
from langchain_community.utilities import SQLDatabase
from query_optimization import EnhancedQueryGenerator, DatabaseSchema

class DatabaseManager:
    """Manages database connections and query execution"""
    
    def __init__(self, connection_params: dict):
        self.connection_params = connection_params
        self.db = self._init_database()
        self.query_generator = EnhancedQueryGenerator()
        self.setup_schemas()
    
    def _init_database(self) -> SQLDatabase:
        """Initialize database connection"""
        db_uri = (
            f"postgresql://{self.connection_params['user']}:{self.connection_params['password']}"
            f"@{self.connection_params['host']}:{self.connection_params['port']}"
            f"/{self.connection_params['database']}"
        )
        return SQLDatabase.from_uri(
            db_uri,
            schema="public",
            view_support=True
        )
    
    def setup_schemas(self):
        """Initialize database schemas"""
        personel_schema = DatabaseSchema(
            table_name="vw_personel_analytic",
            columns={
                "personelid": "ID unik personel (integer)",
                "nama": "Nama lengkap personel (varchar)",
                "nrp": "Nomor registrasi personel (varchar)",
                "satuan": "Nama satuan kerja (varchar)",
                "matra": "Matra (AD/AL/AU/ASN) pangkat khusus (varchar)",
                "jabatan_terakhir_nama_jabatan": "Nama jabatan terakhir (varchar)",
                "last_pangkat": "Pangkat terakhir (varchar)",
                "pendidikan_terakhir_nama_sekolah": "Nama sekolah terakhir (varchar)",
                "pendidikan_terakhir_tahun_lulus": "Tahun lulus (integer)",
                "gaji_terakhir_gaji_pokok": "Gaji pokok terakhir (numeric)",
            },
            description="View utama untuk analisis data personel",
            example_queries=[
                """
                SELECT 
                    satuan,
                    COUNT(*) as jumlah_personel,
                    AVG(gaji_terakhir_gaji_pokok) as rata_rata_gaji
                FROM vw_personel_analytic
                GROUP BY satuan
                ORDER BY jumlah_personel DESC
                """,
                """
                SELECT 
                    p.nama,
                    p.nrp,
                    p.last_pangkat,
                    u.umur
                FROM vw_personel_analytic p
                JOIN vw_umur_personel u ON p.personelid = u.personelid
                WHERE p.matra = 'AD'
                ORDER BY u.umur DESC
                """
            ],
            relationships={
                "vw_umur_personel": "personelid",
                "vw_pangkat_tunggal": "nrp"
            }
        )
        
        self.query_generator.register_schema(personel_schema)
    
    def execute_query(self, query: str) -> Optional[pd.DataFrame]:
        """Execute SQL query and return results"""
        try:
            engine = self.db._engine
            return pd.read_sql_query(query, engine)
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            return None
    
    def process_question(self, question: str) -> Tuple[str, Optional[pd.DataFrame]]:
        """Process user question and return query results"""
        query = self.query_generator.generate_optimized_query(question)
        
        if not self.query_generator.validate_query(query):
            return "Invalid query generated", None
        
        results = self.execute_query(query)
        return query, results