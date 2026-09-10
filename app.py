import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import textwrap
from database import init_db, get_agregat, get_data_kategori, get_wilayah, get_fenomena, get_semua_fenomena, get_tren, get_link_sumber, get_link_publikasi, get_urutan_kategori, get_periode_tersedia
from utils.styling import apply_custom_css

# --------------------------------------------
# SETUP AWAL
# --------------------------------------------
init_db()
st.set_page_config(page_title="Dashboard PDRB", layout="wide")
apply_custom_css()

import base64

@st.cache_data
def muat_gambar_base64(path_file):
    """Baca file gambar lokal, ubah jadi teks base64 supaya bisa
    ditempel langsung di tag <img> HTML (path Windows biasa tidak bisa
    diakses langsung oleh browser)."""
    try:
        with open(path_file, "rb") as f:
            data = f.read()
        ekstensi = path_file.split(".")[-1]
        return f"data:image/{ekstensi};base64,{base64.b64encode(data).decode()}"
    except FileNotFoundError:
        return None

st.markdown("""
<style>
    div[data-testid="stSelectbox"] > div > div {
        background-color: #F9C846 !important;
        border-radius: 12px !important;
        border: 2px solid #C85A1A !important;
    }
    /* Baris kolom berisi panel_kiri/panel_kanan: dibuat rantai flex di
       SETIAP lapisan div bawaan Streamlit (kolom -> block internal ->
       container border-nya) memakai flex-grow, bukan height:100%,
       supaya tinggi ikut nyambung sampai ke container paling dalam
       tanpa ketahan oleh div pembungkus yang tidak diberi tinggi. */
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-panel_kiri"]),
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-panel_kanan"]) {
        align-items: stretch;
    }
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-panel_kiri"]) > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-panel_kanan"]) > div[data-testid="stColumn"] {
        display: flex;
        flex-direction: column;
    }
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-panel_kiri"]) > div[data-testid="stColumn"] > div,
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-panel_kanan"]) > div[data-testid="stColumn"] > div {
        display: flex;
        flex-direction: column;
        flex: 1;
        width: 100%;
    }
    .st-key-panel_kiri, .st-key-panel_kanan_wrapper {
        border-radius: 16px;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        flex: 1;
        position: relative;
    }
    .st-key-panel_kiri {
        border: 3px dashed #F07C2A;
        padding: 16px;
    }
    /* Wrapper baru yang membungkus 2 card kanan (Publikasi PDRB +
       Layanan BPS). Defaultnya ditumpuk vertikal (column) dan
       tinggi totalnya mengikuti tinggi panel_kiri di sebelahnya lewat
       flex:1 yang sama-sama diberi ke kedua card di dalamnya, supaya
       total tinggi keduanya otomatis menyamai panel kiri. */
    .st-key-panel_kanan_wrapper {
        gap: 16px;
        height: 100%;
    }
    .st-key-panel_kanan, .st-key-panel_kanan_kontak {
        border: 3px dashed #F07C2A;
        border-radius: 16px;
        padding: 0 16px 32px 16px;
        box-sizing: border-box;
        flex: 1;
        margin: 0 !important;
    }
    /* Layar sempit: wrapper 2 card kanan diubah jadi sejajar (row)
       supaya urutan akhirnya: [Sumber Pertumbuhan] di atas (lebar
       penuh), lalu [Publikasi PDRB][Layanan BPS] sejajar di bawahnya -
       bukan ditumpuk 3 baris ke bawah. */
    @media (max-width: 640px) {
        .st-key-panel_kanan_wrapper {
            flex-direction: row;
        }
    }
    /* Pengecualian: kalau sumber data tidak ada, container TIDAK usah
       dipaksa ikut setinggi panel sebelahnya - biarkan tinggi mengikuti
       konten pesan "Data belum tersedia..." saja. */
    .st-key-panel_kiri:has(.panel-kosong-marker),
    .st-key-panel_kanan:has(.panel-kosong-marker) {
        flex: 0 0 auto !important;
        align-self: flex-start !important;
    }
    /* Baris paginasi (prev / info halaman / next) DIBUNGKUS dalam satu
       container ber-key "baris_paginasi_..." lalu barisnya (hasil
       st.columns) dipaksa jadi flexbox biasa dengan justify-content:
       space-between. Kolom prev & next di-shrink-to-fit (flex: 0 0 auto)
       supaya nempel di ujung kiri/kanan; kolom info di tengah mengambil
       sisa ruang. Ini dipakai karena trik margin negatif & position:
       absolute sebelumnya tidak konsisten akibat lapisan div bawaan
       Streamlit di antaranya. */
    div[class*="st-key-baris_paginasi_"] div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        justify-content: space-between !important;
        align-items: center !important;
        gap: 8px !important;
    }
    div[class*="st-key-baris_paginasi_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }
    div[class*="st-key-baris_paginasi_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-of-type(2) {
        flex: 1 1 auto !important;
        text-align: center;
    }
    /* Tab "Harga Berlaku / Harga Konstan": diubah jadi pill oranye
       supaya senada dengan kartu Q-to-Q dan Y-on-Y di sebelahnya,
       bukan tab bawaan Streamlit (underline merah/abu-abu). */
    div[class*="st-key-tab_pdrb_harga"] div[data-baseweb="tab-list"] {
        background-color: #FDE9A8;
        border-radius: 10px;
        padding: 4px;
        gap: 4px;
    }
    div[class*="st-key-tab_pdrb_harga"] button[data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        color: #7A3B10;
        font-weight: 700;
        font-size: 13px;
        padding: 8px 4px;
        justify-content: center;
    }
    div[class*="st-key-tab_pdrb_harga"] button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #C85A1A;
        color: white;
    }
    div[class*="st-key-tab_pdrb_harga"] div[data-baseweb="tab-highlight"],
    div[class*="st-key-tab_pdrb_harga"] div[data-baseweb="tab-border"] {
        display: none;
    }
    div[class*="st-key-tab_pdrb_harga"] div[data-testid="stTabs"] > div:first-child {
        margin-bottom: 8px;
    }

    /* --------------------------------------------
       PANEL BERHEADER: Filter / Indikator Utama / Nilai PDRB
       Trik: container diberi padding kiri/kanan/bawah, header
       "menutupi" bagian atas dengan margin negatif supaya
       menyentuh tepi & sudutnya nyambung membentuk 1 kartu utuh.
    -------------------------------------------- */
    /* Baris kolom yang berisi ketiga panel ini dipaksa "stretch"
       supaya tinggi kolom mengikuti kolom yang paling tinggi. */
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-panel_header_"]) {
        align-items: stretch;
    }
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-panel_header_"]) > div[data-testid="stColumn"] {
        display: flex;
    }
    div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-panel_header_"]) > div[data-testid="stColumn"] > div {
        width: 100%;
    }
    div[class*="st-key-panel_header_"] {
        background-color: #FFFFFF;
        border-radius: 16px;
        box-shadow: 0 2px 10px rgba(122, 59, 16, 0.10);
        padding: 0 20px 20px 20px;
        min-height: 280px;
        height: 100%;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
    }
    div[class*="st-key-panel_header_"] .judul-panel {
        margin: 0 -20px 18px -20px;
        padding: 16px 20px;
        background-color: #C85A1A;
        border-radius: 16px 16px 0 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    div[class*="st-key-panel_header_"] .judul-panel span.ikon {
        font-size: 17px;
        line-height: 1;
    }
    div[class*="st-key-panel_header_"] .judul-panel span.teks {
        color: white;
        font-weight: 800;
        font-size: 15px;
        letter-spacing: 0.3px;
    }
    div[class*="st-key-panel_header_"] div[data-testid="stSelectbox"] > div > div {
        background-color: #FBE4A6 !important;
    }
    .st-key-panel_header_indikator,
    .st-key-panel_header_nilai {
        min-height: 250px;
    }

    /* --------------------------------------------
       FILTER DATA - bar horizontal di bawah panel Indikator & Nilai PDRB
    -------------------------------------------- */
    .st-key-panel_filter_bar {
        background-color: #FFFFFF;
        border-radius: 16px;
        box-shadow: 0 2px 10px rgba(122, 59, 16, 0.10);
        padding: 0 20px 20px 20px;
        margin-bottom: 24px;
    }
    .st-key-panel_filter_bar .judul-panel-filter {
        margin: 0 -20px 18px -20px;
        padding: 16px 20px;
        background-color: #C85A1A;
        border-radius: 16px 16px 0 0;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
    .st-key-panel_filter_bar .judul-panel-filter span.ikon {
        font-size: 18px;
        line-height: 1;
    }
    .st-key-panel_filter_bar .judul-panel-filter span.teks {
        color: white;
        font-weight: 800;
        font-size: 15px;
        letter-spacing: 0.3px;
    }
    .st-key-panel_hero_intro {
        background-color: #FBF1DE;
        border: 3px dashed #F07C2A;
        border-radius: 20px;
        padding: 20px 20px 4px 20px;
        margin-bottom: 24px;
        box-shadow: 0 2px 10px rgba(122, 59, 16, 0.08);
    }
    .st-key-panel_hero_intro div[data-testid="stHorizontalBlock"] {
        align-items: center;
    }

    .st-key-panel_filter_bar div[data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    .st-key-panel_filter_bar label[data-testid="stWidgetLabel"] p {
        font-weight: 700 !important;
        font-size: 12px !important;
        color: #7A3B10 !important;
        margin-bottom: 2px !important;
    }
    .st-key-panel_filter_bar div[data-testid="stSelectbox"] > div > div {
        background-color: #FDE9A8 !important;
        border: 2px solid #C85A1A !important;
        border-radius: 12px !important;
    }

    /* --------------------------------------------
       KARTU "MEMAHAMI PERTUMBUHAN EKONOMI" - pakai CSS Grid dengan
       jumlah kolom yang diatur eksplisit per breakpoint, supaya
       komposisi saat turun ke baris baru selalu rapi:
       5 (desktop) -> 3+2 -> 2+2+1 -> 1+1+1+1+1 (paling sempit).
    -------------------------------------------- */
    .baris-kartu-penjelasan {
        display: grid !important;
        grid-template-columns: repeat(1, 1fr);
        gap: 14px !important;
    }
    @media (min-width: 481px) {
        .baris-kartu-penjelasan {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    @media (min-width: 821px) {
        .baris-kartu-penjelasan {
            grid-template-columns: repeat(3, 1fr);
        }
    }
    @media (min-width: 1151px) {
        .baris-kartu-penjelasan {
            grid-template-columns: repeat(5, 1fr);
        }
        /* Panah penghubung (›) SENGAJA dihapus - berdasarkan masukan
           sosialisasi, kartu-kartu ini jadi terlalu ramai/bertumpuk kalau
           dikasih dekorasi panah di antaranya. */
    }
</style>
""", unsafe_allow_html=True)




