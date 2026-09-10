import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# --------------------------------------------
# KONEKSI KE SUPABASE (PostgreSQL)
#
# CATATAN MIGRASI DARI database_lokal.py (SQLite):
#   - Semua placeholder "?" diganti "%s" (gaya psycopg2/Postgres).
#   - Semua "INSERT OR REPLACE" diganti "INSERT ... ON CONFLICT (pk) DO
#     UPDATE SET ..." (upsert versi Postgres).
#   - kategori_master.rowid (bawaan SQLite) diganti kolom "urutan"
#     (BIGSERIAL) - lihat migration_supabase.sql.
#   - Migrasi otomatis tabel fenomena_lapangan_usaha/fenomena_pengeluaran
#     versi sangat lama SENGAJA tidak dibawa - itu migrasi satu-kali punya
#     database SQLite lama dan tidak relevan lagi untuk Supabase yang fresh.
# --------------------------------------------

@st.cache_resource(show_spinner=False)
def get_engine():
    """Satu SQLAlchemy engine yang dipakai bersama sepanjang hidup app
    (di-cache st.cache_resource, supaya tidak bikin koneksi baru tiap
    kali script Streamlit rerun)."""
    db_url = st.secrets["supabase"]["db_url"]
    # SQLAlchemy butuh driver eksplisit di skema URL-nya.
    url_sqlalchemy = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return create_engine(
        url_sqlalchemy,
        pool_pre_ping=True,   # cek koneksi masih hidup sebelum dipakai (Supabase suka drop koneksi idle)
        pool_size=5,
        max_overflow=5,
    )


