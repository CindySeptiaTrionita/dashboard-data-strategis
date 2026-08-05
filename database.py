# ==========================================
# DATABASE.PY - "Petugas Lemari Arsip"
# File ini isinya fungsi buat simpan & ambil data dari database
# ==========================================

import sqlite3
import pandas as pd

NAMA_FILE_DB = "data_pdrb.db"

def get_connection():
    # Ini kayak "buka pintu lemari arsip"
    return sqlite3.connect(NAMA_FILE_DB, check_same_thread=False)

def init_db():
    """Bikin 'rak' di lemari kalau belum ada, terus isi data awal"""
    conn = get_connection()
    cursor = conn.cursor()

    # Bikin tabel (rak) kalau belum ada
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lapangan_usaha (
            kategori TEXT PRIMARY KEY,
            pertumbuhan REAL,
            fenomena TEXT
        )
    """)

    # Cek dulu, kalau rak-nya masih kosong, isi data awal
    cursor.execute("SELECT COUNT(*) FROM lapangan_usaha")
    jumlah_data = cursor.fetchone()[0]

    if jumlah_data == 0:
        data_awal = [
            ("Administrasi Pemerintahan", 11.33,
             "Pertumbuhan tertinggi didorong oleh realisasi belanja pemerintah "
             "daerah yang meningkat pada Triwulan I 2026."),
            ("Konstruksi", 8.15,
             "Sektor konstruksi tumbuh signifikan seiring berlanjutnya "
             "pembangunan infrastruktur dan proyek properti."),
            ("Jasa Keuangan", 8.08,
             "Peningkatan didorong oleh pertumbuhan penyaluran kredit "
             "perbankan dan aktivitas jasa keuangan lainnya."),
            ("Transportasi dan Pergudangan", 7.09,
             "Mobilitas masyarakat dan aktivitas logistik yang meningkat "
             "mendorong pertumbuhan sektor ini."),
            ("Perdagangan dan Reparasi", 4.19,
             "Aktivitas perdagangan tumbuh moderat, sejalan dengan daya beli "
             "masyarakat yang relatif stabil."),
            ("Lainnya", 2.75,
             "Sektor-sektor lain tumbuh secara moderat dan cenderung stabil."),
        ]
        cursor.executemany(
            "INSERT INTO lapangan_usaha VALUES (?, ?, ?)", data_awal
        )

    conn.commit()
    conn.close()

def get_all_data():
    """Ambil SEMUA data dari lemari, bentuknya tabel (DataFrame)"""
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM lapangan_usaha", conn)
    conn.close()
    return df

def update_data(kategori, pertumbuhan_baru, fenomena_baru):
    """Ubah data yang SUDAH ADA di lemari"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE lapangan_usaha SET pertumbuhan = ?, fenomena = ? WHERE kategori = ?",
        (pertumbuhan_baru, fenomena_baru, kategori)
    )
    conn.commit()
    conn.close()

def tambah_kategori_baru(kategori, pertumbuhan, fenomena):
    """Nambah kategori BARU ke lemari"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO lapangan_usaha VALUES (?, ?, ?)",
        (kategori, pertumbuhan, fenomena)
    )
    conn.commit()
    conn.close()

def hapus_kategori(kategori):
    """Hapus 1 kategori dari lemari"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lapangan_usaha WHERE kategori = ?", (kategori,))
    conn.commit()
    conn.close()