# --------------------------------------------
# BANNER HEADER
# --------------------------------------------
# --------------------------------------------
st.markdown("""
<div style="position:relative; background-color:#C85A1A; padding:24px 0; margin-bottom:24px;
            box-shadow: 0 0 0 100vmax #C85A1A; clip-path: inset(0 -100vmax);">
    <h1 style="color:white; font-size:32px; font-weight:800; margin:0;">
        SISTEM INFORMASI PERTUMBUHAN EKONOMI (SIMPONI)
    </h1>
</div>
""", unsafe_allow_html=True)





# --------------------------------------------
# HELPER: judul grafik/tabel (rata kiri) + tombol "Sumber Data" (rata kanan)
# --------------------------------------------
# --------------------------------------------
def render_judul_grafik(judul_html, daftar_sumber):
    """
    judul_html   : potongan HTML judul (mis. "<h3>...</h3>"), boleh string kosong.
    daftar_sumber: list of (label_tombol, link). link boleh None kalau
                   datanya belum ada di tabel sumber_data -> tombol nonaktif.
    """
    tombol_html_list = []
    for label_tombol, link in daftar_sumber:
        if link:
            tombol_html_list.append(
                f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                'style="background-color:#F9C846; border:2px solid #C85A1A; border-radius:20px; '
                'padding:6px 16px; font-size:12px; font-weight:700; color:#7A3B10; '
                f'text-decoration:none; white-space:nowrap;">🔗 {label_tombol}</a>'
            )
        else:
            tombol_html_list.append(
                '<span style="background-color:#EFE3C8; border:2px solid #D9C39A; border-radius:20px; '
                'padding:6px 16px; font-size:12px; font-weight:700; color:#A8794F; '
                f'white-space:nowrap;">{label_tombol} -</span>'
            )
    tombol_html = '<div style="display:flex; gap:8px; flex-wrap:wrap;">' + "".join(tombol_html_list) + '</div>'

    st.markdown(
        '<div style="display:flex; align-items:center; justify-content:space-between; '
        'gap:12px; flex-wrap:wrap; margin-bottom:6px;">'
        f'<div style="flex:1; min-width:220px;">{judul_html}</div>'
        f'{tombol_html}'
        '</div>',
        unsafe_allow_html=True
    )




# --------------------------------------------
# LABEL TAMPILAN INDIKATOR PERTUMBUHAN
# Dipakai di seluruh dashboard (dropdown, judul grafik, kartu, dll)
# supaya konsisten: qtq -> Q-to-Q, yoy -> Y-on-Y, ctc -> C-to-C.
# --------------------------------------------
def label_indikator(kode):
    return {"qtq": "Q-to-Q", "yoy": "Y-on-Y", "ctc": "C-to-C"}.get(kode, kode.upper())


# --------------------------------------------
# SECTION: MEMAHAMI PERTUMBUHAN EKONOMI (penjelasan singkat PDRB)
# Konten 5 kartu ini statis (bukan dari database) - dibuat untuk
# menjawab masukan sosialisasi soal perlunya penjelasan ringkas
# mengenai Harga Berlaku, Harga Konstan, Distribusi, Laju
# Pertumbuhan, dan Sumber Pertumbuhan sebelum pengguna masuk ke
# panel Filter & angka-angka PDRB.
# --------------------------------------------
def pecahan(atas, bawah):
    """Render pembagian (a/b) sebagai pecahan atas-bawah (bukan simbol /)."""
    return (
        '<span style="display:inline-flex; flex-direction:column; align-items:center; '
        'vertical-align:middle; line-height:1.2; margin:0 4px; font-size:0.95em;">'
        f'<span style="border-bottom:1.5px solid currentColor; padding:0 4px;">{atas}</span>'
        f'<span style="padding:0 4px;">{bawah}</span>'
        '</span>'
    )

DAFTAR_KARTU_PENJELASAN = [
    {
        "nomor": "01",
        "ikon": "🪙",
        "warna_utama": "#C85A1A",
        "warna_bg": "#FDF0DC",
        "judul": "Seberapa Besar?",
        "deskripsi": "Melihat nilai ekonomi yang dihasilkan suatu daerah, dinilai berdasarkan harga yang berlaku saat itu.",
        "formula": "PDRB ADHB = Σ (Pₜ × Qₜ)",
        "keterangan": [
            ("Pₜ", "harga barang/jasa pada periode t"),
            ("Qₜ", "jumlah barang/jasa pada periode t"),
        ],
        "tag": "PDRB ADHB (Harga Berlaku)",
    },
    {
        "nomor": "02",
        "ikon": "📈",
        "warna_utama": "#B9530F",
        "warna_bg": "#FBE6CE",
        "judul": "Apakah Tumbuh?",
        "deskripsi": "Melihat perkembangan ekonomi secara riil, tanpa pengaruh perubahan harga (inflasi).",
        "formula": "PDRB ADHK = Σ (P₀ × Qₜ)",
        "keterangan": [
            ("P₀", "harga pada tahun dasar"),
            ("Qₜ", "jumlah barang/jasa pada periode t"),
        ],
        "tag": "PDRB ADHK (Harga Konstan)",
    },
    {
        "nomor": "03",
        "ikon": "🧭",
        "warna_utama": "#A8460C",
        "warna_bg": "#F9DCBE",
        "judul": "Siapa yang Berperan?",
        "deskripsi": "Melihat seberapa besar kontribusi setiap lapangan usaha atau komponen pengeluaran terhadap total PDRB.",
        "formula": f"Distribusi = ({pecahan('PDRBᵢ', 'PDRB total')}) × 100%",
        "keterangan": [
            ("PDRBᵢ", "PDRB kategori ke-i"),
            ("PDRB total", "total PDRB"),
        ],
        "tag": "Distribusi PDRB",
    },
    {
        "nomor": "04",
        "ikon": "📊",
        "warna_utama": "#97390A",
        "warna_bg": "#F7D3AE",
        "judul": "Bagaimana Arahnya?",
        "deskripsi": "Melihat seberapa cepat perekonomian tumbuh atau mengalami kontraksi dari waktu ke waktu.",
        "formula": f"Laju = (({pecahan('PDRBₜ', 'PDRBₜ₋₁')}) − 1) × 100%",
        "keterangan": [
            ("PDRBₜ", "PDRB periode berjalan"),
            ("PDRBₜ₋₁", "PDRB periode sebelumnya"),
        ],
        "tag": "Laju Pertumbuhan Ekonomi",
    },
    {
        "nomor": "05",
        "ikon": "🥧",
        "warna_utama": "#C85A1A",
        "warna_bg": "#FDE9CE",
        "judul": "Apa Sumber Pertumbuhannya?",
        # "catatan": "Nah, ini yang paling penting dibedakan dari distribusi.",
        "deskripsi": "Menunjukkan kontribusi masing-masing kategori terhadap laju pertumbuhan ekonomi secara keseluruhan.",
        "formula": f"Sumberᵢ = ({pecahan('ΔPDRBᵢ', 'PDRB totalₜ₋₁')}) × 100%",
        "keterangan": [
            ("ΔPDRBᵢ", "perubahan PDRB kategori ke-i"),
            ("PDRB totalₜ₋₁", "total PDRB periode sebelumnya"),
        ],
        "tag": "Sumber Pertumbuhan Ekonomi",
    },
]