def get_connection():
    """Balikin RAW koneksi psycopg2 (bukan objek SQLAlchemy) - dipakai
    fungsi yang butuh cursor.execute()/executemany() langsung, persis
    seperti pola get_connection() versi SQLite dulu."""
    return get_engine().raw_connection()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # --------------------------------------------
    # TABEL 1 & 2: lapangan_usaha & pengeluaran (struktur sama)
    # --------------------------------------------
    for nama_tabel in ["lapangan_usaha", "pengeluaran"]:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {nama_tabel} (
                tahun TEXT,
                triwulan TEXT,
                kode_kategori TEXT,
                jenis_data TEXT,
                jenis_indikator TEXT,
                indikator_pertumbuhan TEXT,
                nilai DOUBLE PRECISION,
                PRIMARY KEY (tahun, triwulan, kode_kategori, jenis_data, jenis_indikator, indikator_pertumbuhan)
            )
        """)

    # --------------------------------------------
    # TABEL 3: pdrb_agregat
    # --------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdrb_agregat (
            tahun TEXT,
            triwulan TEXT,
            jenis_data TEXT,
            indikator_pertumbuhan TEXT,
            nilai DOUBLE PRECISION,
            PRIMARY KEY (tahun, triwulan, jenis_data, indikator_pertumbuhan)
        )
    """)

    # --------------------------------------------
    # TABEL 4: wilayah_kalteng
    # --------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wilayah_kalteng (
            tahun TEXT,
            triwulan TEXT,
            kota TEXT,
            indikator_pertumbuhan TEXT,
            nilai DOUBLE PRECISION,
            PRIMARY KEY (tahun, triwulan, kota, indikator_pertumbuhan)
        )
    """)

    # --------------------------------------------
    # TABEL 5: fenomena
    # --------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fenomena (
            pendekatan TEXT,
            tahun TEXT,
            triwulan TEXT,
            kategori TEXT,
            indikator TEXT,
            teks TEXT,
            PRIMARY KEY (pendekatan, tahun, triwulan, kategori, indikator)
        )
    """)

    # --------------------------------------------
    # TABEL 7: kategori_master
    # (kolom "urutan" BIGSERIAL menggantikan rowid bawaan SQLite)
    # --------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kategori_master (
            urutan BIGSERIAL,
            pendekatan TEXT,
            kode_kategori TEXT,
            nama_kategori TEXT,
            ikon TEXT,
            PRIMARY KEY (pendekatan, kode_kategori)
        )
    """)

    # --------------------------------------------
    # TABEL 8: sumber_data
    # --------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sumber_data (
            jenis_indikator TEXT,
            indikator_pertumbuhan TEXT,
            klasifikasi TEXT,
            jenis_data TEXT,
            link TEXT,
            PRIMARY KEY (jenis_indikator, indikator_pertumbuhan, klasifikasi, jenis_data)
        )
    """)

    # --------------------------------------------
    # ISI DATA AWAL: kategori_master
    # --------------------------------------------
    cursor.execute("SELECT COUNT(*) FROM kategori_master")
    if cursor.fetchone()[0] == 0:
        kategori_lu = [
            ("lapangan_usaha", "A", "Pertanian, Kehutanan, dan Perikanan", "\U0001F33E"),
            ("lapangan_usaha", "B", "Pertambangan dan Penggalian", "\u26CF\uFE0F"),
            ("lapangan_usaha", "C", "Industri Pengolahan", "\U0001F3ED"),
            ("lapangan_usaha", "D", "Pengadaan Listrik dan Gas", "\u26A1"),
            ("lapangan_usaha", "E", "Pengadaan Air, Pengelolaan Sampah, Limbah dan Daur Ulang", "\U0001F4A7"),
            ("lapangan_usaha", "F", "Konstruksi", "\U0001F3D7\uFE0F"),
            ("lapangan_usaha", "G", "Perdagangan Besar dan Eceran; Reparasi Mobil dan Sepeda Motor", "\U0001F91D"),
            ("lapangan_usaha", "H", "Transportasi dan Pergudangan", "\U0001F69A"),
            ("lapangan_usaha", "I", "Penyediaan Akomodasi dan Makan Minum", "\U0001F37D\uFE0F"),
            ("lapangan_usaha", "J", "Informasi dan Komunikasi", "\U0001F4E1"),
            ("lapangan_usaha", "K", "Jasa Keuangan dan Asuransi", "\U0001F4B0"),
            ("lapangan_usaha", "L", "Real Estate", "\U0001F3E2"),
            ("lapangan_usaha", "MN", "Jasa Perusahaan", "\U0001F4BC"),
            ("lapangan_usaha", "O", "Administrasi Pemerintah, Pertahanan dan Jaminan Sosial Wajib", "\U0001F3DB\uFE0F"),
            ("lapangan_usaha", "P", "Jasa Pendidikan", "\U0001F393"),
            ("lapangan_usaha", "Q", "Jasa Kesehatan dan Kegiatan Sosial", "\U0001F3E5"),
            ("lapangan_usaha", "RSTU", "Jasa Lainnya", "\U0001F527"),
        ]
        kategori_pengeluaran = [
            ("pengeluaran", "Pengeluaran Konsumsi Rumah Tangga", "Pengeluaran Konsumsi Rumah Tangga", "\U0001F6D2"),
            ("pengeluaran", "Pengeluaran Konsumsi LNPRT", "Pengeluaran Konsumsi LNPRT", "\U0001F932"),
            ("pengeluaran", "Pengeluaran Konsumsi Pemerintah", "Pengeluaran Konsumsi Pemerintah", "\U0001F3DB\uFE0F"),
            ("pengeluaran", "Pembentukan Modal Tetap Bruto", "Pembentukan Modal Tetap Bruto", "\U0001F3D7\uFE0F"),
            ("pengeluaran", "Perubahan Inventori", "Perubahan Inventori", "\U0001F4E6"),
            ("pengeluaran", "Net Ekspor", "Net Ekspor", "\U0001F6A2"),
            ("pengeluaran", "Lainnya", "Lainnya (LNPRT, Inventori, Net Ekspor)", "\u2795"),
        ]
        cursor.executemany(
            "INSERT INTO kategori_master (pendekatan, kode_kategori, nama_kategori, ikon) VALUES (%s, %s, %s, %s)",
            kategori_lu,
        )
        cursor.executemany(
            "INSERT INTO kategori_master (pendekatan, kode_kategori, nama_kategori, ikon) VALUES (%s, %s, %s, %s)",
            kategori_pengeluaran,
        )

    # --------------------------------------------
    # TABEL 9: periode_tampil
    # --------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS periode_tampil (
            tahun TEXT,
            triwulan TEXT,
            tampil INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (tahun, triwulan)
        )
    """)

    # --------------------------------------------
    # TABEL 10: publikasi_pdrb
    # Link publikasi PDRB per tahun & jenis data (Lapangan Usaha/
    # Pengeluaran). Dipisah dari tabel sumber_data karena butuh logika
    # pencarian sendiri: kalau tahun yang dipilih di filter belum ada
    # publikasinya, ambil publikasi tahun TERDEKAT DI BAWAHNYA (lihat
    # get_link_publikasi).
    # --------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS publikasi_pdrb (
            tahun TEXT,
            jenis_data TEXT,
            link TEXT,
            PRIMARY KEY (tahun, jenis_data)
        )
    """)

    conn.commit()
    conn.close()


# ==============================================
# FUNGSI ATUR TAMPILAN PERIODE (tahun+triwulan mana yang boleh tampil)
# ==============================================

