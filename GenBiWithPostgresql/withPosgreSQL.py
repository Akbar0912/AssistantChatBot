import os
import streamlit as st 
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SQLDatabase
import re
from dotenv import load_dotenv
import pandas as pd
from visualization import create_visualization, generate_viz_description

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")

pwd = os.environ['DB_PASSWORD']
uid = os.environ['DB_USER']
server = "localhost"
db = os.environ['DB_NAME']
port = 5432

def get_detailed_schema():
    """Mendapatkan informasi detail skema database"""
    return """Anda adalah ahli SQL yang bekerja dengan database PostgreSQL. 
    
    PENTING: 
    - JANGAN gunakan backtick (`)
    - JANGAN tambahkan kata 'sql' di awal query
    - Gunakan nama kolom yang tepat
    - Query harus dimulai langsung dengan SELECT
    - Gunakan COUNT, GROUP BY, ORDER BY untuk hasil yang informatif
    - Tambahkan alias untuk nama kolom yang lebih jelas
    - Urutkan hasil untuk mempermudah pembacaan
    - nama_pangkat = last_pangkat
    
    Database memiliki dua view utama:

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
    - nama_pangkat = pangkat terakhir
    - tmt_pangkat = tanggal penetapan pangkat
    - nokep
    
    Contoh Query Valid:
    1. Mencari personel berdasarkan satuan:
    SELECT nama, nrp, jabatan_terakhir_nama_jabatan, pangkat
    FROM public.vw_personel_analytic 
    WHERE satuan = 'Kementerian Pertahanan'

    2. Mencari data umur personel:
    SELECT nama, umur, nrp
    FROM public.vw_umur_personel
    ORDER BY umur DESC

    3. Mencari personel berdasarkan matra:
    SELECT nama, nrp, pangkat, satuan
    FROM public.vw_personel_analytic
    WHERE matra = 'AD'
    
    4. mencari berdasarkan tingkat pendidikan tampilkan kolom pendidikan_terakhir_nama_pendidikan, jumlah personel dan juga totalnya :
    SELECT pendidikan_terakhir_nama_pendidikan AS "Tingkat Pendidikan", COUNT(personelid) AS "Jumlah Personel" 
    FROM public.vw_personel_analytic GROUP BY pendidikan_terakhir_nama_pendidikan 
    ORDER BY pendidikan_terakhir_nama_pendidikan
    
    4. mencari berdasarkan pendidikan dan pangkat untuk filter tertentu
    SELECT pendidikan_terakhir_nama_pendidikan AS "Tingkat Pendidikan", 
       last_pangkat AS "Pangkat", 
       COUNT(personelid) AS "Jumlah Personel"
    FROM public.vw_personel_analytic
    WHERE matra = 'ASN' 
    GROUP BY pendidikan_terakhir_nama_pendidikan, last_pangkat
    ORDER BY "Tingkat Pendidikan" ASC, "Pangkat" DESC; 
    """

def validate_sql_query(query: str) -> bool:
    """Validasi query SQL"""
    valid_starts = ['SELECT', 'WITH']
    query = query.strip().upper()
    return any(query.startswith(keyword) for keyword in valid_starts)