def html_kartu_penjelasan(kartu):
    catatan_html = ""
    if kartu.get("catatan"):
        catatan_html = (
            f'<p style="margin:0 0 10px 0; font-size:11.5px; font-style:italic; font-weight:700; '
            f'color:{kartu["warna_utama"]}; line-height:1.5;">{kartu["catatan"]}</p>'
        )

    baris_keterangan = "".join(
        f'<div style="margin-bottom:2px;"><span style="font-weight:700; color:#3D2A16;">{notasi}</span>'
        f' = {arti}</div>'
        for notasi, arti in kartu.get("keterangan", [])
    )
    keterangan_html = ""
    if baris_keterangan:
        keterangan_html = (
            '<div style="font-size:11px; color:#5C4630; line-height:1.6; margin-bottom:10px;">'
            f'<div style="font-weight:800; color:#3D2A16; margin-bottom:2px;">Keterangan:</div>'
            f'{baris_keterangan}'
            '</div>'
        )

    return (
        f'<div class="kartu-penjelasan" style="background-color:{kartu["warna_bg"]}; border-radius:16px; '
        'padding:20px; display:flex; flex-direction:column; min-height:300px; box-sizing:border-box;">'
        '<div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">'
        f'<div style="width:30px; height:30px; border-radius:50%; background-color:{kartu["warna_utama"]}; '
        'color:white; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:12px; flex-shrink:0;">'
        f'{kartu["nomor"]}</div>'
        f'<span style="font-size:22px;">{kartu["ikon"]}</span>'
        '</div>'
        f'<p style="margin:0 0 8px 0; font-weight:800; font-size:15px; color:#3D2A16;">{kartu["judul"]}</p>'
        f'{catatan_html}'
        f'<p style="margin:0 0 12px 0; font-size:12px; color:#5C4630; line-height:1.6;">{kartu["deskripsi"]}</p>'
        f'<div style="background-color:white; border-radius:10px; padding:10px 8px; text-align:center; '
        f'font-size:11.5px; font-weight:700; color:#3D2A16; margin-bottom:10px;">{kartu["formula"]}</div>'
        f'{keterangan_html}'
        f'<div style="flex:1;"></div>'
        f'<div style="background-color:{kartu["warna_utama"]}; border-radius:20px; padding:6px 10px; '
        f'text-align:center; font-size:10.5px; font-weight:700; color:white;">{kartu["tag"]}</div>'
        '</div>'
    )

# Path gambar ilustrasi di sisi kanan pengantar. Sesuaikan lagi kalau
# lokasi filenya berubah / dipindah ke folder proyek.
PATH_ILUSTRASI_HERO = r"C:\Users\Lenovo\Documents\Dashboard_PDRB\assets\ilustrasi.png"

def render_hero_intro():
    with st.container(key="panel_hero_intro"):
        col_hero_teks, col_hero_gambar = st.columns([2, 1.2])

        with col_hero_teks:
            st.markdown(
                '<span style="display:inline-block; background-color:#C85A1A; color:white; font-size:12px; '
                'font-weight:700; padding:6px 16px; border-radius:20px; margin-bottom:16px;">Selamat Datang di SIMPONI Kota Palangka Raya</span>'
                '<h1 style="margin:0 0 14px 0; font-size:26px; font-weight:800; color:#3D2A16; line-height:1.3;">'
                'Bagaimana kita tahu ekonomi suatu daerah sedang tumbuh?</h1>'
                '<p style="margin:0; font-size:14px; color:#5C4630; line-height:1.7;">'
                'Angka pertumbuhan ekonomi bukan sekadar angka. Di baliknya, terdapat aktivitas berbagai lapangan usaha '
                'dan komponen pengeluaran yang bersama-sama membentuk kinerja ekonomi daerah.<br><br>'
                '<strong>SIMPONI</strong> membantu melihat cerita tersebut secara lebih sederhana - mulai dari seberapa '
                'besar ekonomi yang dihasilkan, apakah ekonomi tumbuh, siapa yang berperan, hingga apa yang menjadi '
                'sumber pertumbuhannya.</p>',
                unsafe_allow_html=True
            )

        with col_hero_gambar:
            st.markdown(
                '<p style="font-style:italic; font-weight:600; color:#8A4B1E; font-size:15px; '
                'text-align:right; margin:4px 0 14px 0; line-height:1.6;">'
                'Dari angka, menuju pemahaman untuk pembangunan daerah yang lebih baik.</p>',
                unsafe_allow_html=True
            )
            if os.path.exists(PATH_ILUSTRASI_HERO):
                st.image(PATH_ILUSTRASI_HERO, width="stretch")
            else:
                # Placeholder ini hanya muncul kalau file di PATH_ILUSTRASI_HERO
                # belum ditemukan di komputer yang menjalankan dashboard ini.
                st.markdown(
                    '<div style="width:100%; min-height:130px; border:2px dashed #D9B98A; border-radius:16px; '
                    'display:flex; align-items:center; justify-content:center; color:#B98A55; font-size:12px; '
                    'text-align:center; padding:8px;">'
                    f'Gambar belum ditemukan di:<br>{PATH_ILUSTRASI_HERO}</div>',
                    unsafe_allow_html=True
                )

def render_penjelasan_pdrb():
    isi_baris = "".join(html_kartu_penjelasan(k) for k in DAFTAR_KARTU_PENJELASAN)

    st.markdown(
        '<div style="background-color:#FFFFFF; border-radius:20px; padding:24px; '
        'box-shadow: 0 2px 10px rgba(122, 59, 16, 0.10); margin-bottom:24px;">'
        '<div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">'
        '<span style="font-size:20px;">🧭</span>'
        '<span style="font-size:20px; font-weight:800; color:#3D2A16;">Memahami Pertumbuhan Ekonomi</span>'
        '</div>'
        '<p style="margin:0 0 20px 0; font-size:13px; color:#7A3B10;">'
        'Untuk memahami cerita di balik angka PDRB, mari kita lihat melalui lima hal berikut:</p>'
        f'<div class="baris-kartu-penjelasan">{isi_baris}</div>'
        '</div>',
        unsafe_allow_html=True
    )

render_hero_intro()
render_penjelasan_pdrb()




# --------------------------------------------
# SEMUA DEFINISI FUNGSI DI BAWAH INI (dikonsolidasi jadi satu blok) -
# supaya urutan PEMANGGILANNYA di bagian bawah bisa mengikuti urutan
# TAMPIL yang baru (Filter -> Highlight Peristiwa -> Panel Laju
# Pertumbuhan & Nilai PDRB -> Grafik Tren -> Sumber Pertumbuhan ->
# Tabel -> Distribusi -> Peta Kalteng), bukan urutan definisinya.
# --------------------------------------------

def label_arah(nilai):
    """Balikin (teks, warna, simbol panah) sesuai arah nilai. None kalau datanya belum ada."""
    if nilai is None:
        return "", "", ""
    if nilai >= 0:
        return "Pertumbuhan", "#1B7A3D", "▲"
    else:
        return "Kontraksi", "#C0392B", "▼"

def triwulan_sebelumnya(triwulan, tahun):
    """Cari label triwulan+tahun SEBELUMNYA (buat pembanding Q-to-Q)"""
    urutan = ["I", "II", "III", "IV"]
    idx = urutan.index(triwulan)
    if idx == 0:
        return "IV", str(int(tahun) - 1)
    else:
        return urutan[idx - 1], tahun

def ambil_nilai(df, jenis_data, indikator):
    """Balikin nilai numerik, atau None kalau kombinasi datanya belum ada di database."""
    hasil = df[(df["jenis_data"] == jenis_data) & (df["indikator_pertumbuhan"] == indikator)]["nilai"]
    return hasil.values[0] if not hasil.empty else None

def html_kartu_persen(judul, nilai, warna, panah, label, keterangan):
    """Kartu Q-to-Q / Y-on-Y. Kalau nilai None -> tampilkan 'Data belum tersedia'."""
    if nilai is None:
        isi_nilai = '<span style="font-size:14px; font-weight:700; color:#7A3B10;">Data belum tersedia</span>'
        baris_arah = ""
    else:
        isi_nilai = f'<span style="font-size:26px; font-weight:800;">{nilai:.2f}%</span>'
        baris_arah = f'<span style="color:{warna}; font-weight:700; font-size:13px;">{panah} {label}</span><br>'
    # PENTING: baris_arah ditaruh NEMPEL di tag pembuka <div> (bukan di baris
    # sendiri) - kalau baris_arah kosong ("") dan ditaruh di baris sendiri,
    # baris itu jadi baris KOSONG di tengah blok HTML, yang bikin parser
    # Markdown-nya Streamlit berhenti mengenali ini sebagai HTML dan malah
    # menganggap sisanya sebagai code block biasa (makanya tampil sebagai
    # teks mentah, bukan ke-render).
    return textwrap.dedent(f"""
    <div style="flex:1;">
        <div style="position:relative; text-align:center;">
            <div style="background-color:#C85A1A; border-radius:10px; padding:10px;">
                <span style="color:white; font-weight:700; font-size:14px;">{judul}</span>
            </div>
            <div style="background-color:#FDE9A8; border-radius:12px; padding:20px; margin-top:-8px; min-height:34px; display:flex; align-items:center; justify-content:center;">
                {isi_nilai}
            </div>
        </div>
        <div style="margin-top:10px; text-align:left;">{baris_arah}
            <span style="font-size:12px; color:#555;">{keterangan}</span>
        </div>
    </div>
    """).strip()