@st.cache_data
def get_periode_yang_ditampilkan():
    """
    Ambil set (tahun, triwulan) yang statusnya tampil=1.
    Balikin None kalau tabel periode_tampil masih benar-benar kosong (admin
    belum pernah isi daftar sama sekali) - supaya fail-safe: TIDAK
    memfilter apa-apa selama pengaturan belum pernah diisi admin.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM periode_tampil")
        total = cursor.fetchone()[0]
        if total == 0:
            return None
        df = pd.read_sql("SELECT tahun, triwulan FROM periode_tampil WHERE tampil=1", conn)
    except Exception:
        return None
    finally:
        conn.close()
    return set(zip(df["tahun"].astype(str), df["triwulan"].astype(str)))


def _hanya_periode_tampil(df):
    """Buang baris yang periodenya (tahun, triwulan) sedang disembunyikan
    admin lewat menu 'Atur Tampilan Periode'."""
    if df.empty or "tahun" not in df.columns or "triwulan" not in df.columns:
        return df
    periode_ok = get_periode_yang_ditampilkan()
    if periode_ok is None:
        return df
    mask = df.apply(lambda r: (str(r["tahun"]), str(r["triwulan"])) in periode_ok, axis=1)
    return df[mask].reset_index(drop=True)


@st.cache_data
def get_urutan_kategori(pendekatan):
    """
    Ambil urutan kode_kategori PERSIS seperti urutan penyimpanannya di
    kategori_master, memakai kolom "urutan" (pengganti rowid SQLite).
    """
    conn = get_connection()
    df = pd.read_sql(
        "SELECT kode_kategori FROM kategori_master WHERE pendekatan=%s ORDER BY urutan",
        conn, params=(pendekatan,)
    )
    conn.close()
    return df["kode_kategori"].tolist()


@st.cache_data
def get_opsi_kolom(nama_tabel, kolom):
    """Ambil daftar nilai unik (non-null) dari satu kolom di suatu tabel."""
    conn = get_connection()
    try:
        df = pd.read_sql(
            f"SELECT DISTINCT {kolom} FROM {nama_tabel} WHERE {kolom} IS NOT NULL",
            conn,
        )
    finally:
        conn.close()
    if df.empty:
        return []
    return sorted(df[kolom].dropna().astype(str).unique().tolist())


def _periode_diizinkan(tahun, triwulan):
    """True kalau periode (tahun, triwulan) boleh tampil (atau kalau
    pengaturan periode_tampil belum pernah disentuh sama sekali - fail-safe)."""
    periode_ok = get_periode_yang_ditampilkan()
    return periode_ok is None or (str(tahun), str(triwulan)) in periode_ok


@st.cache_data
def get_data_kategori(pendekatan, tahun, triwulan, jenis_data=None, jenis_indikator=None, indikator_pertumbuhan=None):
    if not _periode_diizinkan(tahun, triwulan):
        return pd.DataFrame()
    nama_tabel = pendekatan
    conn = get_connection()
    query = f"""
        SELECT d.*, km.nama_kategori, km.ikon
        FROM {nama_tabel} d
        JOIN kategori_master km
            ON d.kode_kategori = km.kode_kategori
            AND km.pendekatan = %s
        WHERE d.tahun=%s AND d.triwulan=%s
    """
    params = [pendekatan, tahun, triwulan]

    if jenis_data:
        query += " AND d.jenis_data=%s"
        params.append(jenis_data)
    if jenis_indikator:
        query += " AND d.jenis_indikator=%s"
        params.append(jenis_indikator)
    if indikator_pertumbuhan:
        query += " AND d.indikator_pertumbuhan=%s"
        params.append(indikator_pertumbuhan)

    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


@st.cache_data
def get_agregat(tahun, triwulan, jenis_data=None, indikator_pertumbuhan=None):
    if not _periode_diizinkan(tahun, triwulan):
        return pd.DataFrame()
    conn = get_connection()
    query = "SELECT * FROM pdrb_agregat WHERE tahun=%s AND triwulan=%s"
    params = [tahun, triwulan]
    if jenis_data:
        query += " AND jenis_data=%s"
        params.append(jenis_data)
    if indikator_pertumbuhan:
        query += " AND indikator_pertumbuhan=%s"
        params.append(indikator_pertumbuhan)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


@st.cache_data
def get_periode_tersedia():
    """
    Ambil daftar (tahun, triwulan) yang datanya SUDAH ADA di pdrb_agregat
    DAN sedang diatur admin untuk tampil.
    """
    conn = get_connection()
    df = pd.read_sql("SELECT DISTINCT tahun, triwulan FROM pdrb_agregat", conn)
    conn.close()
    if df.empty:
        return df
    df = _hanya_periode_tampil(df)
    if df.empty:
        return df
    urutan_triwulan = {"I": 1, "II": 2, "III": 3, "IV": 4}
    df["_urutan"] = df["triwulan"].map(urutan_triwulan)
    df = df.sort_values(["tahun", "_urutan"]).drop(columns="_urutan").reset_index(drop=True)
    return df


@st.cache_data
def get_wilayah(tahun, triwulan, indikator_pertumbuhan="yoy"):
    if not _periode_diizinkan(tahun, triwulan):
        return pd.DataFrame()
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM wilayah_kalteng WHERE tahun=%s AND triwulan=%s AND indikator_pertumbuhan=%s",
        conn, params=(tahun, triwulan, indikator_pertumbuhan)
    )
    conn.close()
    return df


@st.cache_data
def get_fenomena(pendekatan, tahun, triwulan, kategori, indikator):
    """Balikin teks narasi fenomena, atau None kalau datanya belum ada/kosong/"nan"."""
    if not _periode_diizinkan(tahun, triwulan):
        return None
    conn = get_connection()
    df = pd.read_sql(
        """SELECT teks FROM fenomena
           WHERE pendekatan=%s AND tahun=%s AND triwulan=%s AND kategori=%s AND indikator=%s""",
        conn, params=(pendekatan, tahun, triwulan, kategori, indikator)
    )
    conn.close()
    if df.empty:
        return None
    teks = str(df["teks"].values[0]).strip()
    if teks == "" or teks.lower() in ("nan", "none"):
        return None
    return teks


@st.cache_data
def get_semua_fenomena(pendekatan, tahun, triwulan):
    """
    Balikin SEMUA baris fenomena untuk satu (pendekatan, tahun, triwulan),
    apapun isi kategori & indikator-nya.

    Dipakai karena "sumbu" pembeda fenomena ternyata beda-beda tergantung
    pendekatan: untuk lapangan_usaha biasanya dibedakan per indikator
    (qtq/yoy), tapi untuk pengeluaran (atau kombinasi lain) bisa saja
    dibedakan lewat kategori (mis. nama kategori tertentu, bukan "-"/"UMUM").
    Jadi judul tiap kartu di app.py ditentukan belakangan: pakai kategori
    kalau itu bukan placeholder umum ("UMUM"/"-"/nama pendekatan sendiri),
    kalau tidak baru fallback ke indikator (qtq/yoy/ctc).

    Balikin DataFrame kolom: kategori, indikator, teks
    (baris dengan teks kosong/"nan"/"none" sudah dibuang).
    """
    if not _periode_diizinkan(tahun, triwulan):
        return pd.DataFrame(columns=["kategori", "indikator", "teks"])
    conn = get_connection()
    df = pd.read_sql(
        """SELECT kategori, indikator, teks FROM fenomena
           WHERE pendekatan=%s AND tahun=%s AND triwulan=%s
           ORDER BY kategori, indikator""",
        conn, params=(pendekatan, tahun, triwulan)
    )
    conn.close()
    if df.empty:
        return df
    df["teks"] = df["teks"].astype(str).str.strip()
    df = df[~df["teks"].str.lower().isin(["", "nan", "none"])]
    return df.reset_index(drop=True)


# ==============================================
# FUNGSI UPLOAD EXCEL - sesuai format sheet 'Lapangan Usaha' / 'Pengeluaran'
# ==============================================

def upload_kategori_dari_sheet(df_sheet, pendekatan):
    """
    df_sheet: hasil pd.read_excel() dari sheet 'Lapangan Usaha' atau 'Pengeluaran'
    Format kolom: Tahun, Triwulan, Jenis Data, Jenis Indikator, Indikator Pertumbuhan, <kategori...>, PDRB
    """
    nama_tabel = pendekatan

    df_sheet = df_sheet[pd.to_numeric(df_sheet["Tahun"], errors="coerce").notna()].copy()

    kolom_bukan_kategori = ["Tahun", "Triwulan", "Jenis Data", "Jenis Indikator", "Indikator Pertumbuhan "]
    kolom_kategori = [k for k in df_sheet.columns if k not in kolom_bukan_kategori + ["PDRB"] and "Unnamed" not in str(k)]

    # --- Bagian 1: data per kategori (A, B, C, ... / Konsumsi RT, dst) ---
    df_kategori = df_sheet.melt(
        id_vars=kolom_bukan_kategori,
        value_vars=kolom_kategori,
        var_name="kode_kategori",
        value_name="nilai"
    )
    df_kategori["tahun"] = df_kategori["Tahun"].astype(int).astype(str)
    df_kategori["triwulan"] = df_kategori["Triwulan"].astype(str).str.strip()
    df_kategori["jenis_data"] = df_kategori["Jenis Data"].astype(str).str.strip().str.lower()
    df_kategori["jenis_indikator"] = df_kategori["Jenis Indikator"].astype(str).str.strip().str.replace(" ", "_")
    df_kategori["indikator_pertumbuhan"] = df_kategori["Indikator Pertumbuhan "].astype(str).str.strip()
    df_kategori["nilai"] = pd.to_numeric(df_kategori["nilai"], errors="coerce")
    df_kategori = df_kategori.dropna(subset=["nilai"])

    df_final = df_kategori[["tahun", "triwulan", "kode_kategori", "jenis_data",
                              "jenis_indikator", "indikator_pertumbuhan", "nilai"]]

    conn = get_connection()
    cursor = conn.cursor()
    # UPSERT (pengganti INSERT OR REPLACE SQLite) - biar file yang sama bisa
    # diupload ulang tanpa error duplikat primary key.
    cursor.executemany(
        f"""INSERT INTO {nama_tabel}
                (tahun, triwulan, kode_kategori, jenis_data, jenis_indikator, indikator_pertumbuhan, nilai)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tahun, triwulan, kode_kategori, jenis_data, jenis_indikator, indikator_pertumbuhan)
            DO UPDATE SET nilai = EXCLUDED.nilai""",
        df_final.itertuples(index=False, name=None)
    )
    conn.commit()

    # --- Bagian 2: kolom PDRB (agregat total) ---
    jenis_indikator_valid = df_sheet["Jenis Indikator"].astype(str).str.strip().isin(["-", "laju pertumbuhan"])
    df_agregat = df_sheet[jenis_indikator_valid][kolom_bukan_kategori + ["PDRB"]].copy()
    df_agregat["tahun"] = df_agregat["Tahun"].astype(int).astype(str)
    df_agregat["triwulan"] = df_agregat["Triwulan"].astype(str).str.strip()
    df_agregat["jenis_data"] = df_agregat["Jenis Data"].astype(str).str.strip().str.lower()
    df_agregat["indikator_pertumbuhan"] = df_agregat["Indikator Pertumbuhan "].astype(str).str.strip()
    df_agregat["nilai"] = pd.to_numeric(df_agregat["PDRB"], errors="coerce")
    df_agregat = df_agregat.dropna(subset=["nilai"])
    df_agregat_final = df_agregat[["tahun", "triwulan", "jenis_data", "indikator_pertumbuhan", "nilai"]]

    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO pdrb_agregat (tahun, triwulan, jenis_data, indikator_pertumbuhan, nilai)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (tahun, triwulan, jenis_data, indikator_pertumbuhan)
           DO UPDATE SET nilai = EXCLUDED.nilai""",
        df_agregat_final.itertuples(index=False, name=None)
    )
    conn.commit()
    conn.close()

    return len(df_final), len(df_agregat_final)


