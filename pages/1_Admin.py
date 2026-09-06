import io
import streamlit as st
import pandas as pd
from utils.styling import apply_custom_css
from database import (
    init_db,
    get_connection,
    get_opsi_kolom,
    get_urutan_kategori,
    upload_kategori_dari_sheet,
    upload_wilayah_dari_sheet,
    upload_laju_kota_dari_sheet,
    upload_sumber_data_dari_sheet,
    upload_fenomena_dari_sheet,
)

# --------------------------------------------
# KONFIGURASI
# --------------------------------------------
# Primary key ASLI tiap tabel di Postgres/Supabase (lihat migration_supabase.sql).
# Dipakai sebagai identitas baris di editor (pengganti "rowid" bawaan SQLite,
# yang tidak ada di Postgres) - lihat PRIMARY_KEYS di bawah dan pemakaiannya
# di simpan_perubahan().
PRIMARY_KEYS = {
    "lapangan_usaha": ["tahun", "triwulan", "kode_kategori", "jenis_data", "jenis_indikator", "indikator_pertumbuhan"],
    "pengeluaran": ["tahun", "triwulan", "kode_kategori", "jenis_data", "jenis_indikator", "indikator_pertumbuhan"],
    "pdrb_agregat": ["tahun", "triwulan", "jenis_data", "indikator_pertumbuhan"],
    "wilayah_kalteng": ["tahun", "triwulan", "kota", "indikator_pertumbuhan"],
    "fenomena": ["pendekatan", "tahun", "triwulan", "kategori", "indikator"],
    "kategori_master": ["pendekatan", "kode_kategori"],
    "sumber_data": ["jenis_indikator", "indikator_pertumbuhan", "klasifikasi", "jenis_data"],
    "periode_tampil": ["tahun", "triwulan"],
}

# Pastikan semua tabel (termasuk yang baru: periode_tampil, fenomena) sudah
# ada begitu halaman Admin dibuka, TANPA bergantung urutan buka app.py dulu.
# init_db() aman dipanggil berkali-kali (CREATE TABLE IF NOT EXISTS) dan
# otomatis migrasi data lama kalau ada peninggalan struktur tabel versi
# sebelumnya (mis. fenomena_lapangan_usaha/fenomena_pengeluaran -> fenomena).
init_db()

# CATATAN KEAMANAN: ini password sederhana untuk kebutuhan internal.
# Untuk penggunaan yang lebih serius, pindahkan ke st.secrets, contoh:
#   ADMIN_PASSWORD = st.secrets["admin_password"]
# lalu isi file .streamlit/secrets.toml dengan: admin_password = "..."
ADMIN_PASSWORD = "admin123"

st.set_page_config(page_title="Admin - Dashboard PDRB", layout="wide")
apply_custom_css()