def html_kartu_nilai_pdrb(judul, nilai):
    """Kartu Nilai PDRB (Harga Berlaku / Konstan). Kalau nilai None -> 'Data belum tersedia'."""
    isi_nilai = (
        '<span style="font-size:14px; font-weight:700; color:#7A3B10;">Data belum tersedia</span>'
        if nilai is None else
        f'<span style="font-size:22px; font-weight:800;">Rp{nilai:,.1f} M</span>'
    )
    return textwrap.dedent(f"""
    <div style="position:relative; text-align:center; margin-bottom:20px;">
        <div style="background-color:#C85A1A; border-radius:10px; padding:10px;">
            <span style="color:white; font-weight:700; font-size:14px;">{judul}</span>
        </div>
        <div style="background-color:#FDE9A8; border-radius:12px; padding:20px; margin-top:-8px; min-height:34px; display:flex; align-items:center; justify-content:center;">
            {isi_nilai}
        </div>
    </div>
    """).strip()


# --------------------------------------------
# GRAFIK TREN (mengikuti dropdown Tahun/Triwulan/Indikator di atas)
# Histori diambil otomatis dari tabel pdrb_agregat, jendela bergulir 9
# triwulan (3 tahun) terakhir yang BERAKHIR di triwulan yang dipilih -
# kalau periode yang dipilih belum ada datanya, otomatis mundur pakai
# data terakhir yang sudah tersedia.
# --------------------------------------------
def render_grafik_tren(indikator_pertumbuhan, tahun_dipilih, triwulan_dipilih):
    df_tren = get_tren(
        indikator_pertumbuhan=indikator_pertumbuhan,
        tahun=tahun_dipilih, triwulan=triwulan_dipilih
    )

    # Judul dibuat dinamis mengikuti rentang tahun yang BENERAN ditampilkan
    # di jendela bergulir (bukan di-hardcode) - misal cuma ada data 2025-2026,
    # judulnya otomatis "2025 - 2026", bukan tetap "2024 - 2026".
    if df_tren.empty:
        rentang_tahun = str(tahun_dipilih)
    else:
        tahun_awal, tahun_akhir = df_tren["tahun"].iloc[0], df_tren["tahun"].iloc[-1]
        rentang_tahun = tahun_awal if tahun_awal == tahun_akhir else f"{tahun_awal} - {tahun_akhir}"

    judul_tren_html = f"""
    <h3 style="margin:0;">
        Pertumbuhan Ekonomi Kota Palangka Raya
        <span style="font-style:italic; font-weight:400;">({label_indikator(indikator_pertumbuhan)}) (%)</span>
    </h3>
    """
    link_tren = get_link_sumber(
        jenis_indikator="Laju PDRB Agregat",
        indikator_pertumbuhan=indikator_pertumbuhan,
        klasifikasi="-",
        jenis_data="ADHK"
    )
    render_judul_grafik(judul_tren_html, [("Sumber Data", link_tren)])

    if df_tren.empty:
        st.info("Data tren belum tersedia untuk indikator ini.")
        return

    data_tren = pd.DataFrame({
        "Triwulan": df_tren["label"],
        "PDRB": df_tren["nilai"]
    })

    fig_tren = go.Figure()
    fig_tren.add_trace(go.Scatter(
        x=data_tren["Triwulan"], y=data_tren["PDRB"], mode="lines",
        line=dict(color="#B5651D", width=2),
        fill="tozeroy", fillcolor="rgba(197, 106, 45, 0.15)", showlegend=False
    ))
    fig_tren.add_trace(go.Scatter(
        x=data_tren["Triwulan"], y=data_tren["PDRB"], mode="markers+text",
        marker=dict(size=34, symbol="square", color="rgba(0,0,0,0)"),
        text=["📦"] * len(data_tren), textposition="middle center",
        textfont=dict(size=22), showlegend=False
    ))
    fig_tren.add_trace(go.Scatter(
        x=data_tren["Triwulan"], y=[v + 0.55 for v in data_tren["PDRB"]], mode="text",
        text=[f"<b>{v}</b>" for v in data_tren["PDRB"]],
        textfont=dict(size=17, color="black"), showlegend=False
    ))
    titik_terakhir = data_tren.iloc[-1]
    fig_tren.add_annotation(
        x=titik_terakhir["Triwulan"], y=titik_terakhir["PDRB"] + 0.55,
        text=f"<b>{titik_terakhir['PDRB']}</b>", showarrow=False,
        font=dict(size=18, color="black"), bgcolor="#F9C846",
        bordercolor="#C85A1A", borderwidth=2, borderpad=6, xanchor="center"
    )

    batas_bawah = data_tren["PDRB"].min() - 2
    batas_atas = data_tren["PDRB"].max() + 2

    fig_tren.update_layout(
        plot_bgcolor="#FDF6E9", paper_bgcolor="#FDF6E9", height=380,
        margin=dict(l=20, r=20, t=60, b=20),
        yaxis=dict(visible=False, range=[batas_bawah, batas_atas]),
        xaxis=dict(showgrid=False, showline=True, linecolor="#C85A1A", linewidth=2,
                   tickfont=dict(size=13, color="#333"))
    )
    # key wajib unik karena isi semua tab tetap dieksekusi tiap rerun,
    # bukan cuma tab yang lagi aktif dilihat
    st.plotly_chart(fig_tren, width='stretch', key=f"tren_{indikator_pertumbuhan}")


# --------------------------------------------
# FUNGSI BAR CHART & PANEL SUMBER PERTUMBUHAN (definisi fungsi)
# --------------------------------------------
# --------------------------------------------
def buat_bar_chart(data, judul_grafik):
    warna_bar = ["#C0392B" if v < 0 else "#F07C2A" for v in data["Nilai"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data["Kategori"], y=data["Nilai"],
        text=[f"{v:.2f}".replace(".", ",") for v in data["Nilai"]],
        textposition="inside", insidetextanchor="end",
        textfont=dict(size=16, color="white", family="Arial Black"),
        marker_color=warna_bar, showlegend=False
    ))
    fig.update_layout(
        plot_bgcolor="#FDF6E9", paper_bgcolor="#FDF6E9", height=280,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(visible=False), xaxis=dict(showticklabels=False, showgrid=False)
    )
    return fig