def upload_wilayah_dari_sheet(df_sheet):
    """
    df_sheet: hasil pd.read_excel() dari sheet 'Laju Kalteng'
    Format kolom: Tahun, Triwulan, Indikator Pertumbuhan, <nama kota...>
    """
    df_sheet = df_sheet[pd.to_numeric(df_sheet["Tahun"], errors="coerce").notna()].copy()

    kolom_bukan_kota = ["Tahun", "Triwulan", "Indikator Pertumbuhan "]
    kolom_kota = [k for k in df_sheet.columns if k not in kolom_bukan_kota and "Unnamed" not in str(k)]

    df_panjang = df_sheet.melt(
        id_vars=kolom_bukan_kota,
        value_vars=kolom_kota,
        var_name="kota",
        value_name="nilai"
    )
    df_panjang["tahun"] = df_panjang["Tahun"].astype(int).astype(str)
    df_panjang["triwulan"] = df_panjang["Triwulan"].astype(str).str.strip()
    df_panjang["indikator_pertumbuhan"] = df_panjang["Indikator Pertumbuhan "].astype(str).str.strip()
    df_panjang["nilai"] = pd.to_numeric(df_panjang["nilai"], errors="coerce")
    df_panjang = df_panjang.dropna(subset=["nilai"])

    df_final = df_panjang[["tahun", "triwulan", "kota", "indikator_pertumbuhan", "nilai"]]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO wilayah_kalteng (tahun, triwulan, kota, indikator_pertumbuhan, nilai)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (tahun, triwulan, kota, indikator_pertumbuhan)
           DO UPDATE SET nilai = EXCLUDED.nilai""",
        df_final.itertuples(index=False, name=None)
    )
    conn.commit()
    conn.close()

    return len(df_final)


def upload_laju_kota_dari_sheet(df_sheet, jenis_data="adhk"):
    """
    df_sheet: hasil pd.read_excel() dari sheet 'Laju Palangka'
    Format kolom: Tahun, Triwulan, Indikator Pertumbuhan, Nilai
    """
    df = df_sheet.copy()
    df.columns = [str(k).strip() for k in df.columns]

    df = df[pd.to_numeric(df["Tahun"], errors="coerce").notna()].copy()
    df["Triwulan"] = df["Triwulan"].astype(str).str.strip()
    df = df[df["Triwulan"].isin(["I", "II", "III", "IV"])]

    df["tahun"] = df["Tahun"].astype(int).astype(str)
    df["triwulan"] = df["Triwulan"]
    df["indikator_pertumbuhan"] = df["Indikator Pertumbuhan"].astype(str).str.strip()
    df["nilai"] = pd.to_numeric(df["Nilai"], errors="coerce")
    df = df.dropna(subset=["nilai"])
    df["jenis_data"] = jenis_data

    df_final = df[["tahun", "triwulan", "jenis_data", "indikator_pertumbuhan", "nilai"]]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO pdrb_agregat (tahun, triwulan, jenis_data, indikator_pertumbuhan, nilai)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (tahun, triwulan, jenis_data, indikator_pertumbuhan)
           DO UPDATE SET nilai = EXCLUDED.nilai""",
        df_final.itertuples(index=False, name=None)
    )
    conn.commit()
    conn.close()
    return len(df_final)