# Override CSS tema global khusus halaman ini.
# styling.py membuat SEMUA tombol jadi bulat 40x40px (untuk tombol pagination
# di halaman utama), yang bikin teks tombol di halaman admin ("Keluar",
# "Simpan Perubahan") pecah huruf per huruf karena dipaksa muat di lingkaran
# kecil. Halaman admin tidak punya tombol pagination, jadi aman dikembalikan
# ke bentuk normal di sini saja.
st.markdown("""
<style>
    div[data-testid="stButton"] > button {
        border-radius: 8px !important;
        width: auto !important;
        height: auto !important;
        padding: 0.5rem 1.25rem !important;
        white-space: nowrap !important;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------
# GERBANG LOGIN
# --------------------------------------------
if "admin_login" not in st.session_state:
    st.session_state.admin_login = False

if not st.session_state.admin_login:
    st.markdown("""
    <div style="background-color:#C85A1A; padding:20px 28px; margin-bottom:24px; border-radius:8px;">
        <h2 style="color:white; margin:0;">🔐 Login Admin</h2>
    </div>
    """, unsafe_allow_html=True)

    col_form, _ = st.columns([1, 2])
    with col_form:
        password_input = st.text_input("Password", type="password", key="admin_password_input")
        if st.button("Masuk", type="primary"):
            if password_input == ADMIN_PASSWORD:
                st.session_state.admin_login = True
                st.rerun()
            else:
                st.error("Password salah. Coba lagi.")
    st.stop()


# --------------------------------------------
# HEADER + TOMBOL LOGOUT
# --------------------------------------------
st.markdown("""
<div style="background-color:#C85A1A; padding:20px 28px; margin-bottom:8px; border-radius:8px;">
    <h2 style="color:white; margin:0;">⚙️ Admin Data PDRB</h2>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Sesi Admin")
    if st.button("🚪 Keluar", width='stretch'):
        st.session_state.admin_login = False
        st.rerun()

st.caption(
    "Gunakan filter di tiap tab buat mempersempit baris yang mau diedit. Klik dua kali sel "
    "untuk mengubah, klik ➕ di baris paling bawah untuk menambah baris baru, pilih baris lalu "
    "tekan tombol 🗑️ (ikon sampah) untuk menghapus. Jangan lupa klik **Simpan Perubahan** setelah selesai."
)
st.divider()

# Tampilkan notifikasi popup yang "dititipkan" sebelum halaman refresh
# (dipakai setelah Simpan Perubahan / Upload Excel berhasil, karena st.rerun()
# langsung memuat ulang halaman sebelum st.toast() sempat tampil kalau dipanggil
# di tempat yang sama).
if "_toast_pesan" in st.session_state:
    _pesan, _ikon = st.session_state.pop("_toast_pesan")
    st.toast(_pesan, icon=_ikon)


# --------------------------------------------
# FUNGSI BANTUAN DATABASE
# --------------------------------------------
def get_conn():
    return get_connection()


def ambil_tabel(nama_tabel):
    """Ambil semua baris dari suatu tabel, tanpa filter apapun."""
    conn = get_conn()
    df = pd.read_sql_query(f"SELECT * FROM {nama_tabel}", conn)
    conn.close()
    return df


def ambil_tabel_filter(nama_tabel, kondisi):
    """
    Ambil baris dari suatu tabel sesuai filter.
    kondisi: dict {nama_kolom: nilai}. Kolom dengan nilai None dilewati (tidak difilter).
    """
    aktif = {k: v for k, v in kondisi.items() if v is not None}
    query = f"SELECT * FROM {nama_tabel}"
    params = []
    if aktif:
        klausa = " AND ".join([f"{k}=%s" for k in aktif])
        query += f" WHERE {klausa}"
        params = list(aktif.values())
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def bersihkan_nilai(nilai):
    """Rapikan satu nilai sebelum disimpan ke database:
    - kalau teks, buang spasi nyangkut di depan/belakang
    - kalau bukan teks (angka, NaN, dll), biarkan apa adanya
    Ini jaring pengaman supaya ketikan yang gak sengaja kepencet spasi
    (mis. 'ADHK ') tidak ikut tersimpan dan bikin data jadi tidak konsisten."""
    if isinstance(nilai, str):
        return nilai.strip()
    return nilai


def simpan_perubahan(nama_tabel, df_asli, df_edit, kolom_data):
    """
    Bandingkan data asli vs hasil edit lalu terapkan INSERT/UPDATE/DELETE
    berdasarkan PRIMARY KEY ASLI tabel tersebut (lihat PRIMARY_KEYS) - Postgres
    tidak punya "rowid" bawaan seperti SQLite, jadi identitas baris dipakai
    dari kombinasi kolom PK-nya sendiri.

    Efeknya: kalau user mengedit salah satu kolom PK di baris yang sudah ada
    (mis. ganti "Tahun" 2025 -> 2026), itu diperlakukan sebagai hapus baris
    lama + tambah baris baru (bukan UPDATE) - hasil akhirnya tetap benar.

    CATATAN: df_asli/df_edit boleh berupa hasil yang sudah difilter (bukan
    seluruh isi tabel) - baris di luar filter tidak akan ikut kehapus, karena
    perbandingan cuma terjadi di antara baris yang memang lagi ditampilkan.
    """
    kolom_pk = PRIMARY_KEYS[nama_tabel]
    kolom_non_pk = [k for k in kolom_data if k not in kolom_pk]

    def pk_lengkap(baris):
        return all(not _kosong(baris.get(k)) for k in kolom_pk)

    def kunci_pk(baris):
        return tuple(bersihkan_nilai(baris[k]) for k in kolom_pk)

    # Baris kosong (mis. baris baru dari tombol ➕ yang belum sempat diisi
    # user) dilewati dulu - PK-nya belum lengkap jadi belum bisa disimpan.
    df_asli_valid = df_asli[df_asli.apply(pk_lengkap, axis=1)] if not df_asli.empty else df_asli
    df_edit_valid = df_edit[df_edit.apply(pk_lengkap, axis=1)] if not df_edit.empty else df_edit

    kunci_asli = {kunci_pk(b): b for _, b in df_asli_valid.iterrows()}
    kunci_edit = {kunci_pk(b): b for _, b in df_edit_valid.iterrows()}

    conn = get_conn()
    cur = conn.cursor()

    # hapus baris yang hilang dari hasil edit (termasuk baris yang PK-nya diubah user)
    where_pk = " AND ".join([f"{k}=%s" for k in kolom_pk])
    for kunci in kunci_asli.keys() - kunci_edit.keys():
        cur.execute(f"DELETE FROM {nama_tabel} WHERE {where_pk}", kunci)

    for kunci, baris in kunci_edit.items():
        if kunci in kunci_asli:
            # PK-nya tidak berubah -> UPDATE kolom non-PK saja
            if kolom_non_pk:
                nilai_non_pk = [bersihkan_nilai(baris[k]) for k in kolom_non_pk]
                set_clause = ",".join([f"{k}=%s" for k in kolom_non_pk])
                cur.execute(
                    f"UPDATE {nama_tabel} SET {set_clause} WHERE {where_pk}",
                    nilai_non_pk + list(kunci)
                )
        else:
            # Baris baru, atau PK-nya baru saja diubah user -> INSERT
            placeholder = ",".join(["%s"] * len(kolom_data))
            nilai_lengkap = [bersihkan_nilai(baris[k]) for k in kolom_data]
            if kolom_non_pk:
                upsert = f"ON CONFLICT ({','.join(kolom_pk)}) DO UPDATE SET " + \
                    ",".join([f"{k}=EXCLUDED.{k}" for k in kolom_non_pk])
            else:
                upsert = f"ON CONFLICT ({','.join(kolom_pk)}) DO NOTHING"
            cur.execute(
                f"INSERT INTO {nama_tabel} ({','.join(kolom_data)}) VALUES ({placeholder}) {upsert}",
                nilai_lengkap
            )

    conn.commit()
    conn.close()


def opsi_filter(nama_tabel, kolom):
    """Bungkus get_opsi_kolom + tambahkan opsi 'Semua' di depan."""
    return ["Semua"] + get_opsi_kolom(nama_tabel, kolom)


def nilai_terkirim(pilihan):
    return None if pilihan == "Semua" else pilihan


# --------------------------------------------
# FUNGSI BANTUAN EDITOR FORMAT LEBAR (kategori/kota/indikator jadi kolom ke
# samping, PERSIS seperti template Excel-nya) - dipakai buat tab Lapangan
# Usaha, Pengeluaran, Wilayah Kab/Kota, dan Fenomena.
# --------------------------------------------
def ambil_tabel_lebar(nama_tabel, kolom_kunci, kolom_pivot, kolom_nilai, daftar_kolom_lebar, kondisi):
    """
    Ambil data dari tabel panjang di database, lalu "lebarkan" (kolom_pivot
    disebar jadi kolom ke samping, kolom_nilai jadi isinya) - supaya
    tampilannya sama seperti template Excel.

    Balikin (df_lebar, kolom_lebar_final). kolom_lebar_final = daftar_kolom_lebar
    ditambah kolom lain yang KEBETULAN ada di data tapi di luar daftar itu
    (mis. data lama di luar template) - supaya kolom itu tetap ditampilkan
    dan tidak diam-diam hilang kalau nanti disimpan ulang.
    """
    df_panjang = ambil_tabel_filter(nama_tabel, kondisi)
    kolom_lebar_final = list(daftar_kolom_lebar)

    if df_panjang.empty:
        return pd.DataFrame(columns=kolom_kunci + kolom_lebar_final), kolom_lebar_final

    df_lebar = df_panjang.pivot_table(
        index=kolom_kunci, columns=kolom_pivot, values=kolom_nilai, aggfunc="first"
    ).reset_index()
    df_lebar.columns.name = None

    for kolom in df_lebar.columns:
        if kolom not in kolom_kunci and kolom not in kolom_lebar_final:
            kolom_lebar_final.append(kolom)
    for kolom in kolom_lebar_final:
        if kolom not in df_lebar.columns:
            df_lebar[kolom] = pd.NA

    return df_lebar[kolom_kunci + kolom_lebar_final], kolom_lebar_final


def _kosong(nilai):
    return nilai is None or nilai == "" or (isinstance(nilai, float) and pd.isna(nilai)) or pd.isna(nilai)


def simpan_perubahan_lebar(nama_tabel, kolom_kunci, kolom_pivot, kolom_nilai, kolom_lebar_final,
                            df_asli_lebar, df_edit_lebar, tipe_nilai="angka"):
    """
    Simpan hasil edit tabel LEBAR balik ke tabel panjang di database.
    Strategi per kombinasi kolom_kunci: hapus semua baris panjang lama untuk
    kombinasi itu, lalu insert ulang tiap kolom lebar yang terisi - jadi
    kolom yang DIKOSONGKAN admin di editor otomatis ikut kehapus juga
    (bukan cuma yang diisi ulang yang ke-update).
    """
    conn = get_conn()
    cur = conn.cursor()

    def kunci_baris(baris):
        return tuple(bersihkan_nilai(baris[k]) for k in kolom_kunci)

    def hapus_kunci(kunci):
        klausa = " AND ".join([f"{k}=%s" for k in kolom_kunci])
        cur.execute(f"DELETE FROM {nama_tabel} WHERE {klausa}", kunci)

    kunci_asli = {kunci_baris(b) for _, b in df_asli_lebar.iterrows()} if not df_asli_lebar.empty else set()
    kunci_edit = {kunci_baris(b) for _, b in df_edit_lebar.iterrows()} if not df_edit_lebar.empty else set()

    # Baris (kombinasi kunci) yang dihapus admin dari editor -> hapus semua
    for kunci in kunci_asli - kunci_edit:
        hapus_kunci(kunci)

    # Baris yang masih ada / baru ditambah -> replace penuh
    for _, baris in df_edit_lebar.iterrows():
        kunci = kunci_baris(baris)
        if any(_kosong(v) for v in kunci):
            continue  # kombinasi kunci belum lengkap diisi -> lewati dulu
        hapus_kunci(kunci)
        for kolom_lebar in kolom_lebar_final:
            nilai_mentah = baris.get(kolom_lebar)
            if _kosong(nilai_mentah):
                continue
            if tipe_nilai == "angka":
                try:
                    nilai_final = float(nilai_mentah)
                except (TypeError, ValueError):
                    continue
            else:
                nilai_final = str(nilai_mentah).strip()
                if nilai_final == "":
                    continue
            nama_kolom_semua = kolom_kunci + [kolom_pivot, kolom_nilai]
            nilai_semua = list(kunci) + [kolom_lebar, nilai_final]
            placeholder = ",".join(["%s"] * len(nama_kolom_semua))
            cur.execute(
                f"INSERT INTO {nama_tabel} ({','.join(nama_kolom_semua)}) VALUES ({placeholder})",
                nilai_semua
            )

    conn.commit()
    conn.close()


def render_editor_tabel_lebar(nama_tabel, kolom_kunci, kolom_pivot, kolom_nilai, daftar_kolom_lebar,
                               column_config_kunci, tipe_nilai, judul, kolom_filter=None,
                               bantuan_kolom_lebar=None):
    """Sama seperti render_editor_tabel(), tapi kategori/kota/indikator
    ditampilkan sebagai KOLOM ke samping (format lebar) - persis seperti
    template Excel-nya - bukan baris terpisah per kategori."""
    st.markdown(f"#### {judul}")
    st.caption(
        "Format tabel ini SAMA seperti template Excel-nya (kategori/kota/indikator "
        "jadi kolom ke samping). Klik dua kali sel untuk mengubah, ➕ di baris paling "
        "bawah untuk baris baru, pilih baris lalu 🗑️ untuk menghapus."
    )

    kondisi = {}
    if kolom_filter:
        st.caption("Pakai filter di bawah buat mempersempit baris yang mau diedit (pilih 'Semua' kalau mau lihat/edit semuanya).")
        kolom_ui = st.columns(len(kolom_filter))
        for i, kolom in enumerate(kolom_filter):
            label = LABEL_KOLOM_FILTER.get(kolom, kolom)
            pilihan = kolom_ui[i].selectbox(
                label, opsi_filter(nama_tabel, kolom), key=f"filter_{nama_tabel}_lebar_{kolom}"
            )
            kondisi[kolom] = nilai_terkirim(pilihan)

    df_asli, kolom_lebar_final = ambil_tabel_lebar(
        nama_tabel, kolom_kunci, kolom_pivot, kolom_nilai, daftar_kolom_lebar, kondisi
    )

    if kolom_filter:
        st.caption(f"Menampilkan {len(df_asli)} baris sesuai filter di atas.")

    column_config = dict(column_config_kunci)
    for kolom_lebar in kolom_lebar_final:
        bantuan = (bantuan_kolom_lebar or {}).get(kolom_lebar)
        if tipe_nilai == "angka":
            column_config[kolom_lebar] = st.column_config.NumberColumn(kolom_lebar, format="%.2f", help=bantuan)
        else:
            column_config[kolom_lebar] = st.column_config.TextColumn(kolom_lebar, width="large", help=bantuan)

    kunci_editor = f"editor_{nama_tabel}_lebar"
    df_edit = st.data_editor(
        df_asli, num_rows="dynamic", width="stretch", key=kunci_editor,
        column_config=column_config, hide_index=True,
    )

    if kolom_filter and any(v is not None for v in kondisi.values()):
        st.caption(
            "⚠️ Baris baru yang kamu tambah lewat tombol ➕ TIDAK otomatis ikut nilai filter "
            "di atas — isi manual semua kolomnya biar konsisten."
        )

    if st.button("💾 Simpan Perubahan", key=f"simpan_{nama_tabel}_lebar", type="primary"):
        try:
            simpan_perubahan_lebar(
                nama_tabel, kolom_kunci, kolom_pivot, kolom_nilai, kolom_lebar_final,
                df_asli, df_edit, tipe_nilai=tipe_nilai
            )
            st.session_state["_toast_pesan"] = (
                f"Perubahan pada tabel '{nama_tabel}' berhasil disimpan.", "✅"
            )
            st.rerun()
        except Exception as e:
            st.toast("Gagal menyimpan perubahan.", icon="❌")
            st.error(f"Gagal menyimpan: {e}")


LABEL_KOLOM_FILTER = {
    "tahun": "Tahun",
    "triwulan": "Triwulan",
    "jenis_data": "Jenis Data",
    "indikator_pertumbuhan": "Indikator Pertumbuhan",
    "pendekatan": "Pendekatan",
}


def render_editor_tabel(nama_tabel, kolom_data, column_config, judul, kolom_filter=None):
    """
    Tampilkan editor untuk satu tabel.
    kolom_filter: daftar nama kolom yang mau dijadikan filter di atas editor
    (mis. ["tahun", "triwulan", "jenis_data", "indikator_pertumbuhan"]).
    Kalau None, tampilkan seluruh isi tabel tanpa filter (cocok buat tabel kecil
    seperti kategori_master).
    """
    st.markdown(f"#### {judul}")

    kondisi = {}
    if kolom_filter:
        st.caption(
            "Pakai filter di bawah buat mempersempit baris yang mau diedit "
            "(pilih 'Semua' kalau mau lihat/edit semuanya)."
        )
        kolom_ui = st.columns(len(kolom_filter))
        for i, kolom in enumerate(kolom_filter):
            label = LABEL_KOLOM_FILTER.get(kolom, kolom)
            pilihan = kolom_ui[i].selectbox(
                label, opsi_filter(nama_tabel, kolom), key=f"filter_{nama_tabel}_{kolom}"
            )
            kondisi[kolom] = nilai_terkirim(pilihan)
        df_asli = ambil_tabel_filter(nama_tabel, kondisi)
    else:
        df_asli = ambil_tabel(nama_tabel)

    if kolom_filter:
        st.caption(f"Menampilkan {len(df_asli)} baris sesuai filter di atas.")

    kunci_editor = f"editor_{nama_tabel}"
    df_edit = st.data_editor(
        df_asli,
        num_rows="dynamic",
        width="stretch",
        key=kunci_editor,
        column_config=column_config,
        hide_index=True,
    )

    if kolom_filter and any(v is not None for v in kondisi.values()):
        st.caption(
            "⚠️ Baris baru yang kamu tambah lewat tombol ➕ TIDAK otomatis ikut nilai filter "
            "di atas — isi manual semua kolomnya biar konsisten."
        )

    if st.button("💾 Simpan Perubahan", key=f"simpan_{nama_tabel}", type="primary"):
        try:
            simpan_perubahan(nama_tabel, df_asli, df_edit, kolom_data)
            st.session_state["_toast_pesan"] = (
                f"Perubahan pada tabel '{nama_tabel}' berhasil disimpan.", "✅"
            )
            st.rerun()
        except Exception as e:
            st.toast(f"Gagal menyimpan perubahan.", icon="❌")
            st.error(f"Gagal menyimpan: {e}")


# --------------------------------------------
# KONFIGURASI KOLOM PER TABEL
# --------------------------------------------
OPSI_TRIWULAN = ["I", "II", "III", "IV"]
OPSI_JENIS_DATA = ["adhk", "adhb"]
OPSI_JENIS_INDIKATOR = ["-", "distribusi", "laju_pertumbuhan", "sumber"]
OPSI_INDIKATOR_PERTUMBUHAN = ["-", "yoy", "qtq", "ctc"]
OPSI_PENDEKATAN = ["lapangan_usaha", "pengeluaran"]

# Khusus tabel sumber_data: dibuat konsisten sama tabel lain (huruf kecil,
# bukan ikut penulisan "ADHK"/"ADHB" di sheet Excel aslinya)
OPSI_JENIS_DATA_SUMBER = ["adhk", "adhb"]
OPSI_KLASIFIKASI_SUMBER = ["-", "lapangan_usaha", "pengeluaran"]

# Untuk fenomena yang dibedakan lewat kategori (bukan indikator pertumbuhan),
# kolom indikator diisi "-" - jadi "-" ikut jadi opsi valid di sini.
OPSI_INDIKATOR_FENOMENA = ["-", "yoy", "qtq", "ctc"]


tab_agregat, tab_lapangan_usaha, tab_pengeluaran, tab_wilayah, tab_kategori, \
    tab_fenomena, tab_sumber, tab_periode, tab_upload = st.tabs([
        "PDRB Agregat", "Lapangan Usaha", "Pengeluaran", "Wilayah Kab/Kota",
        "Kategori Master", "Fenomena", "Sumber Data",
        "🗓️ Atur Tampilan Periode", "📤 Upload Excel"
    ])

with tab_agregat:
    render_editor_tabel(
        "pdrb_agregat",
        kolom_data=["tahun", "triwulan", "jenis_data", "indikator_pertumbuhan", "nilai"],
        column_config={
            "tahun": st.column_config.TextColumn("Tahun", required=True),
            "triwulan": st.column_config.SelectboxColumn("Triwulan", options=OPSI_TRIWULAN, required=True),
            "jenis_data": st.column_config.SelectboxColumn("Jenis Data", options=OPSI_JENIS_DATA, required=True),
            "indikator_pertumbuhan": st.column_config.SelectboxColumn("Indikator", options=OPSI_INDIKATOR_PERTUMBUHAN, required=True),
            "nilai": st.column_config.NumberColumn("Nilai", format="%.2f", required=True),
        },
        judul="PDRB Agregat (Total)",
        kolom_filter=["tahun", "triwulan", "jenis_data", "indikator_pertumbuhan"],
    )

# Daftar kab/kota Kalteng (14 kab/kota) - sumber tunggal buat editor Wilayah
# DAN template Excel "Laju Kalteng", biar dua-duanya selalu sinkron.
DAFTAR_KOTA_KALTENG = [
    "Kotawaringin Barat", "Kotawaringin Timur", "Kapuas", "Barito Selatan",
    "Barito Utara", "Sukamara", "Lamandau", "Seruyan", "Katingan", "Pulang Pisau",
    "Gunung Mas", "Barito Timur", "Murung Raya", "Palangka Raya",
]

with tab_lapangan_usaha:
    render_editor_tabel_lebar(
        "lapangan_usaha",
        kolom_kunci=["tahun", "triwulan", "jenis_data", "jenis_indikator", "indikator_pertumbuhan"],
        kolom_pivot="kode_kategori",
        kolom_nilai="nilai",
        daftar_kolom_lebar=get_urutan_kategori("lapangan_usaha"),
        column_config_kunci={
            "tahun": st.column_config.TextColumn("Tahun", required=True),
            "triwulan": st.column_config.SelectboxColumn("Triwulan", options=OPSI_TRIWULAN, required=True),
            "jenis_data": st.column_config.SelectboxColumn("Jenis Data", options=OPSI_JENIS_DATA, required=True),
            "jenis_indikator": st.column_config.SelectboxColumn("Jenis Indikator", options=OPSI_JENIS_INDIKATOR, required=True),
            "indikator_pertumbuhan": st.column_config.SelectboxColumn("Indikator", options=OPSI_INDIKATOR_PERTUMBUHAN, required=True),
        },
        tipe_nilai="angka",
        judul="PDRB Menurut Lapangan Usaha",
        kolom_filter=["tahun", "triwulan", "jenis_data", "indikator_pertumbuhan"],
    )

with tab_pengeluaran:
    render_editor_tabel_lebar(
        "pengeluaran",
        kolom_kunci=["tahun", "triwulan", "jenis_data", "jenis_indikator", "indikator_pertumbuhan"],
        kolom_pivot="kode_kategori",
        kolom_nilai="nilai",
        daftar_kolom_lebar=get_urutan_kategori("pengeluaran"),
        column_config_kunci={
            "tahun": st.column_config.TextColumn("Tahun", required=True),
            "triwulan": st.column_config.SelectboxColumn("Triwulan", options=OPSI_TRIWULAN, required=True),
            "jenis_data": st.column_config.SelectboxColumn("Jenis Data", options=OPSI_JENIS_DATA, required=True),
            "jenis_indikator": st.column_config.SelectboxColumn("Jenis Indikator", options=OPSI_JENIS_INDIKATOR, required=True),
            "indikator_pertumbuhan": st.column_config.SelectboxColumn("Indikator", options=OPSI_INDIKATOR_PERTUMBUHAN, required=True),
        },
        tipe_nilai="angka",
        judul="PDRB Menurut Pengeluaran",
        kolom_filter=["tahun", "triwulan", "jenis_data", "indikator_pertumbuhan"],
    )

with tab_wilayah:
    render_editor_tabel_lebar(
        "wilayah_kalteng",
        kolom_kunci=["tahun", "triwulan", "indikator_pertumbuhan"],
        kolom_pivot="kota",
        kolom_nilai="nilai",
        daftar_kolom_lebar=DAFTAR_KOTA_KALTENG,
        column_config_kunci={
            "tahun": st.column_config.TextColumn("Tahun", required=True),
            "triwulan": st.column_config.SelectboxColumn("Triwulan", options=OPSI_TRIWULAN, required=True),
            "indikator_pertumbuhan": st.column_config.SelectboxColumn("Indikator", options=OPSI_INDIKATOR_PERTUMBUHAN, required=True),
        },
        tipe_nilai="angka",
        judul="Laju Pertumbuhan Kabupaten/Kota",
        kolom_filter=["tahun", "triwulan", "indikator_pertumbuhan"],
    )

with tab_kategori:
    # Tabel referensi kecil (24 baris) - tanpa filter, tampil semua sekaligus.
    render_editor_tabel(
        "kategori_master",
        kolom_data=["pendekatan", "kode_kategori", "nama_kategori", "ikon"],
        column_config={
            "pendekatan": st.column_config.SelectboxColumn("Pendekatan", options=OPSI_PENDEKATAN, required=True),
            "kode_kategori": st.column_config.TextColumn("Kode Kategori", required=True),
            "nama_kategori": st.column_config.TextColumn("Nama Kategori", required=True),
            "ikon": st.column_config.TextColumn("Ikon (emoji)", required=False),
        },
        judul="Kategori Master (Lapangan Usaha & Pengeluaran)",
    )

with tab_fenomena:
    render_editor_tabel_lebar(
        "fenomena",
        kolom_kunci=["pendekatan", "tahun", "triwulan", "kategori"],
        kolom_pivot="indikator",
        kolom_nilai="teks",
        daftar_kolom_lebar=["-", "qtq", "yoy", "ctc"],
        column_config_kunci={
            "pendekatan": st.column_config.SelectboxColumn("Pendekatan", options=OPSI_PENDEKATAN, required=True),
            "tahun": st.column_config.TextColumn("Tahun", required=True),
            "triwulan": st.column_config.SelectboxColumn("Triwulan", options=OPSI_TRIWULAN, required=True),
            "kategori": st.column_config.TextColumn(
                "Kategori", required=True,
                help="Isi '-' kalau narasi ini dibedakan per indikator pertumbuhan "
                     "-> isi teksnya di kolom qtq/yoy/ctc di samping. Atau isi nama "
                     "kategori spesifik (mis. 'Konsumsi Rumah Tangga') kalau narasi "
                     "ini dibedakan per kategori -> isi teksnya di kolom '-' saja."
            ),
        },
        tipe_nilai="teks",
        judul="Fenomena / Narasi Analisis",
        kolom_filter=["pendekatan", "tahun", "triwulan"],
    )

with tab_sumber:
    # Tabel sumber_data tidak punya kolom tahun/triwulan.
    render_editor_tabel(
        "sumber_data",
        kolom_data=["jenis_indikator", "indikator_pertumbuhan", "klasifikasi", "jenis_data", "link"],
        column_config={
            "jenis_indikator": st.column_config.TextColumn("Jenis Indikator", required=True, help="Contoh: PDRB, Distribusi PDRB, Laju PDRB Palangka, dst"),
            "indikator_pertumbuhan": st.column_config.SelectboxColumn("Indikator Pertumbuhan", options=OPSI_INDIKATOR_PERTUMBUHAN, required=True),
            "klasifikasi": st.column_config.SelectboxColumn("Klasifikasi", options=OPSI_KLASIFIKASI_SUMBER, required=True),
            "jenis_data": st.column_config.SelectboxColumn("Jenis Data", options=OPSI_JENIS_DATA_SUMBER, required=True),
            "link": st.column_config.TextColumn("Link / Judul Sumber", required=True, help="Tautan (URL) atau judul tabel sumber data BPS"),
        },
        judul="Sumber Data (Referensi Link BPS)",
        kolom_filter=["indikator_pertumbuhan", "jenis_data"],
    )


# --------------------------------------------
# TEMPLATE EXCEL UNTUK UPLOAD
# --------------------------------------------
TEMPLATE_SHEETS = {
    "Lapangan Usaha": [
        "Tahun", "Triwulan", "Jenis Data", "Jenis Indikator", "Indikator Pertumbuhan ",
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "MN", "O", "P", "Q", "RSTU", "PDRB",
    ],
    "Pengeluaran": [
        "Tahun", "Triwulan", "Jenis Data", "Jenis Indikator", "Indikator Pertumbuhan ",
        "Pengeluaran Konsumsi Rumah Tangga", "Pengeluaran Konsumsi LNPRT",
        "Pengeluaran Konsumsi Pemerintah", "Pembentukan Modal Tetap Bruto",
        "Perubahan Inventori", "Net Ekspor", "Lainnya", "PDRB",
    ],
    "Laju Kalteng": [
        "Tahun", "Triwulan", "Indikator Pertumbuhan ",
        "Kotawaringin Barat", "Kotawaringin Timur", "Kapuas", "Barito Selatan",
        "Barito Utara", "Sukamara", "Lamandau", "Seruyan", "Katingan", "Pulang Pisau",
        "Gunung Mas", "Barito Timur", "Murung Raya", "Palangka Raya",
    ],
    "Laju Palangka": ["Tahun", "Triwulan", "Jenis Data", "Indikator Pertumbuhan ", "Nilai  "],
    "Sumber Data": ["Jenis Indikator", "Indikator Pertumbuhan", "Klasifikasi", "Jenis Data", "Link"],
    "Fenomena": ["Jenis Klasifikasi", "Tahun", "Triwulan", "Kategori", "qtq", "yoy"],
}


def buat_template_excel():
    """Bikin file Excel kosong (cuma header kolom) sesuai format yang dikenali
    fitur upload di bawah, supaya admin tinggal isi data baru lalu upload balik."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nama_sheet, kolom in TEMPLATE_SHEETS.items():
            pd.DataFrame(columns=kolom).to_excel(writer, sheet_name=nama_sheet, index=False)
    buffer.seek(0)
    return buffer


# --------------------------------------------
# TAB ATUR TAMPILAN PERIODE
# --------------------------------------------
with tab_periode:
    st.caption(
        "⚠️ Daftar di sini DIISI MANUAL — tidak otomatis ambil dari tabel data lain "
        "(karena tahun/triwulan antar tabel bisa tidak sinkron). Tambah baris pakai "
        "➕ di bagian bawah tabel: isi Tahun, pilih Triwulan, centang Tampil kalau boleh "
        "muncul di dashboard. Kombinasi tahun+triwulan yang TIDAK ada di daftar ini "
        "otomatis dianggap tidak tampil, begitu daftar ini sudah pernah diisi minimal 1 baris."
    )
    render_editor_tabel(
        "periode_tampil",
        kolom_data=["tahun", "triwulan", "tampil"],
        column_config={
            "tahun": st.column_config.TextColumn("Tahun", required=True),
            "triwulan": st.column_config.SelectboxColumn("Triwulan", options=OPSI_TRIWULAN, required=True),
            "tampil": st.column_config.CheckboxColumn(
                "Tampil di Dashboard?", default=True,
                help="Centang supaya periode ini muncul di dashboard publik, uncheck untuk menyembunyikan"
            ),
        },
        judul="🗓️ Atur Tampilan Periode",
    )


# --------------------------------------------
# TAB UPLOAD DARI EXCEL
# --------------------------------------------
UPLOAD_TYPES = {
    "Lapangan Usaha (format sheet 'Lapangan Usaha')": {"fungsi": "kategori", "pendekatan": "lapangan_usaha"},
    "Pengeluaran (format sheet 'Pengeluaran')": {"fungsi": "kategori", "pendekatan": "pengeluaran"},
    "Laju Pertumbuhan Kab/Kota Kalteng (format sheet 'Laju Kalteng')": {"fungsi": "wilayah"},
    "Laju/Nilai PDRB Palangka Raya - Agregat (format sheet 'Laju Palangka')": {"fungsi": "laju_kota"},
    "Sumber Data - Referensi Link BPS (format sheet 'Sumber Data')": {"fungsi": "sumber_data"},
    "Fenomena - Narasi Analisis (format sheet 'Fenomena')": {"fungsi": "fenomena"},
}

with tab_upload:
    st.markdown("#### 📤 Upload Data dari File Excel")
    st.caption(
        "Pakai fitur ini buat update data massal (misal data triwulan baru) langsung dari file Excel, "
        "tanpa isi manual satu-satu di tabel. Baris dengan kombinasi kunci yang sama (mis. tahun+triwulan+"
        "kategori yang sama) otomatis TERTIMPA nilai barunya, jadi file yang sama aman diupload berkali-kali."
    )

    st.download_button(
        label="📥 Unduh Template Excel",
        data=buat_template_excel(),
        file_name="Template_Upload_PDRB.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="tombol_download_template",
    )
    st.caption(
        "Template berisi semua sheet yang dikenali sistem beserta nama kolomnya. "
        "Isi sheet yang kamu butuhkan saja (boleh satu sheet), simpan filenya, lalu upload lagi di bawah."
    )
    st.divider()

    file_upload = st.file_uploader("Pilih file Excel (.xlsx)", type=["xlsx"], key="uploader_excel_admin")

    if file_upload is not None:
        try:
            daftar_sheet = pd.ExcelFile(file_upload).sheet_names
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")
            daftar_sheet = []

        if daftar_sheet:
            col_a, col_b = st.columns(2)
            sheet_pilihan = col_a.selectbox("Pilih sheet yang mau diupload", daftar_sheet, key="upload_sheet_pilihan")
            tipe_pilihan = col_b.selectbox("Data ini formatnya sesuai", list(UPLOAD_TYPES.keys()), key="upload_tipe_pilihan")

            info_tipe = UPLOAD_TYPES[tipe_pilihan]

            jenis_data_manual = None
            if info_tipe["fungsi"] == "laju_kota":
                jenis_data_manual = st.selectbox(
                    "Jenis Data (sheet ini tidak punya kolom Jenis Data sendiri, pilih manual)",
                    OPSI_JENIS_DATA, key="upload_jenis_data_manual"
                )

            try:
                df_preview = pd.read_excel(file_upload, sheet_name=sheet_pilihan)
                st.caption(f"Pratinjau 10 baris pertama dari sheet '{sheet_pilihan}':")
                st.dataframe(df_preview.head(10), width='stretch')

                if st.button("🚀 Proses Upload", key="tombol_proses_upload", type="primary"):
                    try:
                        if info_tipe["fungsi"] == "kategori":
                            n1, n2 = upload_kategori_dari_sheet(df_preview, info_tipe["pendekatan"])
                            pesan_sukses = f"Berhasil: {n1} baris data kategori + {n2} baris data PDRB agregat."
                        elif info_tipe["fungsi"] == "wilayah":
                            n = upload_wilayah_dari_sheet(df_preview)
                            pesan_sukses = f"Berhasil upload {n} baris data wilayah."
                        elif info_tipe["fungsi"] == "laju_kota":
                            n = upload_laju_kota_dari_sheet(df_preview, jenis_data=jenis_data_manual)
                            pesan_sukses = f"Berhasil upload {n} baris data PDRB agregat."
                        elif info_tipe["fungsi"] == "sumber_data":
                            n = upload_sumber_data_dari_sheet(df_preview)
                            pesan_sukses = f"Berhasil upload {n} baris data sumber data."
                        elif info_tipe["fungsi"] == "fenomena":
                            n = upload_fenomena_dari_sheet(df_preview)
                            pesan_sukses = f"Berhasil upload {n} baris data fenomena/narasi analisis."
                        st.session_state["_toast_pesan"] = (pesan_sukses, "✅")
                        st.rerun()
                    except Exception as e:
                        st.toast("Gagal memproses upload.", icon="❌")
                        st.error(f"Gagal upload: {e}")
            except Exception as e:
                st.toast("Gagal membaca sheet.", icon="❌")
                st.error(f"Gagal membaca sheet '{sheet_pilihan}': {e}")