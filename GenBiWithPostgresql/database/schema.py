from typing import List, Dict, Optional
from dataclasses import dataclass
import psycopg2

@dataclass
class ColumnMetadata:
    name: str
    type: str
    nullable: bool
    description: str = ""

@dataclass
class TableMetadata:
    name: str
    columns: List[ColumnMetadata]
    primary_keys: List[str]
    foreign_keys: List[Dict]
    description: str = ""

class SchemaManager:
    def __init__(self, connection):
        self.conn = connection
        self.tables_metadata = {}
        self.relationships = []
        
        # Descriptions for tables and columns
        self._init_descriptions()
        
        # Extract metadata
        self.extract_table_metadata()
        self.build_relationships()
    
    def _init_descriptions(self):
        self.table_descriptions = {
            "master_pejabat": "Tabel yang menyimpan informasi pejabat beserta jabatan dan pangkatnya",
            "personel": "Tabel utama yang menyimpan data personel/pegawai",
            "riwayat_pendidikan": "Tabel yang menyimpan riwayat pendidikan personel",
            "pendidikan": "Tabel referensi jenis dan tingkat pendidikan"
        }
        
        self.column_descriptions = {
            'master_pejabat': {
                'personel_id': 'ID referensi ke tabel personel',
                'nama_pejabat': 'Nama lengkap pejabat',
                'nrp_pejabat': 'Nomor Registrasi Pusat pejabat',
                'pangkat_pejabat': 'Pangkat pejabat',
                'jabatan_pejabat': 'Jabatan pejabat',
                'tmt_pangkat_pejabat': 'Terhitung Mulai Tanggal pangkat pejabat',
                'tmt_jabatan_pejabat': 'Terhitung Mulai Tanggal jabatan pejabat',
            },
            'personel': {
                'personelid': 'ID unik personel',
                'nama': 'Nama lengkap personel',
                'nrp': 'Nomor Registrasi Pusat',
                'pangkat': 'Pangkat personel',
                'jabatan': 'Jabatan personel',
                'satker': 'Satuan kerja',
            },
            'riwayat_pendidikan': {
                'personel_id': 'ID referensi ke tabel personel',
                'pendidikanid': 'ID referensi ke tabel pendidikan',
                'nama_pendidikan': 'Nama pendidikan',
                'jurusan': 'Nama jurusan',
                'tahun_lulus': 'Tahun kelulusan',
                'ipk': 'Indeks Prestasi Kumulatif',
            },
            'pendidikan': {
                'pendidikanid': 'ID unik pendidikan',
                'pendidikan': 'Nama jenis/tingkat pendidikan',
                'tingkat_pendidikan_id': 'ID tingkat pendidikan',
                'tingkat_pendidikan_nama': 'Nama tingkat pendidikan',
                'pangkatmin': 'Pangkat minimum',
                'pangkatmax': 'Pangkat maximum',
            }

        }

    def extract_table_metadata(self):
        cur = self.conn.cursor()
        
        for table_name in self.table_descriptions.keys():
            # Get columns
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
            """, (table_name,))
            columns = cur.fetchall()
            
            # Get primary keys
            cur.execute("""
                SELECT ccu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name)
                WHERE constraint_type = 'PRIMARY KEY' AND tc.table_name = %s
            """, (table_name,))
            primary_keys = [row[0] for row in cur.fetchall()]
            
            # Get foreign keys
            cur.execute("""
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
                WHERE constraint_type = 'FOREIGN KEY' AND tc.table_name = %s
            """, (table_name,))
            foreign_keys = cur.fetchall()
            
            self.tables_metadata[table_name] = TableMetadata(
                name=table_name,
                columns=[ColumnMetadata(
                    name=col[0],
                    type=col[1],
                    nullable=col[2] == 'YES',
                    description=self.column_descriptions.get(table_name, {}).get(col[0], "")
                ) for col in columns],
                primary_keys=primary_keys,
                foreign_keys=[{
                    'column': fk[0],
                    'foreign_table': fk[1],
                    'foreign_column': fk[2]
                } for fk in foreign_keys],
                description=self.table_descriptions.get(table_name, "")
            )

    def build_relationships(self):
        self.relationships = [
            {
                'source_table': 'master_pejabat',
                'source_columns': ['pejabat_id'],
                'target_table': 'personel',
                'target_columns': ['personelid'],
                'relationship_type': 'many_to_one',
            },
            {
                'source_table': 'riwayat_pendidikan',
                'source_columns': ['rowid'],
                'target_table': 'personel',
                'target_columns': ['personelid'],
                'relationship_type': 'many_to_one',
            },
            {
                'source_table': 'riwayat_pendidikan',
                'source_columns': ['rowid'],
                'target_table': 'pendidikan',
                'target_columns': ['pendidikanid'],
                'relationship_type': 'many_to_one',
            }

        ]

    def get_table_schema_text(self) -> str:
        schema_text = "Database Schema:\n\n"
        
        for table_name, metadata in self.tables_metadata.items():
            schema_text += f"Table: {table_name}\n"
            if metadata.description:
                schema_text += f"Description: {metadata.description}\n"
            
            schema_text += "Columns:\n"
            for column in metadata.columns:
                nullable = "NULL" if column.nullable else "NOT NULL"
                desc = f" - {column.description}" if column.description else ""
                schema_text += f"- {column.name} ({column.type}) {nullable}{desc}\n"
            
            schema_text += "\n"
        
        if self.relationships:
            schema_text += "Relationships:\n"
            for rel in self.relationships:
                schema_text += f"- {rel['source_table']}.{','.join(rel['source_columns'])} -> "
                schema_text += f"{rel['target_table']}.{','.join(rel['target_columns'])}\n"
        
        return schema_text