def upload_sumber_data_dari_sheet(df_sheet):
    """
    df_sheet: hasil pd.read_excel() dari sheet 'Sumber Data'
    Format kolom: Jenis Indikator, Indikator Pertumbuhan, Klasifikasi, Jenis Data, Link
    """
    df = df_sheet.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={
        "Jenis Indikator": "jenis_indikator",
        "Indikator Pertumbuhan": "indikator_pertumbuhan",
        "Klasifikasi": "klasifikasi",
        "Jenis Data": "jenis_data",
        "Link": "link",
    })

    kolom_wajib = ["jenis_indikator", "indikator_pertumbuhan", "klasifikasi", "jenis_data", "link"]
    df = df[[k for k in kolom_wajib if k in df.columns]].copy()
    df = df.dropna(how="all")

    for k in kolom_wajib:
        if k in df.columns:
            df[k] = df[k].astype(str).str.strip()

    if "jenis_data" in df.columns:
        df["jenis_data"] = df["jenis_data"].str.lower()
    if "klasifikasi" in df.columns:
        df["klasifikasi"] = df["klasifikasi"].str.replace(" ", "_")

    df = df.dropna(subset=["jenis_indikator"])
    df = df[df["jenis_indikator"] != ""]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO sumber_data
               (jenis_indikator, indikator_pertumbuhan, klasifikasi, jenis_data, link)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (jenis_indikator, indikator_pertumbuhan, klasifikasi, jenis_data)
           DO UPDATE SET link = EXCLUDED.link""",
        df[kolom_wajib].itertuples(index=False, name=None)
    )
    conn.commit()
    conn.close()
    return len(df)


def upload_fenomena_dari_sheet(df_sheet):
    """
    df_sheet: hasil pd.read_excel() dari sheet 'Fenomena'
    Format kolom (long/1 baris = 1 kartu): Jenis Klasifikasi, Tahun, Triwulan,
    Kategori, Indikator, Teks

    - Kategori : nama kategori/topik kalau fenomena ini dibedakan per kategori
                 (mis. "Konsumsi Rumah Tangga"). Kosongkan / isi "-" kalau
                 fenomena ini dibedakan lewat kolom Indikator, bukan kategori.
    - Indikator: "qtq" / "yoy" / "ctc" kalau fenomena ini dibedakan per
                 indikator pertumbuhan. Kosongkan / isi "-" kalau dibedakan
                 lewat Kategori.
    - Teks     : narasi lengkapnya (wajib diisi, baris dengan Teks kosong
                 otomatis dilewati).

    Minimal salah SATU dari Kategori/Indikator berisi nilai yang bermakna
    per baris, supaya render_fenomena() di app.py tau mana yang dipakai jadi
    judul kartu.
    """
    df = df_sheet.copy()
    df.columns = [str(c).strip() for c in df.columns]

    df = df[pd.to_numeric(df["Tahun"], errors="coerce").notna()].copy()
    df["tahun"] = df["Tahun"].astype(int).astype(str)
    df["triwulan"] = df["Triwulan"].astype(str).str.strip()

    peta_pendekatan = {"lapangan usaha": "lapangan_usaha", "pengeluaran": "pengeluaran"}
    df["pendekatan"] = df["Jenis Klasifikasi"].astype(str).str.strip().str.lower().map(peta_pendekatan)
    df = df.dropna(subset=["pendekatan"])

    def bersihkan_kolom(nama_kolom, nilai_default):
        if nama_kolom in df.columns:
            hasil = df[nama_kolom].astype(str).str.strip()
            return hasil.replace({"": nilai_default, "nan": nilai_default, "None": nilai_default})
        return pd.Series(nilai_default, index=df.index)

    df["kategori"] = bersihkan_kolom("Kategori", "UMUM")
    df["indikator"] = bersihkan_kolom("Indikator", "-").str.lower()
    df["teks"] = bersihkan_kolom("Teks", "")

    df = df[(df["teks"] != "") & (df["teks"].str.lower() != "nan") & (df["teks"] != "None")]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO fenomena
               (pendekatan, tahun, triwulan, kategori, indikator, teks)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (pendekatan, tahun, triwulan, kategori, indikator)
           DO UPDATE SET teks = EXCLUDED.teks""",
        df[["pendekatan", "tahun", "triwulan", "kategori", "indikator", "teks"]]
            .itertuples(index=False, name=None)
    )
    conn.commit()
    conn.close()
    return len(df)