@st.fragment
def render_panel(data_lengkap, judul_grafik, key_halaman, pendekatan, item_per_halaman=5):
    if data_lengkap.empty:
        st.markdown(
            f"<div class='panel-kosong-marker' style='display:none;'></div>"
            f"<h5 style='color:#C85A1A; margin:0;'>{judul_grafik}</h5>",
            unsafe_allow_html=True
        )
        st.info("Data belum tersedia untuk kombinasi filter ini.")
        return

    if key_halaman not in st.session_state:
        st.session_state[key_halaman] = 1

    total_item = len(data_lengkap)
    total_halaman = max(1, -(-total_item // item_per_halaman))
    halaman_aktif = st.session_state[key_halaman]

    awal = (halaman_aktif - 1) * item_per_halaman
    akhir = awal + item_per_halaman
    data_halaman_ini = data_lengkap.iloc[awal:akhir].reset_index(drop=True)

    st.markdown(f"<h5 style='color:#C85A1A; margin:0;'>{judul_grafik}</h5>", unsafe_allow_html=True)

    fig = buat_bar_chart(data_halaman_ini, judul_grafik)
    st.plotly_chart(fig, width='stretch', key=f"chart_{key_halaman}")

    kolom_ikon = st.columns(len(data_halaman_ini))
    for i, kol in enumerate(kolom_ikon):
        with kol:
            st.markdown(f"""
            <div style="text-align:center;">
                <div style="width:50px; height:50px; border-radius:50%; border:2px solid #1B4F72;
                            display:flex; align-items:center; justify-content:center; margin:0 auto; font-size:22px;">
                    {data_halaman_ini['Ikon'][i]}
                </div>
                <p style="font-size:11px; margin-top:6px;">{data_halaman_ini['Kategori'][i]}</p>
            </div>
            """, unsafe_allow_html=True)

    with st.container(key=f"baris_paginasi_{key_halaman}"):
        col_prev, col_info, col_next = st.columns([1, 3, 1])
        with col_prev:
            with st.container(key=f"tombol_prev_{key_halaman}"):
                if st.button("⬅️", key=f"prev_{key_halaman}", disabled=(halaman_aktif == 1)):
                    st.session_state[key_halaman] -= 1
                    st.rerun()
        with col_info:
            st.markdown(f"<p style='text-align:center; padding-top:8px; font-size:13px;'>Halaman {halaman_aktif}/{total_halaman}</p>", unsafe_allow_html=True)
        with col_next:
            with st.container(key=f"tombol_next_{key_halaman}"):
                if st.button("➡️", key=f"next_{key_halaman}", disabled=(halaman_aktif == total_halaman)):
                    st.session_state[key_halaman] += 1
                    st.rerun()



# --------------------------------------------
# FUNGSI FENOMENA (narasi analisis singkat per pendekatan)
# --------------------------------------------
def render_fenomena(pendekatan, judul_seksi):
    """
    Menampilkan kartu-kartu fenomena berdampingan untuk (pendekatan, tahun,
    triwulan) yang aktif. "Sumbu" pembeda antar kartu TIDAK selalu
    indikator_pertumbuhan (qtq/yoy) - untuk beberapa pendekatan pembedanya
    adalah kode_kategori (mis. nama kategori tertentu). Jadi tiap baris
    diambil apa adanya dari database, dan judul kartunya ditentukan:
      - kalau kode_kategori BUKAN placeholder umum ("UMUM"/"-") -> pakai
        kode_kategori sebagai judul kartu
      - kalau kode_kategori memang "UMUM"/"-" -> fallback ke
        indikator_pertumbuhan (qtq/yoy/ctc) sebagai judul kartu, seperti semula

    Section (termasuk judul) disembunyikan total kalau tidak ada satupun
    baris fenomena yang datanya ada/tidak kosong.
    """
    df_fenomena = get_semua_fenomena(pendekatan, tahun_dipilih, triwulan_dipilih)
    if df_fenomena.empty:
        return

    daftar_konten = []
    label_pendekatan_generik = pendekatan.replace("_", " ").strip().lower()
    for _, baris in df_fenomena.iterrows():
        kategori = str(baris["kategori"]).strip()
        # Kategori dianggap "cuma placeholder" (bukan judul kartu yang berarti)
        # kalau isinya UMUM/"-"/kosong, ATAU cuma mengulang nama pendekatan itu
        # sendiri (mis. Kategori="Lapangan Usaha" utk pendekatan=lapangan_usaha)
        # -- itu template lama yang sudah ada, tetap harus jatuh ke qtq/yoy.
        if kategori.strip().lower() in ("umum", "-", "", label_pendekatan_generik):
            label_kartu = label_indikator(baris["indikator"])
        else:
            label_kartu = kategori
        daftar_konten.append((label_kartu, baris["teks"]))

    if not daftar_konten:
        return

    judul_html = (
        f"<h3 style='margin:0;'>{judul_seksi} "
        f"<span style='font-style:italic; font-weight:400; font-size:14px;'>"
        f"(Triwulan {triwulan_dipilih} {tahun_dipilih})</span></h3>"
    )
    render_judul_grafik(judul_html, [])

    daftar_kolom = st.columns(len(daftar_konten))
    for kolom, (label_kartu, teks_fenomena) in zip(daftar_kolom, daftar_konten):
        with kolom:
            st.markdown(
                '<div style="border:3px solid #F07C2A; border-radius:16px; padding:20px 24px; '
                'background-color:#FDF0DC; height:100%;">'
                f'<p style="margin:0 0 10px 0; font-size:13px; font-weight:700; color:#C85A1A;">{label_kartu}</p>'
                f'<p style="margin:0; font-size:14px; line-height:1.8; color:#3D2A16; text-align:justify;">{teks_fenomena}</p>'
                '</div>',
                unsafe_allow_html=True
            )



# --------------------------------------------
# FUNGSI TABEL PDRB PER TRIWULAN (definisi fungsi)
# --------------------------------------------
DAFTAR_TRIWULAN = ["I", "II", "III", "IV"]
KOLOM_TABEL = [f"Triwulan {tw}" for tw in DAFTAR_TRIWULAN] + ["Tahunan"]

def format_nilai(nilai):
    if nilai is None:
        return "-"
    teks = f"{nilai:,.2f}"
    # ubah format ribuan/desimal ala Indonesia: 1,384.12 -> 1.384,12
    teks = teks.replace(",", "#").replace(".", ",").replace("#", ".")
    return teks

def siapkan_tabel_triwulan(pendekatan, jenis_data):
    # Urutan kategori WAJIB ikut urutan baku di kategori_master (mis. untuk
    # pengeluaran: Konsumsi RT, LNPRT, Pemerintah, Modal Tetap Bruto,
    # Inventori, Net Ekspor), bukan urutan kemunculan hasil query - supaya
    # tabel tidak "acak" tiap kali direfresh.
    urutan_master = get_urutan_kategori(pendekatan)
    nama_kategori_map = {}
    nilai_per_kategori = {}  # {kode_kategori: {"I": nilai, "II": nilai, ...}}

    for tw in DAFTAR_TRIWULAN:
        df_tw = get_data_kategori(
            pendekatan, tahun_dipilih, tw,
            jenis_data=jenis_data, jenis_indikator="-", indikator_pertumbuhan="-"
        )
        if df_tw.empty:
            continue
        for _, baris in df_tw.iterrows():
            kode = baris["kode_kategori"]
            # "Lainnya" adalah kategori gabungan (LNPRT + Inventori + Net
            # Ekspor) yang cuma dipakai kalau rinciannya sengaja tidak
            # tersedia - jangan ditampilkan dobel kalau rinciannya sendiri
            # sudah ada di tabel ini.
            if kode == "Lainnya":
                continue
            if kode not in nilai_per_kategori:
                nilai_per_kategori[kode] = {}
                nama_kategori_map[kode] = baris["nama_kategori"]
            nilai_per_kategori[kode][tw] = baris["nilai"]

    urutan_kategori = [kode for kode in urutan_master if kode in nilai_per_kategori]

    if not urutan_kategori:
        return []

    baris_tabel = []
    for kode in urutan_kategori:
        baris = {"Kategori": nama_kategori_map[kode]}
        for tw in DAFTAR_TRIWULAN:
            baris[f"Triwulan {tw}"] = format_nilai(nilai_per_kategori[kode].get(tw))
        baris["Tahunan"] = "-"
        baris_tabel.append(baris)

    return baris_tabel


def buat_html_tabel_triwulan(baris_tabel):
    # PENTING: setiap potongan HTML ditulis dalam SATU baris (tanpa newline/indentasi),
    # supaya Markdown tidak menganggapnya code block.
    kolom_header = "".join(
        f'<th style="background-color:#C85A1A; color:white; font-weight:700; font-size:13px; padding:10px 12px; text-align:right; white-space:nowrap;">{k}</th>'
        for k in KOLOM_TABEL
    )
    header_html = (
        f'<th style="background-color:#7A3B10; color:white; font-weight:700; font-size:13px; padding:10px 12px; text-align:left; border-radius:8px 0 0 0;">Kategori</th>'
        f'{kolom_header}'
    )

    baris_html = []
    for i, baris in enumerate(baris_tabel):
        warna_baris = "#FDF6E9" if i % 2 == 0 else "#FBE4C2"
        sel_kategori = f'<td style="padding:9px 12px; font-size:13px; font-weight:600; color:#7A3B10; background-color:{warna_baris}; white-space:nowrap;">{baris["Kategori"]}</td>'
        sel_angka = "".join(
            f'<td style="padding:9px 12px; font-size:13px; font-weight:600; color:#3D2A16; background-color:{warna_baris}; text-align:right;">{baris[k]}</td>'
            for k in KOLOM_TABEL
        )
        baris_html.append(f'<tr>{sel_kategori}{sel_angka}</tr>')

    return (
        '<div style="border:3px solid #F07C2A; border-radius:16px; padding:4px; background-color:#FDF0DC; overflow-x:auto;">'
        '<table style="width:100%; border-collapse:collapse;">'
        f'<thead><tr>{header_html}</tr></thead>'
        f'<tbody>{"".join(baris_html)}</tbody>'
        '</table>'
        '</div>'
    )


def render_tabel_triwulan(pendekatan, judul_seksi):
    # PERBAIKAN: sebelumnya di-replace("_", " ") jadi "lapangan usaha" (spasi),
    # padahal kolom klasifikasi di tabel sumber_data disimpan "lapangan_usaha"
    # (underscore, sama seperti nama tabel/pendekatan). Karena get_link_sumber
    # mencocokkan pakai TRIM+LOWER (bukan normalisasi spasi/underscore), link
    # jadi selalu gagal ketemu untuk lapangan usaha. Pakai pendekatan apa adanya.
    klasifikasi_link = pendekatan
    st.markdown(f"<h3 style='margin:0 0 8px 0;'>{judul_seksi}</h3>", unsafe_allow_html=True)
    tab_adhk, tab_adhb = st.tabs(["ADHK (Harga Konstan)", "ADHB (Harga Berlaku)"])

    with tab_adhk:
        link_adhk = get_link_sumber(
            jenis_indikator="PDRB", indikator_pertumbuhan="-",
            klasifikasi=klasifikasi_link, jenis_data="ADHK"
        )
        render_judul_grafik("", [("Sumber Data", link_adhk)])
        baris_tabel = siapkan_tabel_triwulan(pendekatan, "adhk")
        if not baris_tabel:
            st.info("Data belum tersedia.")
        else:
            st.markdown(buat_html_tabel_triwulan(baris_tabel), unsafe_allow_html=True)

    with tab_adhb:
        link_adhb = get_link_sumber(
            jenis_indikator="PDRB", indikator_pertumbuhan="-",
            klasifikasi=klasifikasi_link, jenis_data="ADHB"
        )
        render_judul_grafik("", [("Sumber Data", link_adhb)])
        baris_tabel = siapkan_tabel_triwulan(pendekatan, "adhb")
        if not baris_tabel:
            st.info("Data belum tersedia.")
        else:
            st.markdown(buat_html_tabel_triwulan(baris_tabel), unsafe_allow_html=True)


# --------------------------------------------
# FUNGSI PANEL DISTRIBUSI (%) vs LAJU PERTUMBUHAN (%) (definisi fungsi)
# --------------------------------------------
def siapkan_data_distribusi_laju(pendekatan, indikator):
    df_distribusi = get_data_kategori(
        pendekatan, tahun_dipilih, triwulan_dipilih,
        jenis_data="adhb", jenis_indikator="distribusi"
    )
    df_laju = get_data_kategori(
        pendekatan, tahun_dipilih, triwulan_dipilih,
        jenis_data="adhk", jenis_indikator="laju_pertumbuhan",
        indikator_pertumbuhan=indikator
    )
    if df_distribusi.empty or df_laju.empty:
        return pd.DataFrame(columns=["kode_kategori", "Kategori", "Distribusi", "Laju"])

    df_gabungan = pd.merge(
        df_distribusi[["kode_kategori", "nama_kategori", "nilai"]].rename(columns={"nilai": "Distribusi"}),
        df_laju[["kode_kategori", "nilai"]].rename(columns={"nilai": "Laju"}),
        on="kode_kategori"
    )
    df_gabungan = df_gabungan.rename(columns={"nama_kategori": "Kategori"})
    df_gabungan = df_gabungan.sort_values("Distribusi", ascending=False).reset_index(drop=True)
    return df_gabungan


def render_distribusi_laju(pendekatan, judul_seksi, indikator):
    # PERBAIKAN: sama seperti di render_tabel_triwulan - pakai pendekatan
    # apa adanya (mis. "lapangan_usaha"), jangan diganti jadi "lapangan usaha".
    klasifikasi_link = pendekatan
    link_distribusi = get_link_sumber(
        jenis_indikator="Distribusi PDRB", indikator_pertumbuhan="-",
        klasifikasi=klasifikasi_link, jenis_data="ADHB"
    )
    link_laju = get_link_sumber(
        jenis_indikator="Laju PDRB Palangka", indikator_pertumbuhan=indikator,
        klasifikasi=klasifikasi_link, jenis_data="ADHK"
    )
    daftar_sumber = [("Sumber Distribusi", link_distribusi), ("Sumber Laju", link_laju)]
    data_distribusi_laju = siapkan_data_distribusi_laju(pendekatan, indikator)

    if data_distribusi_laju.empty:
        render_judul_grafik(f"<h3 style='margin:0;'>{judul_seksi}</h3>", daftar_sumber)
        st.info("Data distribusi belum tersedia untuk periode ini.")
        return

    render_judul_grafik(f"<h3 style='margin:0;'>{judul_seksi}</h3>", daftar_sumber)

    maks_distribusi = data_distribusi_laju["Distribusi"].max()
    maks_laju = data_distribusi_laju["Laju"].abs().max()

    # PENTING: setiap potongan HTML ditulis dalam SATU baris (tanpa newline/indentasi).
    # Kalau ada baris yang diawali >=4 spasi, Markdown akan menganggapnya sebagai
    # code block dan menampilkan HTML mentah alih-alih merendernya.
    daftar_baris_html = []
    for _, baris in data_distribusi_laju.iterrows():
        teks_distribusi = f"{baris['Distribusi']:.2f}".replace(".", ",")
        teks_laju = f"{baris['Laju']:.2f}".replace(".", ",")
        lebar_distribusi = max(2, (baris["Distribusi"] / maks_distribusi) * 100)
        # lebar_laju dihitung sebagai % dari SATU sisi (zona positif ATAU
        # zona negatif) sehingga nilai dengan |laju| terbesar akan memenuhi
        # penuh salah satu sisi tsb - bukan % dari keseluruhan kolom Laju.
        lebar_laju = max(2, (abs(baris["Laju"]) / maks_laju) * 100)
        warna_laju = "#C0392B" if baris["Laju"] < 0 else "#F07C2A"

        # PERBAIKAN: batang Laju sekarang punya garis nol (baseline) di
        # tengah kolom Laju. Nilai positif tumbuh ke KANAN dari baseline,
        # nilai negatif tumbuh ke KIRI dari baseline (bukan sama-sama
        # tumbuh ke kanan cuma beda warna seperti sebelumnya) - meniru
        # gaya grafik "diverging bar" pada contoh referensi.
        if baris["Laju"] < 0:
            zona_kiri = (
                '<div style="flex:1; display:flex; align-items:center; justify-content:flex-end; gap:6px;">'
                f'<span style="font-size:12px; font-weight:600; white-space:nowrap; color:{warna_laju};">{teks_laju}</span>'
                f'<div style="background-color:{warna_laju}; height:16px; width:{lebar_laju}%; border-radius:3px 0 0 3px;"></div>'
                '</div>'
            )
            zona_kanan = '<div style="flex:1;"></div>'
        else:
            zona_kiri = '<div style="flex:1;"></div>'
            zona_kanan = (
                '<div style="flex:1; display:flex; align-items:center; gap:6px;">'
                f'<div style="background-color:{warna_laju}; height:16px; width:{lebar_laju}%; border-radius:0 3px 3px 0;"></div>'
                f'<span style="font-size:12px; font-weight:600; white-space:nowrap; color:{warna_laju};">{teks_laju}</span>'
                '</div>'
            )

        satu_baris = (
            '<div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">'
            '<div style="flex:1; display:flex; align-items:center; justify-content:flex-end; gap:6px;">'
            f'<span style="font-size:12px; font-weight:600; white-space:nowrap;">{teks_distribusi}</span>'
            f'<div style="background-color:#F07C2A; height:16px; width:{lebar_distribusi}%; border-radius:3px;"></div>'
            '</div>'
            '<div style="flex:1.4; text-align:center;">'
            f'<span style="background-color:#FBD9A6; border-radius:12px; padding:3px 10px; font-size:11px; font-weight:600; color:#7A3B10; display:inline-block;">{baris["Kategori"]}</span>'
            '</div>'
            '<div style="flex:1; display:flex; align-items:stretch;">'
            f'{zona_kiri}'
            '<div style="width:2px; background-color:#C85A1A; opacity:0.35;"></div>'
            f'{zona_kanan}'
            '</div>'
            '</div>'
        )
        daftar_baris_html.append(satu_baris)

    baris_html = "".join(daftar_baris_html)

    html_panel = (
        '<div style="border:3px solid #F07C2A; border-radius:20px; padding:24px; background-color:#FDF0DC;">'
        '<div style="display:flex; margin-bottom:16px;">'
        '<div style="flex:1; background-color:#C85A1A; border-radius:10px; padding:8px; text-align:center;">'
        '<span style="color:white; font-weight:700; font-size:14px;">Distribusi (%)</span>'
        '</div>'
        '<div style="flex:1.4;"></div>'
        '<div style="flex:1; background-color:#C85A1A; border-radius:10px; padding:8px; text-align:center;">'
        f'<span style="color:white; font-weight:700; font-size:14px;">Laju Pertumbuhan ({label_indikator(indikator)}) (%)</span>'
        '</div>'
        '</div>'
        f'{baris_html}'
        '</div>'
    )
    st.markdown(html_panel, unsafe_allow_html=True)


# --------------------------------------------
# FUNGSI SIAPKAN DATA BAR (dipakai section Sumber Pertumbuhan)
# --------------------------------------------
def siapkan_data_bar(pendekatan, indikator):
    df = get_data_kategori(
        pendekatan, tahun_dipilih, triwulan_dipilih,
        jenis_data="adhk", jenis_indikator="sumber",
        indikator_pertumbuhan=indikator
    )
    if df.empty:
        return pd.DataFrame(columns=["Kategori", "Nilai", "Ikon"])
    df_hasil = df.rename(columns={"nama_kategori": "Kategori", "nilai": "Nilai", "ikon": "Ikon"})
    df_hasil = df_hasil[["Kategori", "Nilai", "Ikon"]].sort_values("Nilai", ascending=False).reset_index(drop=True)
    return df_hasil


# --------------------------------------------
# FILTER DATA (bar horizontal, tampil tepat setelah bagian penjelasan -
# sesuai masukan sosialisasi supaya filter tidak "menumpuk" di kiri, dan
# pengguna sudah paham dulu istilah-istilah PDRB sebelum memilih periode)
# --------------------------------------------
# Opsi Tahun & Triwulan TIDAK di-hardcode - diambil otomatis dari data
# yang sudah diinput admin ke pdrb_agregat. Kalau baru rilis sampai
# Triwulan II 2026, opsi berhenti di situ; begitu ada data baru
# (mis. Triwulan II 2027), opsi tahun & triwulan otomatis bertambah.
df_periode_tersedia = get_periode_tersedia()
if df_periode_tersedia.empty:
    daftar_tahun_tersedia = ["2026"]
else:
    daftar_tahun_tersedia = sorted(df_periode_tersedia["tahun"].unique().tolist())

with st.container(key="panel_filter_bar"):
    st.markdown(
        '<div class="judul-panel-filter"><span class="teks">FILTER DATA</span></div>',
        unsafe_allow_html=True
    )

    col_judul_filter, col_f_tahun, col_f_triwulan, col_f_jenis_data, col_f_indikator = st.columns(
        [2, 1, 1, 1.3, 1.2]
    )

    with col_judul_filter:
        st.markdown(
            '<div style="display:flex; align-items:center; gap:12px;">'
            '<img src="https://img.icons8.com/wired/64/filter.png" alt="filter" '
            'style="width:40px; height:40px; flex-shrink:0;">'
            '<div style="font-size:15px; font-weight:600; color:#7A3B10; line-height:1.5;">'
            'Sesuaikan periode dan indikator yang ingin Anda lihat.</div>'
            '</div>',
            unsafe_allow_html=True
        )

    with col_f_tahun:
        tahun_dipilih = st.selectbox(
            "Tahun", options=daftar_tahun_tersedia,
            index=len(daftar_tahun_tersedia) - 1,
            format_func=lambda x: f"🗓️ {x}"
        )

    if df_periode_tersedia.empty:
        daftar_triwulan_tersedia = ["I"]
    else:
        daftar_triwulan_tersedia = df_periode_tersedia[
            df_periode_tersedia["tahun"] == tahun_dipilih
        ]["triwulan"].tolist()
        if not daftar_triwulan_tersedia:
            daftar_triwulan_tersedia = ["I"]

    with col_f_triwulan:
        triwulan_dipilih = st.selectbox(
            "Triwulan", options=daftar_triwulan_tersedia,
            index=len(daftar_triwulan_tersedia) - 1,
            format_func=lambda x: f"🗓️ {x}"
        )

    with col_f_jenis_data:
        # Dipakai buat menentukan pendekatan (lapangan_usaha/pengeluaran)
        # di section "Highlight Peristiwa", "Sumber Pertumbuhan", "Tabel
        # Nilai PDRB per Triwulan", dan "Distribusi" di bawah - bagian
        # lain (Laju Pertumbuhan PDRB Palangka Raya, Grafik Tren, Peta
        # Kalteng) memang tidak dipecah per pendekatan, jadi tidak
        # terpengaruh oleh pilihan ini.
        jenis_data_dipilih = st.selectbox(
            "Jenis Data", options=["Lapangan Usaha", "Pengeluaran"],
            format_func=lambda x: f"🗃️ {x}"
        )

    with col_f_indikator:
        indikator_dipilih = st.selectbox(
            "Indikator", options=["yoy", "qtq", "ctc"],
            format_func=lambda x: f"📈 {label_indikator(x)}"
        )


# --------------------------------------------
# PENDEKATAN TERPILIH (dari filter "Jenis Data" di atas) - dipakai di
# section "Highlight Peristiwa", "Sumber Pertumbuhan", "Tabel Nilai PDRB
# per Triwulan", dan "Distribusi" supaya section-section itu cukup
# menampilkan SATU pendekatan sesuai pilihan pengguna (bukan menumpuk
# lapangan usaha & pengeluaran sekaligus seperti sebelumnya).
# --------------------------------------------
PETA_PENDEKATAN = {"Lapangan Usaha": "lapangan_usaha", "Pengeluaran": "pengeluaran"}
pendekatan_dipilih = PETA_PENDEKATAN[jenis_data_dipilih]


# --------------------------------------------
# HIGHLIGHT PERISTIWA (berdasarkan pilihan Jenis Data di Filter Data)
# --------------------------------------------
render_fenomena(pendekatan_dipilih, f"Highlight Peristiwa Perekonomian Palangka Raya Menurut {jenis_data_dipilih}")

st.divider()


# --------------------------------------------
# AMBIL DATA AGREGAT DARI DATABASE
# --------------------------------------------
df_agregat = get_agregat(tahun_dipilih, triwulan_dipilih)

nilai_qtq = ambil_nilai(df_agregat, "adhk", "qtq")
nilai_yoy = ambil_nilai(df_agregat, "adhk", "yoy")
nilai_ctc = ambil_nilai(df_agregat, "adhk", "ctc")
nilai_adhb = ambil_nilai(df_agregat, "adhb", "-")
nilai_adhk = ambil_nilai(df_agregat, "adhk", "-")

tw_sebelumnya, tahun_tw_sebelumnya = triwulan_sebelumnya(triwulan_dipilih, tahun_dipilih)
label_qtq, warna_qtq, panah_qtq = label_arah(nilai_qtq)
label_yoy, warna_yoy, panah_yoy = label_arah(nilai_yoy)
label_ctc, warna_ctc, panah_ctc = label_arah(nilai_ctc)

col_panel_indikator, col_panel_nilai = st.columns([1.6, 1.3])

with col_panel_indikator:
    with st.container(key="panel_header_indikator"):
        st.markdown(
            '<div class="judul-panel"><span class="ikon">📊</span>'
            '<span class="teks">LAJU PERTUMBUHAN PDRB PALANGKA RAYA</span></div>',
            unsafe_allow_html=True
        )
        kartu_qtq_html = html_kartu_persen(
            "Q-to-Q", nilai_qtq, warna_qtq, panah_qtq, label_qtq,
            f"Dibanding Triwulan {tw_sebelumnya} {tahun_tw_sebelumnya}"
        )
        kartu_yoy_html = html_kartu_persen(
            "Y-on-Y", nilai_yoy, warna_yoy, panah_yoy, label_yoy,
            f"Dibanding Triwulan {triwulan_dipilih} {int(tahun_dipilih)-1}"
        )
        kartu_ctc_html = html_kartu_persen(
            "C-to-C", nilai_ctc, warna_ctc, panah_ctc, label_ctc,
            f"Dibanding Kumulatif s.d. Tw {triwulan_dipilih} {int(tahun_dipilih)-1}"
        )
        st.markdown(
            f'<div style="display:flex; gap:16px;">{kartu_qtq_html}{kartu_yoy_html}{kartu_ctc_html}</div>',
            unsafe_allow_html=True
        )

with col_panel_nilai:
    with st.container(key="panel_header_nilai"):
        st.markdown(
            '<div class="judul-panel">'
            '<span class="ikon" style="border:2px solid white; border-radius:50%; width:20px; height:20px; '
            'display:inline-flex; align-items:center; justify-content:center; font-size:9px; font-weight:800; color:white;">Rp</span>'
            '<span class="teks">NILAI PDRB</span>'
            '</div>',
            unsafe_allow_html=True
        )
        with st.container(key="tab_pdrb_harga"):
            tab_berlaku, tab_konstan = st.tabs(["Harga Berlaku", "Harga Konstan"])
            with tab_berlaku:
                st.markdown(html_kartu_nilai_pdrb("PDRB Harga Berlaku", nilai_adhb), unsafe_allow_html=True)
            with tab_konstan:
                st.markdown(html_kartu_nilai_pdrb("PDRB Harga Konstan", nilai_adhk), unsafe_allow_html=True)


st.divider()


render_grafik_tren(indikator_dipilih, tahun_dipilih, triwulan_dipilih)

st.divider()

# --------------------------------------------
# SUMBER PERTUMBUHAN PDRB (berdasarkan pilihan Jenis Data di Filter Data)
# + kartu Link Publikasi PDRB di sebelahnya
# --------------------------------------------
data_bar_terpilih = siapkan_data_bar(pendekatan_dipilih, indikator_dipilih)

col_sumber_pertumbuhan, col_publikasi = st.columns([2, 1])

with col_sumber_pertumbuhan:
    with st.container(key="panel_kiri"):
        render_panel(
            data_bar_terpilih,
            f"SUMBER PERTUMBUHAN PDRB MENURUT {jenis_data_dipilih.upper()} TRIWULAN {triwulan_dipilih} {tahun_dipilih} ({label_indikator(indikator_dipilih)}) (%)",
            key_halaman="halaman_sumber_pertumbuhan",
            pendekatan=pendekatan_dipilih
        )

with col_publikasi:
    with st.container(key="panel_kanan_wrapper"):
        with st.container(key="panel_kanan"):
            # Link publikasi diambil dari tabel publikasi_pdrb berdasarkan
            # tahun & Jenis Data yang aktif di Filter Data. Kalau tahun yang
            # dipilih belum ada publikasinya, get_link_publikasi otomatis
            # mundur ke tahun TERDEKAT DI BAWAHNYA yang jenis datanya sama
            # (tidak pernah mengambil publikasi dari tahun yang lebih baru).
            link_publikasi = get_link_publikasi(
                tahun=tahun_dipilih, jenis_data=pendekatan_dipilih
            )
            teks_tombol_publikasi = f"Publikasi PDRB menurut {jenis_data_dipilih}"
            if link_publikasi:
                tombol_publikasi_html = (
                    f'<a href="{link_publikasi}" target="_blank" rel="noopener noreferrer" '
                    'style="background-color:#C85A1A; color:white; text-decoration:none; font-weight:700; '
                    'font-size:13px; padding:10px 22px; border-radius:20px; display:inline-block; white-space:nowrap;">'
                    f'{teks_tombol_publikasi}</a>'
                )
            else:
                tombol_publikasi_html = (
                    '<span style="background-color:#EFE3C8; color:#A8794F; font-weight:700; font-size:13px; '
                    'padding:10px 22px; border-radius:20px; display:inline-block; white-space:nowrap;">'
                    f'{teks_tombol_publikasi} - Belum Tersedia</span>'
                )
            gambar_publikasi = muat_gambar_base64("assets/publikasi.png")
            tag_gambar_publikasi = (
                f'<img src="{gambar_publikasi}" alt="Publikasi PDRB" '
                'style="width:140px; height:140px; object-fit:contain;">'
                if gambar_publikasi else
                '<div style="font-size:48px;">📚</div>'
            )
            st.markdown(
                '<div style="text-align:center; display:flex; flex-direction:column; align-items:center; '
                'justify-content:center; height:100%; padding:0;">'
                f'{tag_gambar_publikasi}'
                '<p style="font-weight:800; font-size:15px; color:#3D2A16; margin:0 0 6px 0;">Publikasi PDRB</p>'
                '<p style="font-size:12px; color:#7A3B10; margin:0 0 18px 0; line-height:1.6;">'
                'Baca publikasi lengkap PDRB Kota Palangka Raya.</p>'
                f'{tombol_publikasi_html}'
                '</div>',
                unsafe_allow_html=True
            )

        # --------------------------------------------
        # CARD BARU: Layanan & Kontak BPS Kota Palangka Raya
        # Gambar pelayanan.png di atas, 2 tombol link (Website & WhatsApp)
        # berdampingan di bawahnya.
        # --------------------------------------------
        with st.container(key="panel_kanan_kontak"):
            url_bps = "https://palangkakota.bps.go.id"
            url_wa = "https://wa.me/6285810006271"

            gambar_pelayanan = muat_gambar_base64("assets/pelayanan.png")
            tag_gambar_pelayanan = (
                f'<img src="{gambar_pelayanan}" alt="Layanan BPS" '
                'style="width:140px; height:140px; object-fit:contain;">'
                if gambar_pelayanan else
                '<div style="font-size:48px;">📞</div>'
            )
            st.markdown(
                '<div style="text-align:center; display:flex; flex-direction:column; align-items:center; '
                'justify-content:center; height:100%; padding:0;">'
                f'{tag_gambar_pelayanan}'
                '<p style="font-weight:800; font-size:15px; color:#3D2A16; margin:0 0 6px 0;">Layanan BPS Kota Palangka Raya</p>'
                '<p style="font-size:12px; color:#7A3B10; margin:0 0 18px 0; line-height:1.6;">'
                'Hubungi kami untuk informasi lebih lanjut.</p>'
                '<div style="display:flex; gap:10px; justify-content:center; flex-wrap:wrap;">'
                f'<a href="{url_bps}" target="_blank" rel="noopener noreferrer" '
                'style="background-color:#C85A1A; color:white; text-decoration:none; font-weight:700; '
                'font-size:12px; padding:10px 16px; border-radius:20px; display:inline-block; white-space:nowrap;">'
                '🌐 Website BPS</a>'
                f'<a href="{url_wa}" target="_blank" rel="noopener noreferrer" '
                'style="background-color:#C85A1A; color:white; text-decoration:none; font-weight:700; '
                'font-size:12px; padding:10px 16px; border-radius:20px; display:inline-block; white-space:nowrap;">'
                '💬 0858-1000-6271</a>'
                '</div>'
                '</div>',
                unsafe_allow_html=True
            )

st.divider()


# --------------------------------------------
# TABEL PDRB PER TRIWULAN (berdasarkan pilihan Jenis Data di Filter Data)
# --------------------------------------------
render_tabel_triwulan(pendekatan_dipilih, f"PDRB Triwulanan menurut {jenis_data_dipilih} {tahun_dipilih} (Miliar Rupiah)")

st.divider()


# --------------------------------------------
# DISTRIBUSI (%) vs LAJU PERTUMBUHAN (%) (berdasarkan pilihan Jenis Data di Filter Data)
# --------------------------------------------
render_distribusi_laju(pendekatan_dipilih, f"Distribusi dan Laju Pertumbuhan PDRB Menurut {jenis_data_dipilih} (%)", indikator_dipilih)

st.divider()


# --------------------------------------------
# PETA TEMATIK KALIMANTAN TENGAH + BAR LAJU PERTUMBUHAN WILAYAH
# --------------------------------------------
# --------------------------------------------
judul_wilayah_html = (
    "<h3 style='margin:0;'>Laju Pertumbuhan PDRB Kabupaten/Kota se-Kalimantan Tengah "
    f"<span style='font-style:italic; font-weight:400;'>({label_indikator(indikator_dipilih)}) (%)</span></h3>"
)
link_wilayah = get_link_sumber(
    jenis_indikator="Laju Pertumbuhan Kalteng",
    indikator_pertumbuhan=indikator_dipilih,
    klasifikasi="-",
    jenis_data="ADHK"
)
render_judul_grafik(judul_wilayah_html, [("Sumber Data", link_wilayah)])

with open("assets/kalteng.geojson", "r", encoding="utf-8") as f:
    geojson_kalteng = json.load(f)

df_wilayah = get_wilayah(tahun_dipilih, triwulan_dipilih, indikator_pertumbuhan=indikator_dipilih)
df_wilayah = df_wilayah.rename(columns={"kota": "Wilayah", "nilai": "Pertumbuhan"})

# --- Samakan nama wilayah dengan properti "kab_kota" di geojson ---
# Kadang penulisan di database ("Palangka Raya") beda dengan di geojson
# ("Kota Palangka Raya"), sehingga Plotly gagal mencocokkan lokasi dan
# wilayah itu tampil putih kosong tanpa nilai saat hover.
def normalisasi_nama_wilayah(nama):
    return (
        nama.lower()
        .replace("kabupaten ", "")
        .replace("kota ", "")
        .strip()
    )

nama_kab_kota_geojson = [
    fitur["properties"]["kab_kota"] for fitur in geojson_kalteng["features"]
]
peta_nama_wilayah = {
    normalisasi_nama_wilayah(nama): nama for nama in nama_kab_kota_geojson
}
df_wilayah["Wilayah"] = df_wilayah["Wilayah"].apply(
    lambda nama: peta_nama_wilayah.get(normalisasi_nama_wilayah(nama), nama)
)

col_peta, col_bar_wilayah = st.columns([1.1, 1])

with col_peta:
    fig_peta = px.choropleth(
        df_wilayah,
        geojson=geojson_kalteng,
        locations="Wilayah",
        featureidkey="properties.kab_kota",
        color="Pertumbuhan",
        color_continuous_scale=["#FDE9A8", "#F9C846", "#F07C2A", "#C85A1A"],
        projection="mercator"
    )
    fig_peta.update_geos(fitbounds="locations", visible=False)
    fig_peta.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=500,
        paper_bgcolor="#FDF6E9", coloraxis_colorbar=dict(title="Pertumbuhan (%)"),
        dragmode=False
    )
    st.plotly_chart(
        fig_peta, width='stretch',
        config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False}
    )