def clean_sql_query(query: str) -> str:
    """Membersihkan query SQL dari kata kunci dan karakter yang tidak diinginkan"""
    # Convert ke lowercase untuk pengecekan
    cleaned = query.strip().lower()
    
    cleaned = re.sub(r'^sql\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+sql\s+', ' ', cleaned, flags=re.IGNORECASE)
    
    # Hapus kata 'sql' di awal query dengan lebih teliti
    if cleaned.startswith('sql'):
        cleaned = query[3:].strip()
    else:
        cleaned = query.strip()
    
    # Hapus backticks
    cleaned = cleaned.replace('`', '')
    
    # Hapus semicolon dan komentar
    cleaned = re.sub(r';.*$', '', cleaned)
    cleaned = re.sub(r'--.*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    
    # Hapus multiple spaces
    cleaned = ' '.join(cleaned.split())
    
    return cleaned

def validate_column_names(query: str) -> bool:
    """Validasi nama kolom dalam query"""
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
            'bahasa_terakhir_nama_bahasa', 'bahasa_terakhir_kemampuan_bicara', 'bahasa_terakhir_kemampuan_membaca', 'bahasa_terakhir_kemampuan_menulis', 'bahasa_terakhir_keterangan', 'bahasa_terakhir_file_bahasa', 'tanda_jasa_terakhir_nama_tanda_jasa', 'tanda_jasa_terakhir_sumber_data', 'tanda_jasa_terakhir_file_tanda_jasa', 'tanda_jasa_terakhir_nama_pemberi_tanda_jasa', 'tanda_jasa_terakhir_keterangan', 'diklat_terakhir_tanggal_kep', 'diklat_terakhir_file_tanggal_kep', 'diklat_terakhir_is_trigger'

        ],
        'vw_umur_personel': [
            'personelid', 'nama', 'tgllahir', 'umur', 'nrp'
        ],
        'vw_pangkat_tunggal':[
            'nip_tunggal','nama_tunggal', 'nourut', 'nip', 'nama', 'nama_pangkat', 'tmt_pangkat', 'nokep'
        ]
    }
    
    query = query.lower()
    for view, columns in valid_columns.items():
        if view in query:
            cols_in_query = re.findall(r'select\s+(.+?)\s+from', query)[0].split(',')
            cols_in_query = [c.strip() for c in cols_in_query]
            if '*' in cols_in_query:
                return True
            return all(any(col in c for c in cols_in_query) for col in columns)
    return False

def format_error_message(error: Exception) -> str:
    """Format error message for user display."""
    return f"Maaf, terjadi kesalahan dalam memproses permintaan Anda. Detail: {str(error)}"


def init_database() -> SQLDatabase:
  db_uri = f"postgresql://{uid}:{pwd}@{server}:{port}/{db}"
  return SQLDatabase.from_uri(
      db_uri, 
      schema="public",
      view_support=True,
      )