@st.cache_data
def get_tren(indikator_pertumbuhan="yoy", tahun=None, triwulan=None, jumlah_periode=9):
    """
    Ambil histori laju pertumbuhan sepanjang jendela bergulir (rolling window)
    sebanyak `jumlah_periode` triwulan (default 9 = 3 tahun), BERAKHIR di
    periode (tahun, triwulan) yang dipilih di dashboard.
    """
    conn = get_connection()
    df = pd.read_sql(
        """SELECT tahun, triwulan, nilai FROM pdrb_agregat
           WHERE jenis_data='adhk' AND indikator_pertumbuhan=%s""",
        conn, params=(indikator_pertumbuhan,)
    )
    conn.close()

    if df.empty:
        return df

    urutan_triwulan = {"I": 1, "II": 2, "III": 3, "IV": 4}
    df["urutan"] = df["triwulan"].map(urutan_triwulan)
    df = df.sort_values(["tahun", "urutan"]).drop(columns="urutan").reset_index(drop=True)
    df["label"] = "Tw " + df["triwulan"] + " " + df["tahun"]

    if tahun is None or triwulan is None:
        return df

    cocok = df.index[(df["tahun"] == str(tahun)) & (df["triwulan"] == str(triwulan))]
    if len(cocok) > 0:
        idx_akhir = cocok[0]
    else:
        idx_akhir = len(df) - 1

    idx_awal = max(0, idx_akhir - jumlah_periode + 1)
    return df.iloc[idx_awal:idx_akhir + 1].reset_index(drop=True)


