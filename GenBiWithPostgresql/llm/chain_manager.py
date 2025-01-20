from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from openai import OpenAI
from langchain_openai import ChatOpenAI
import pandas as pd
import re
import os
from dotenv import load_dotenv

load_dotenv()

class LlamaService:
    def __init__(self):
        """Initialize LlamaService with shared LLM instances"""
        self.llm_vision = ChatOllama(
                            model="llama3sql", 
                            temperature=0.1, 
                            n_gpu_layers=-1,
                            # num_gqa = 8,
                            # repeat_penalty = 0,
                            # top_p = 0.9
                            )
        self.llm_base = ChatOllama(
                            model="llama3sql", 
                            temperature=0.1, 
                            n_gpu_layers=-1,
                            # num_gqa = 8,
                            # repeat_penalty = 0
                            )
    
    # Jika ingin menggunakan model dari OpenAI
    # def __init__(self):
    #     """Initialize OpenAIService with shared OpenAI instances"""
    #     api_key = os.getenv('OPENAI_API_KEY')
    #     self.client = OpenAI(api_key=api_key)
    #     # Using GPT-4 for vision tasks and GPT-3.5 for text
    #     self.llm_vision = ChatOpenAI(
    #         model="gpt-3.5-turbo",
    #         temperature=0.1,
    #         api_key=api_key
    #     )
    #     self.llm_base = ChatOpenAI(
    #         model="gpt-3.5-turbo",
    #         temperature=0.1,
    #         api_key=api_key
    #     )
    
    def extract_sql_query(self, text: str) -> str:
        """Extract only the SQL query from text, supporting both WITH and SELECT"""
        # Find query starting with either WITH or SELECT
        pattern = r'(WITH\s+.*?AS\s*\(.*\)\s*SELECT.*|SELECT\s+.*?)(?=;|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(0).strip()
        return text
    
    def validate_sql_query(self, query: str) -> bool:
        """Validate SQL query"""
        valid_starts = ['SELECT', 'WITH']
        query = query.strip().upper()
        return any(query.startswith(keyword) for keyword in valid_starts)
    
    def clean_sql_query(self, query: str) -> str:
        """Clean SQL query from unwanted keywords and characters"""
        cleaned = query.strip().lower()
        
        cleaned = re.sub(r'^sql\s+', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+sql\s+', ' ', cleaned, flags=re.IGNORECASE)
        
        if cleaned.startswith('sql'):
            cleaned = query[3:].strip()
        else:
            cleaned = query.strip()
        
        cleaned = cleaned.replace('`', '')
        cleaned = re.sub(r';.*$', '', cleaned)
        cleaned = re.sub(r'--.*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
        cleaned = ' '.join(cleaned.split())
        
        # Normalisasi whitespace dengan mempertahankan format CTE
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Perbaiki formatting untuk WITH clause
        cleaned = re.sub(r'WITH\s+(\w+)\s+AS\s*\(', r'WITH \1 AS (', cleaned, flags=re.IGNORECASE)
        
        return cleaned

    def validate_column_names(self, query: str) -> bool:
        """Validate column names in query"""
        valid_columns = {
            'vw_personel_analytic': [
                'tugas_dinas_terakhir_tanggal_selesai', 'pendidikan_terakhir_tugas_belajar', 'jabatan_terakhir_tanggal_kep', 
            'tugas_dinas_terakhir_tanggal_sprin', 'dikmil_terakhir_no_urut', 'gaji_terakhir_gaji_pokok', 'tmt_dikma', 
            'gaji_terakhir_bln_dibayar', 'jabatan_terakhir_tanggal_sprin', 'jabatan_terakhir_tmt_jabatan', 'last_tmt_pangkat', 
            'tmt_dikmilti', 'gaji_terakhir_gaji_lama', 'dikmil_terakhir_tanggal_sk', 'dikmil_terakhir_tanggal_mulai', 
            'tugas_operasi_terakhir_no_urut', 'dikmil_terakhir_tanggal_selesai', 'tgl_sk_cpns', 'tugas_operasi_terakhir_tanggal_mulai', 
            'tugas_operasi_terakhir_tanggal_selesai', 'tmt_kategori', 'tmt_tni', 'tugas_operasi_terakhir_tanggal_kep', 
            'tugas_operasi_terakhir_tmt_operasi', 'dikmil_terakhir_tanggal_kep', 'dikmil_terakhir_tmt_pddk', 'tgl_sk_pns', 
            'tmt_perwira', 'gaji_terakhir_tmt_pangkat', 'pendidikan_terakhir_no_urut', 'tmt_cpns', 'update_tgl_foto', 
            'tgl_sk_tni', 'diklat_terakhir_tanggal_mulai', 'diklat_terakhir_tanggal_selesai', 'tmt_pns', 'tmt_kemhan', 
            'pendidikan_terakhir_tanggal_sttb', 'tgl_lahir', 'last_tmt_jabatan', 'diklat_terakhir_jam_pelajaran', 
            'bahasa_terakhir_no_urut', 'jabatan_terakhir_tmt_jabatan_selesai', 'tmt_pemberhentian', 'jabatan_terakhir_tgl_sk', 
            'tgl_pensiun', 'pendidikan_terakhir_ipk', 'jabatan_terakhir_is_struktural', 'tanda_jasa_terakhir_no_urut', 
            'pendidikan_terakhir_tanggal_kep', 'pendidikan_terakhir_tmt_pddk', 'gaji_terakhir_no_urut', 
            'pendidikan_terakhir_hapus_sementara', 'tanda_jasa_terakhir_tanggal_kep', 'tanda_jasa_terakhir_tmt_tanda_jasa', 
            'tinggi', 'gaji_terakhir_tanggal_sk', 'tugas_dinas_terakhir_no_urut', 'gaji_terakhir_tmt_sk', 
            'jabatan_terakhir_no_urut', 'berat', 'tugas_dinas_terakhir_tanggal_mulai', 'no_randis', 'no_label', 
            'no_karsu_karis', 'no_kps_kpi', 'no_regis', 'email_kantor', 'ciri_khusus', 'bentuk_muka', 'no_sk_cpns', 
            'file_sk_cpns', 'no_sk_pns', 'file_sk_pns', 'no_sk_tni', 'file_sk_tni', 'no_sk_kemhan', 'ket_pindah', 
            'no_sk_pensiun', 'jenis_jabatan', 'tipe_jabatan', 'tipe_pegawai','status_pegawai', 'tempat_lahir_id_sapk', 
            'tingkat_pendidikan_nama', 'instansi_induk_nama', 'instansi_kerja_nama', 'unor_nama', 'unor_induk_nama', 
            'mk_tahun', 'mk_bulan', 'kpkn_nama', 'nip_lama', 'jenis_pegawai_id_sapk', 'kedudukan_hukum_id_sapk', 
            'nip_nrp_atasan', 'nama_atasan', 'satuan_atasan', 'jabatan_atasan', 'pangkat_atasan', 'jabatan_terakhir_no_kep', 
            'jabatan_terakhir_no_sprin', 'jabatan_terakhir_satker', 'jabatan_terakhir_satker_asal', 'jabatan_terakhir_nama_jabatan', 
            'jabatan_terakhir_jenis_jabatan', 'jabatan_terakhir_gol_jabatan', 'jabatan_terakhir_pangkat', 'jabatan_terakhir_keterangan', 
            'jabatan_terakhir_nrp_penetap', 'jabatan_terakhir_nama_penetap', 'jabatan_terakhir_jabatan_penetap', 
            'jabatan_terakhir_pangkat_penetap', 'jabatan_terakhir_sumber_data', 'jabatan_terakhir_jabatan_anomali', 
            'jabatan_terakhir_tipe_jabatan', 'jabatan_terakhir_no_sk', 'jabatan_terakhir_sk_file', 'gaji_terakhir_no_sk', 
            'gaji_terakhir_pejabat_penetap', 'gaji_terakhir_masa_kerja_th', 'gaji_terakhir_masa_kerja_bl', 
            'gaji_terakhir_jenis_kenaikan', 'gaji_terakhir_sudah_dibayar', 'gaji_terakhir_validator', 'gaji_terakhir_is_trigger', 
            'gaji_terakhir_kppn', 'gaji_terakhir_nrp_penetap', 'gaji_terakhir_nama_penetap', 'gaji_terakhir_jabatan_penetap', 
            'gaji_terakhir_pangkat_penetap', 'gaji_terakhir_sumber_data', 'pendidikan_terakhir_jurusan', 
            'pendidikan_terakhir_nama_sekolah', 'pendidikan_terakhir_tempat_sekolah', 'pendidikan_terakhir_kepala_sekolah', 
            'pendidikan_terakhir_no_sttb', 'pendidikan_terakhir_tahun_lulus', 'pendidikan_terakhir_nama_bidang', 
            'pendidikan_terakhir_nama_pendidikan', 'pendidikan_terakhir_kode_gelar', 'pendidikan_terakhir_kode_bidang', 
            'pendidikan_terakhir_akreditasi', 'pendidikan_terakhir_no_kep', 'pendidikan_terakhir_keterangan', 
            'pendidikan_terakhir_sumber_data', 'pendidikan_terakhir_pendidikan_anomali', 'pendidikan_terakhir_negara', 
            'pendidikan_terakhir_gelar_depan', 'pendidikan_terakhir_gelar_belakang', 'pendidikan_terakhir_file_ijazah', 
            'dikmil_terakhir_dikmil', 'dikmil_terakhir_jenis_dikmil', 'dikmil_terakhir_tahun_lulus', 'dikmil_terakhir_penyelenggara', 
            'dikmil_terakhir_ranking_dikmil', 'dikmil_terakhir_jumlah_siswa', 'dikmil_terakhir_status_aktif', 
            'dikmil_terakhir_jenis_pendidikan', 'dikmil_terakhir_tempat', 'dikmil_terakhir_no_sk', 'dikmil_terakhir_no_kep', 
            'dikmil_terakhir_keterangan', 'dikmil_terakhir_sumber_data', 'dikmil_terakhir_pendidikan_militer_anomali', 
            'dikmil_terakhir_angkatan', 'dikmil_terakhir_file', 'kinerja_terakhir_tahun', 'kinerja_terakhir_jabatan', 
            'kinerja_terakhir_satuan', 'kinerja_terakhir_nilai_skp', 'kinerja_terakhir_nilai_perilaku', 'kinerja_terakhir_nilai_prestasi', 
            'kinerja_terakhir_nrp_penetap', 'kinerja_terakhir_nama_penetap', 'kinerja_terakhir_jabatan_penetap', 
            'kinerja_terakhir_pangkat_penetap', 'kinerja_terakhir_nilai_orientasi_pelayanan', 'kinerja_terakhir_nilai_komitmen', 
            'kinerja_terakhir_nilai_kerjasama', 'kinerja_terakhir_nilai_integritas', 'kinerja_terakhir_nilai_disiplin', 
            'kinerja_terakhir_nilai_kepemimpinan', 'kinerja_terakhir_nilai_ppkp', 'kinerja_terakhir_file_kinerja', 'kinerja_terakhir_nama_atasan_penetap', 
            'tugas_dinas_terakhir_negara', 'tugas_dinas_terakhir_tugas', 'tugas_dinas_terakhir_keterangan', 'tugas_dinas_terakhir_tahun', 
            'tugas_dinas_terakhir_no_sprin', 'tugas_dinas_terakhir_nrp_penetap', 'tugas_dinas_terakhir_nama_penetap', 'tugas_dinas_terakhir_jabatan_penetap', 
            'tugas_dinas_terakhir_pangkat_penetap', 'tugas_dinas_terakhir_sumber_data', 'tugas_dinas_terakhir_tugas_ln_anomali', 'tugas_dinas_terakhir_lama_tugas', 
            'tugas_dinas_terakhir_lokasi', 'tugas_dinas_terakhir_provinsi', 'tugas_dinas_terakhir_kabkota', 'tugas_dinas_terakhir_file_dinas', 
            'tugas_operasi_terakhir_operasi', 'tugas_operasi_terakhir_keterangan', 'tugas_operasi_terakhir_tahun', 'tugas_operasi_terakhir_nokep', 
            'tugas_operasi_terakhir_lokasi', 'tugas_operasi_terakhir_jabatan', 'tugas_operasi_terakhir_negara', 'tugas_operasi_terakhir_sumber_data', 
            'tugas_operasi_terakhir_tugas_operasi_anomali', 'tugas_operasi_terakhir_provinsi', 'tugas_operasi_terakhir_kabkota', 'tugas_operasi_terakhir_file_tugas', 
            'diklat_terakhir_nama_diklat', 'diklat_terakhir_surat_tugas', 'diklat_terakhir_tempat', 'diklat_terakhir_hasil', 'diklat_terakhir_tahun', 'diklat_terakhir_file_diklat', 
            'bahasa_terakhir_nama_bahasa', 'bahasa_terakhir_kemampuan_bicara', 'bahasa_terakhir_kemampuan_membaca', 'bahasa_terakhir_kemampuan_menulis', 'bahasa_terakhir_keterangan', 'bahasa_terakhir_file_bahasa', 
            'tanda_jasa_terakhir_nama_tanda_jasa', 'tanda_jasa_terakhir_sumber_data', 'tanda_jasa_terakhir_file_tanda_jasa', 'tanda_jasa_terakhir_nama_pemberi_tanda_jasa', 'tanda_jasa_terakhir_keterangan', 'diklat_terakhir_tanggal_kep', 
            'diklat_terakhir_file_tanggal_kep', 'diklat_terakhir_is_trigger', 'jenis_kelamin', 'last_pangkat'
            ],
            'vw_umur_personel': [
                'personelid', 'nama', 'tgllahir', 'umur', 'nrp'
            ],
            'vw_pangkat_tunggal': [
                'nip_tunggal', 'nama_tunggal', 'nourut', 'nip', 'nama', 
                'nama_pangkat', 'tmt_pangkat', 'nokep'
            ]
        }
        
        query = query.lower()
        for view, columns in valid_columns.items():
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

    def get_detailed_schema(self):
        """Get detailed database schema information"""
        return """Anda adalah ahli SQL yang bekerja dengan database PostgreSQL. 
        
        PENTING: 
        - hasilkan hanya berbentuk query sql yang valid
        - Query HARUS dimulai dengan WITH (untuk CTE) atau SELECT
        - JANGAN menambahkan titik koma (;) di akhir query
        - Gunakan CTE (WITH) untuk query kompleks yang membutuhkan temporary result
        - JANGAN gunakan backtick (`)
        - JANGAN tambahkan kata 'sql' di awal query atau di tengah query
        - Gunakan nama kolom yang tepat
        - Query harus dimulai langsung dengan SELECT
        - Ini contoh format yang BENAR:
        SELECT kolom FROM tabel
        - Ini contoh format yang SALAH:
        sql SELECT kolom FROM tabel
        SQL query: SELECT kolom FROM tabel
        - Gunakan COUNT, GROUP BY, ORDER BY untuk hasil yang informatif
        - Tambahkan alias untuk nama kolom yang lebih jelas
        - Urutkan hasil untuk mempermudah pembacaan
        - untuk jenis kelamin agar dijadikan sebagai legend khusus untuk jenis kelamin jadikan seperti double stack pada value nya
        - jika terdapat nama_pangkat = last_pangkat diambil dari view personel analytic
        - view yang memiliki personelid memiliki relasi ke tabel personel yang berisi semua informasi terkait personel
        - khusus untuk umur karena bertipe text atau string konversi terlebih dahulu ke dalam integer atau numerik
        
        Database memiliki view dan tabel:
        
        1. public.personel
        2. public.sumberprajurit
        
        
        ---------------------------------------------------------
        1. public.vw_personel_analytic
        Kolom-kolom penting:
        - personelid (integer) - ID unik personel
        - nama (varchar) - Nama lengkap personel
        - nrp (varchar) - Nomor registrasi personel
        - satuan (varchar) - Nama satuan kerja
        - matra (varchar) - Matra (AD/AL/AU/ASN) pangkat khusus
        - jabatan_terakhir_nama_jabatan (varchar) - Nama jabatan terakhir
        - last_pangkat (varchar) - Pangkat terakhir
        - pendidikan_terakhir_nama_pendidikan (varchar) - tingkat pendidikan
        - pendidikan_terakhir_nama_sekolah (varchar) - Nama sekolah terakhir
        - pendidikan_terakhir_tahun_lulus (integer) - Tahun lulus
        - gaji_terakhir_gaji_pokok (numeric) - Gaji pokok terakhir
        - tipe_pegawai (varchar) - jenis dari status pegawai
        - jenis_kelamin (varchar) - jenis kelamin atau gender (L/P)

        2. public.vw_umur_personel
        Kolom-kolom:
        - personelid (integer) - ID unik personel
        - nama (varchar) - Nama lengkap
        - tgllahir (date) - Tanggal lahir
        - umur (integer) - Umur dalam tahun
        - nrp (varchar) - Nomor registrasi personel
        
        3. public.vw_pangkat_tunggal
        kolom-kolom:
        - nip_tunggal
        - nama_tunggal = nama panggilan
        - nourut
        - nip = nomor registrasi personel
        - nama = nama lengkap personel
        - nama_pangkat = pangkat terakhir (last_pangkat)
        - tmt_pangkat = tanggal penetapan pangkat
        - nokep
        """

    def generate_sql_query(self, question: str) -> str:
        """Generate SQL query based on user question"""
        system_prompt = self.get_detailed_schema()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", """Analisis pertanyaan berikut dan buat query SQL yang tepat:
            Pertanyaan: {question}
            """)
        ])
        
        chain = prompt | self.llm_vision | StrOutputParser()
        
        # Generate initial query
        sql = chain.invoke({"question": question})
        cleaned_sql = self.clean_sql_query(sql)
        
        # Validate query
        if not self.validate_sql_query(sql) or not self.validate_column_names(sql):
            specific_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", f"Buat query SQL untuk: {question}")
            ])
            
            chain = specific_prompt | self.llm_vision | StrOutputParser()
            sql = chain.invoke({"question": question})
            cleaned_sql = self.clean_sql_query(sql)
            
        final_sql = self.extract_sql_query(cleaned_sql)
        return final_sql

    def get_analysis_response(self, df_results: pd.DataFrame, viz_description: str) -> str:
        """Generate analysis response using LLaMA"""
        return self.llm_base.predict(f"""Berikan analisis dari data berikut:
        Data: {df_results.to_string() if not df_results.empty else 'No data found'}
        Visualization Description: {viz_description}""")

    def generate_full_response(self, user_query: str, df_results: pd.DataFrame, viz_description: str, chat_history: list) -> str:
        """Generate complete response using LLaMA"""
        template = """
        Berdasarkan pertanyaan dan data yang tersedia:
        {question}

        DATA HASIL QUERY:
        {raw_data}
        
        Apakah Anda ingin informasi lebih detail tentang data tertentu?
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        
        chain = RunnablePassthrough.assign(
            raw_data=lambda x: df_results.to_string() if not df_results.empty else "No data found",
            # viz_description=lambda x: viz_description,
            # analysis=lambda x: self.get_analysis_response(df_results, viz_description)
        ) | prompt | self.llm_base | StrOutputParser()
        
        return chain.invoke({
            "question": user_query,
            "query_result": f"Query yang digunakan: {self.generate_sql_query(user_query)}",
            "chat_history": chat_history
        })
        
    @staticmethod
    def format_error_message(error: Exception) -> str:
        """Format error message for user display"""
        return f"Maaf, terjadi kesalahan dalam memproses permintaan Anda. Detail: {str(error)}"