def generate_sql_query(question: str) -> str:
    """Menghasilkan query SQL berdasarkan pertanyaan user"""
    system_prompt = get_detailed_schema() + """
    ATURAN WAJIB:
    1. JANGAN PERNAH menulis kata 'sql' di awal atau di tengah query
    2. Query HARUS dimulai langsung dengan kata SELECT
    3. Ini contoh format yang BENAR:
       SELECT kolom FROM tabel
    4. Ini contoh format yang SALAH:
       sql SELECT kolom FROM tabel
       SQL query: SELECT kolom FROM tabel
    5. nama_pangkat = last_pangkat
    """
    
    llm = ChatOllama(model="llama3.2-vision", temperature=0.1)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Analisis pertanyaan berikut dan buat query SQL yang tepat:
        Pertanyaan: {question}
        
        INGAT:
        - Query HARUS dimulai langsung dengan kata SELECT
        - JANGAN PERNAH menambahkan kata 'sql' di awal query
        - JANGAN gunakan backtick (`)
        - Gunakan nama kolom yang tepat
        
        Hasilkan HANYA query SQL yang valid, tanpa penjelasan tambahan.
        Gunakan nama kolom yang tepat dari skema yang diberikan.""")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    # Generate query pertama
    sql = chain.invoke({"question": question})
    cleaned_sql = clean_sql_query(sql)
    
    # Validasi query
    if not validate_sql_query(sql) or not validate_column_names(sql):
        # Jika validasi gagal, coba generate ulang dengan prompt yang lebih spesifik
        specific_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", f"""Query sebelumnya tidak valid. Buat query baru untuk pertanyaan:
            {question}
            
            PASTIKAN:
            1. Gunakan nama kolom yang tepat dari skema
            2. Gunakan view yang sesuai (vw_personel_analytic, vw_umur_personel, vw_pangkat_tunggal)
            3. Format query yang benar
            
            Hasilkan HANYA query SQL.""")
        ])
        
        chain = specific_prompt | llm | StrOutputParser()
        sql = chain.invoke({"question": question})
        cleaned_sql = clean_sql_query(sql)
        print(f"Original query: {sql}")
        # print(f"Cleaned query: {cleaned_sql}")
    
    return cleaned_sql

def execute_query(db: SQLDatabase, query: str) -> pd.DataFrame:
    """Execute SQL query and return results as DataFrame"""
    try:
        if 'sql' in query.lower().split():
            query = clean_sql_query(query)
        
        # Get the underlying SQLAlchemy engine
        engine = db._engine
        # Execute query and return DataFrame
        return pd.read_sql_query(query, engine)
    except Exception as e:
        st.error(f"Error executing query: {str(e)}")
        return pd.DataFrame()

def get_response(user_query: str, db: SQLDatabase, chat_history: list) -> tuple:
    """Mendapatkan respons untuk pertanyaan user"""
    try:
        # Generate SQL query
        sql_query = generate_sql_query(user_query)  
        print(f"Generated query: {sql_query}")
        
        # Eksekusi query dan dapatkan hasil
        df_results = execute_query(db, sql_query)
        
        # Initialize default values for visualization
        viz_result = {'success': False, 'figure': None}
        viz_description = ""
        
        # Only attempt visualization if we have valid results
        if not df_results.empty:
            viz_result = create_visualization(df_results, user_query)
            viz_description = generate_viz_description(viz_result, df_results)
        
        # Template untuk respons
        template = """
        Berdasarkan pertanyaan dan data yang tersedia:
        {question}

        DATA HASIL QUERY:
        {raw_data}
        
        VISUALISASI:
        {viz_description}
        
        ANALISIS:
        Berdasarkan data di atas, {analysis}
        
        Apakah Anda ingin informasi lebih detail tentang data tertentu?
        """
        
        prompt = ChatPromptTemplate.from_template(template)     
        llm = ChatOllama(model="llama3.2-vision", temperature=0.1)
        
        chain = RunnablePassthrough.assign(
            raw_data=lambda x: df_results.to_string() if not df_results.empty else "No data found",
            viz_description=lambda x: viz_description,
            analysis=lambda x: llm.predict(f"""Berikan analisis dari data berikut:
            Data: {df_results.to_string() if not df_results.empty else 'No data found'}
            Visualization Description: {viz_description}""")
        ) | prompt | llm | StrOutputParser()
        
        response = chain.invoke({
            "question": user_query,
            "query_result": f"Query yang digunakan: {sql_query}",
            "chat_history": chat_history
        })
        
        return response, df_results, viz_result
        
    except Exception as e:
        # Return a tuple with three elements to match the expected return type
        return (f"Maaf, terjadi kesalahan dalam memproses pertanyaan Anda. Detail: {str(e)}", 
                pd.DataFrame(),  # Empty DataFrame
                {'success': False, 'figure': None})  # Default viz_result

def format_query_result(result: str) -> str:
    """Format hasil query agar lebih mudah dibaca"""
    try:
        # Jika hasil adalah string kosong
        if not result:
            return "Tidak ada data yang ditemukan"
            
        # Jika hasil sudah dalam format yang bagus, kembalikan apa adanya
        if isinstance(result, str) and ('\n' in result or '\t' in result):
            return result
            
        # Jika hasil adalah string tapi perlu diformat
        lines = result.split('), (')
        formatted_lines = []
        for line in lines:
            # Bersihkan karakter special
            clean_line = line.replace('(', '').replace(')', '').replace("'", "")
            formatted_lines.append(clean_line)
            
        return '\n'.join(formatted_lines)
        
    except Exception as e:
        return f"Error saat memformat data: {str(e)}\nData asli: {result}"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
      AIMessage(content="Hello! I'm a Data assistant. Ask me a question about your AdventureWorks :bike: personel data."),
    ]

st.set_page_config(page_title="Chat with Postgres", page_icon=":thought_balloon:")

st.title("Chat with Postgres")


for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("User"):
            st.markdown(message.content)

# initialize the db
db = init_database()
st.session_state.db = db
st.success("Connected to database!")

user_query = st.chat_input("Type a question...")
if user_query is not None and user_query.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    
    with st.chat_message("User"):
        st.markdown(user_query)
        
    with st.chat_message("AI"):
        response, df_results, viz_result = get_response(user_query, st.session_state.db, st.session_state.chat_history)
        st.markdown(response)
        
        if df_results is not None and not df_results.empty:
            st.write("Query Results:")
            st.dataframe(df_results)
            
            if viz_result['success']:
                st.write("Data Visualization:")
                st.plotly_chart(viz_result['figure'], use_container_width=True)
            
            df_content = f"\nData Results:\n```\n{df_results.to_string()}\n```"
            full_response = response + df_content
            
    st.session_state.chat_history.append(AIMessage(content=response))