@st.cache_data
def get_tabel_lengkap(pendekatan, tahun=None, triwulan=None, jenis_data=None, indikator_pertumbuhan=None):
    """Ambil data lapangan_usaha/pengeluaran, balikin ke format lebar (kayak Excel asli)"""
    nama_tabel = pendekatan
    conn = get_connection()

    query = f"SELECT * FROM {nama_tabel}"
    kondisi = []
    params = []
    if tahun:
        kondisi.append("tahun=%s")
        params.append(tahun)
    if triwulan:
        kondisi.append("triwulan=%s")
        params.append(triwulan)
    if jenis_data:
        kondisi.append("jenis_data=%s")
        params.append(jenis_data)
    if indikator_pertumbuhan:
        kondisi.append("indikator_pertumbuhan=%s")
        params.append(indikator_pertumbuhan)
    if kondisi:
        query += " WHERE " + " AND ".join(kondisi)

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    if df.empty:
        return df

    df["jenis_gabungan"] = df["jenis_data"] + " - " + df["jenis_indikator"] + " - " + df["indikator_pertumbuhan"]

    df_lebar = df.pivot_table(
        index=["tahun", "triwulan", "jenis_gabungan"],
        columns="kode_kategori",
        values="nilai"
    ).reset_index()

    return df_lebar


@st.cache_data
def get_tabel_wilayah(tahun=None, triwulan=None, indikator_pertumbuhan=None):
    """Ambil data wilayah_kalteng, balikin ke format lebar."""
    conn = get_connection()
    query = "SELECT * FROM wilayah_kalteng"
    kondisi = []
    params = []
    if tahun:
        kondisi.append("tahun=%s")
        params.append(tahun)
    if triwulan:
        kondisi.append("triwulan=%s")
        params.append(triwulan)
    if indikator_pertumbuhan:
        kondisi.append("indikator_pertumbuhan=%s")
        params.append(indikator_pertumbuhan)
    if kondisi:
        query += " WHERE " + " AND ".join(kondisi)

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    if df.empty:
        return df

    df_lebar = df.pivot_table(
        index=["tahun", "triwulan", "indikator_pertumbuhan"],
        columns="kota",
        values="nilai"
    ).reset_index()

    return df_lebar


@st.cache_data
def get_tabel_agregat(tahun=None, triwulan=None, jenis_data=None, indikator_pertumbuhan=None):
    """Ambil data pdrb_agregat sesuai filter."""
    conn = get_connection()
    query = "SELECT * FROM pdrb_agregat"
    kondisi = []
    params = []
    if tahun:
        kondisi.append("tahun=%s")
        params.append(tahun)
    if triwulan:
        kondisi.append("triwulan=%s")
        params.append(triwulan)
    if jenis_data:
        kondisi.append("jenis_data=%s")
        params.append(jenis_data)
    if indikator_pertumbuhan:
        kondisi.append("indikator_pertumbuhan=%s")
        params.append(indikator_pertumbuhan)
    if kondisi:
        query += " WHERE " + " AND ".join(kondisi)

    urutan_triwulan = {"I": 1, "II": 2, "III": 3, "IV": 4}
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    if df.empty:
        return df
    df["_urutan"] = df["triwulan"].map(urutan_triwulan)
    df = df.sort_values(["tahun", "_urutan", "jenis_data", "indikator_pertumbuhan"]).drop(columns="_urutan").reset_index(drop=True)
    return df


