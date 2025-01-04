from typing import Optional, Dict, Any
import json
from langchain_ollama import ChatOllama
from config.modelLlm import LLMConfig
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage
import logging

class ChainManager:
    def __init__(self, schema_manager):
        """
        Initialize ChainManager dengan schema database dan konfigurasi LLM.
        Schema manager digunakan untuk mendapatkan informasi struktur database.
        """
        self.config = LLMConfig()
        self.schema_manager = schema_manager
        self.logger = self._setup_logging()
        self.system_message = self._create_system_prompt()
        self.chain = self.create_chain()

    def _setup_logging(self):
        """Menyiapkan sistem logging untuk debugging yang lebih baik."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def _create_system_prompt(self) -> str:
        """
        Membuat system prompt yang memberikan konteks tentang database dan tugas.
        Menggunakan informasi schema untuk memberikan pemahaman struktur data.
        """
        schema_text = self.schema_manager.get_table_schema_text()
        
        return f"""Anda adalah asisten SQL yang ahli dalam menganalisis data personel dan pejabat.

        {{schema_text}}
        {{query}}

        Tugas Anda adalah menganalisis pertanyaan pengguna dan memberikan:
        1. Query SQL yang optimal untuk menjawab pertanyaan
        2. Visualisasi yang sesuai untuk menampilkan data
        3. Penjelasan singkat tentang analisis yang dilakukan

        Berikan respons dalam format JSON seperti ini:
        {{
            "query": "<query SQL Anda>",
            "visualization": {{
                "type": "<line/bar/pie/table>",
                "title": "<judul chart>",
                "xAxis": "<label sumbu X>",
                "yAxis": "<label sumbu Y>"
            }},
            "explanation": "<penjelasan analisis Anda>"
        }}

        Panduan penting:
        - Gunakan LEFT JOIN untuk menghubungkan tabel
        - Berikan alias yang jelas (p untuk personel, mp untuk master_pejabat)
        - Sertakan WHERE clause yang relevan
        - Tambahkan ORDER BY yang sesuai
        - Pilih tipe visualisasi yang paling sesuai dengan data"""

    def create_chain(self):
        """
        Membuat chain LangChain dengan format yang benar.
        Menggunakan ChatPromptTemplate untuk memastikan format yang konsisten.
        """
        try:
            # Inisialisasi model LLM
            llm = ChatOllama(
                model=self.config.model,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repeat_penalty=self.config.repeat_penalty,
                timeout=self.config.timeout
            )

            # Membuat chat prompt template dengan format yang benar
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_message),
                ("human", "{input}")  # Menggunakan {input} sebagai placeholder
            ])

            # Membuat chain dengan format yang benar
            chain = prompt | llm

            return chain

        except Exception as e:
            error_msg = f"Gagal membuat chain: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Mengekstrak dan memvalidasi JSON dari response model.
        Menangani berbagai format response yang mungkin diberikan model.
        """
        try:
            # Mencari struktur JSON dalam response
            response = response.strip()
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("Tidak ditemukan struktur JSON dalam response")
                
            json_str = response[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            # Validasi struktur JSON
            required_fields = ['query', 'visualization', 'explanation']
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Field yang diperlukan tidak ada: {field}")
            
            # Validasi visualization
            viz = parsed['visualization']
            viz_fields = ['type', 'title', 'xAxis', 'yAxis']
            for field in viz_fields:
                if field not in viz:
                    raise ValueError(f"Field visualization tidak ada: {field}")
            
            if viz['type'].lower() not in ['line', 'bar', 'pie', 'table']:
                raise ValueError(f"Tipe visualization tidak valid: {viz['type']}")
                
            return parsed
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Gagal parsing JSON: {str(e)}")

    def process_query(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Memproses pertanyaan user dan mengembalikan hasil analisis.
        Menangani berbagai kasus error yang mungkin terjadi.
        """
        try:
            self.logger.info(f"Memproses pertanyaan: {question}")
            
            # Invoke chain dengan format yang benar
            response = self.chain.invoke({"input": question})
            
            # Mengambil teks response dari output model
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse dan validasi response
            result = self._parse_json_response(response_text)
            
            self.logger.info("Berhasil memproses query")
            return result
            
        except Exception as e:
            error_msg = f"Error saat memproses query: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)