with col_bar_wilayah:
    df_wilayah_urut = df_wilayah.sort_values("Pertumbuhan", ascending=True).reset_index(drop=True)

    # Kota Palangka Raya (fokus utama dashboard ini) diberi warna KHUSUS
    # yang beda dari kabupaten/kota lain, supaya langsung kelihatan di
    # antara batang-batang lainnya - terlepas dari nilainya positif/negatif.
    def warna_bar_per_wilayah(nama_wilayah, nilai):
        if "palangka" in str(nama_wilayah).lower():
            return "#1B4F72"
        return "#C0392B" if nilai < 0 else "#F07C2A"

    warna_bar_wilayah = [
        warna_bar_per_wilayah(nama, nilai)
        for nama, nilai in zip(df_wilayah_urut["Wilayah"], df_wilayah_urut["Pertumbuhan"])
    ]

    fig_bar_wilayah = go.Figure(go.Bar(
        x=df_wilayah_urut["Pertumbuhan"], y=df_wilayah_urut["Wilayah"],
        orientation="h",
        text=[f"{v:.2f}".replace(".", ",") for v in df_wilayah_urut["Pertumbuhan"]],
        textposition="inside", insidetextanchor="end",
        textfont=dict(size=12, color="white", family="Arial Black"),
        marker_color=warna_bar_wilayah, showlegend=False
    ))
    fig_bar_wilayah.update_layout(
        plot_bgcolor="#FDF6E9", paper_bgcolor="#FDF6E9",
        height=500, margin=dict(l=10, r=40, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(tickfont=dict(size=11, color="#333"))
    )
    st.plotly_chart(fig_bar_wilayah, width='stretch')

    st.markdown(
        '<div style="display:flex; gap:16px; justify-content:center; flex-wrap:wrap; margin-top:-8px;">'
        '<span style="font-size:12px; color:#555;"><span style="display:inline-block; width:12px; height:12px; '
        'background-color:#1B4F72; border-radius:3px; margin-right:5px; vertical-align:middle;"></span>Kota Palangka Raya</span>'
        '<span style="font-size:12px; color:#555;"><span style="display:inline-block; width:12px; height:12px; '
        'background-color:#F07C2A; border-radius:3px; margin-right:5px; vertical-align:middle;"></span>Pertumbuhan positif</span>'
        '<span style="font-size:12px; color:#555;"><span style="display:inline-block; width:12px; height:12px; '
        'background-color:#C0392B; border-radius:3px; margin-right:5px; vertical-align:middle;"></span>Kontraksi (negatif)</span>'
        '</div>',
        unsafe_allow_html=True
    )

st.divider()


# --------------------------------------------
# FOOTER
# --------------------------------------------
# --------------------------------------------
st.markdown(textwrap.dedent("""
<div style="text-align:center; padding:20px 0 8px 0; color:#7A3B10;">
    <p style="margin:0; font-weight:700; font-size:14px;">Badan Pusat Statistik Kota Palangka Raya</p>
    <p style="margin:4px 0 0 0; font-size:12px; color:#A8794F;">Jl. Dr. Wahidin Sudirohusodo No. 5, Kota Palangka Raya, Kalimantan Tengah</p>
    <p style="margin:2px 0 0 0; font-size:12px; color:#A8794F;">© 2026 BPS Kota Palangka Raya. Seluruh hak cipta dilindungi.</p>
</div>
""").strip(), unsafe_allow_html=True)