@st.cache_data
def get_link_sumber(jenis_indikator, klasifikasi="-", jenis_data="-", indikator_pertumbuhan="-"):
    """
    Ambil SATU link sumber data yang cocok dengan kombinasi filter sebuah
    grafik/tabel di dashboard.
    """
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT link FROM sumber_data
        WHERE TRIM(LOWER(jenis_indikator)) = TRIM(LOWER(%s))
          AND TRIM(LOWER(klasifikasi)) = TRIM(LOWER(%s))
          AND TRIM(LOWER(jenis_data)) = TRIM(LOWER(%s))
          AND TRIM(LOWER(indikator_pertumbuhan)) = TRIM(LOWER(%s))
        LIMIT 1
        """,
        conn, params=(jenis_indikator, klasifikasi, jenis_data, indikator_pertumbuhan)
    )
    conn.close()
    if df.empty:
        return None
    return df.iloc[0]["link"]


@st.cache_data
def get_link_publikasi(tahun, jenis_data):
    """
    Ambil link publikasi PDRB untuk kartu "Publikasi PDRB", dengan aturan:
      - jenis_data harus SAMA (case-insensitive) dengan pilihan filter
        "Jenis Data" (Lapangan Usaha / Pengeluaran) - tidak nyasar ke
        jenis_data lain.
      - hanya boleh tahun publikasi <= tahun yang dipilih di filter
        (tidak menampilkan publikasi dari tahun yang lebih baru/"masa
        depan" dibanding data yang sedang dilihat).
      - dari yang memenuhi dua syarat di atas, ambil tahun PALING BESAR
        (paling dekat/terbaru).
    Balikin None kalau tidak ada satupun tahun yang cocok - dashboard
    lalu menampilkan status "belum tersedia", TANPA mencari jenis_data
    lain sebagai pengganti.
    """
    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT tahun, link FROM publikasi_pdrb
        WHERE TRIM(LOWER(jenis_data)) = TRIM(LOWER(%s))
          AND tahun::INTEGER <= %s::INTEGER
        ORDER BY tahun::INTEGER DESC
        LIMIT 1
        """,
        conn, params=(jenis_data, tahun)
    )
    conn.close()
    if df.empty:
        return None
    return df.iloc[0]["link"]


@st.cache_data
def get_tabel_publikasi(jenis_data=None):
    """Ambil seluruh data publikasi_pdrb sesuai filter (dipakai halaman Admin)."""
    conn = get_connection()
    query = "SELECT * FROM publikasi_pdrb"
    params = []
    if jenis_data:
        query += " WHERE TRIM(LOWER(jenis_data)) = TRIM(LOWER(%s))"
        params.append(jenis_data)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    if df.empty:
        return df
    return df.sort_values(["jenis_data", "tahun"]).reset_index(drop=True)


def upload_publikasi_dari_sheet(df_sheet):
    """
    df_sheet: hasil pd.read_excel() dari sheet berisi daftar publikasi PDRB.
    Format kolom: Tahun, Jenis Data, Link
    """
    df = df_sheet.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={
        "Tahun": "tahun",
        "Jenis Data": "jenis_data",
        "Link": "link",
    })

    kolom_wajib = ["tahun", "jenis_data", "link"]
    df = df[[k for k in kolom_wajib if k in df.columns]].copy()
    df = df.dropna(how="all")

    for k in kolom_wajib:
        if k in df.columns:
            df[k] = df[k].astype(str).str.strip()

    df = df.dropna(subset=["tahun", "jenis_data"])
    df = df[(df["tahun"] != "") & (df["jenis_data"] != "")]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO publikasi_pdrb
               (tahun, jenis_data, link)
           VALUES (%s, %s, %s)
           ON CONFLICT (tahun, jenis_data)
           DO UPDATE SET link = EXCLUDED.link""",
        df[kolom_wajib].itertuples(index=False, name=None)
    )
    conn.commit()
    conn.close()
    return len(df)


@st.cache_data
def get_tabel_sumber_data(jenis_data=None, indikator_pertumbuhan=None):
    """Ambil data sumber_data sesuai filter."""
    conn = get_connection()
    query = "SELECT * FROM sumber_data"
    kondisi = []
    params = []
    if jenis_data:
        kondisi.append("jenis_data=%s")
        params.append(jenis_data)
    if indikator_pertumbuhan:
        kondisi.append("indikator_pertumbuhan=%s")
        params.append(indikator_pertumbuhan)
    if kondisi:
        query += " WHERE " + " AND ".join(kondisi)

    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df