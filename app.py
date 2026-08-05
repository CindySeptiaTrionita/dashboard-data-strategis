import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, get_all_data
from utils.styling import apply_custom_css
import plotly.graph_objects as go


# WAJIB dipanggil paling awal
init_db()
st.set_page_config(page_title="Dashboard PDRB", layout="wide")
apply_custom_css()

# --------------------------------------------
# BANNER HEADER - full width oranye tua
# --------------------------------------------
st.markdown("""
<div style="background-color:#C85A1A; padding:24px 32px; border-radius:0px; margin-bottom:24px;">
    <h1 style="color:white; font-size:32px; font-weight:800; margin:0;">
        PERTUMBUHAN EKONOMI KOTA PALANGKA RAYA
    </h1>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------
# CSS: Dandanin selectbox jadi kotak kuning rounded
# (taruh SEKALI aja, di luar kolom, sebelum bikin kolom)
# --------------------------------------------
st.markdown("""
<style>
    div[data-testid="stSelectbox"] > div > div {
        background-color: #F9C846 !important;
        border-radius: 12px !important;
        border: 2px solid #C85A1A !important;
    }
    /* Target SEMUA elemen di dalam kotak select, biar pasti kena */
    div[data-testid="stSelectbox"] * {
        font-weight: 700 !important;
        font-size: 16px !important;
        color: #2C3E50 !important;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------
# BARIS FILTER + METRIC CARD
# (bikin kolom SEKALI aja)
# --------------------------------------------
col_filter, col_m1, col_m2, col_m3 = st.columns([1.3, 1, 1, 1])

with col_filter:
    tahun_dipilih = st.selectbox(
        "Tahun",  # ini tetep wajib ditulis (buat aksesibilitas), tapi nggak keliatan
        options=["2024", "2025", "2026"],
        index=2,
        label_visibility="collapsed",
        format_func=lambda x: f"Tahun: {x}"
    )
    triwulan_dipilih = st.selectbox(
        "Triwulan",
        options=["Tw I", "Tw II", "Tw III", "Tw IV"],
        index=0,
        label_visibility="collapsed",
        format_func=lambda x: f"Triwulan: {x}"
    )

# --------------------------------------------
# METRIC CARD
# --------------------------------------------

with col_m1:
    st.markdown("""
    <div style="position:relative; text-align:center; margin-bottom:20px;">
        <div style="background-color:#C85A1A; border-radius:10px; padding:10px; position:relative; z-index:2;">
            <span style="color:white; font-weight:700; font-size:14px;">Q to Q</span>
        </div>
        <div style="background-color:#FDE9A8; border-radius:12px; padding:20px 10px 12px; margin-top:-8px; box-shadow:2px 4px 8px rgba(0,0,0,0.15);">
            <span style="font-size:28px; font-weight:800;">-7,77%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown("""
    <div style="position:relative; text-align:center; margin-bottom:20px;">
        <div style="background-color:#C85A1A; border-radius:10px; padding:10px; position:relative; z-index:2;">
            <span style="color:white; font-weight:700; font-size:14px;">Y on Y</span>
        </div>
        <div style="background-color:#FDE9A8; border-radius:12px; padding:20px 10px 12px; margin-top:-8px; box-shadow:2px 4px 8px rgba(0,0,0,0.15);">
            <span style="font-size:28px; font-weight:800;">5,94%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown("""
    <div style="position:relative; text-align:center; margin-bottom:20px;">
        <div style="background-color:#C85A1A; border-radius:10px; padding:10px; position:relative; z-index:2;">
            <span style="color:white; font-weight:700; font-size:14px;">PDRB Harga Berlaku</span>
        </div>
        <div style="background-color:#FDE9A8; border-radius:12px; padding:20px 10px 12px; margin-top:-8px; box-shadow:2px 4px 8px rgba(0,0,0,0.15);">
            <span style="font-size:24px; font-weight:800;">Rp7.169,5 M</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --------------------------------------------
# TRENDLINE PDRB 2024-2026
# --------------------------------------------

data_tren = pd.DataFrame({
    "Triwulan": ["Tw I 2024", "Tw II 2024", "Tw III 2024", "Tw IV 2024",
                 "Tw I 2025", "Tw II 2025", "Tw III 2025", "Tw IV 2025", "Tw I 2026"],
    "PDRB": [7.48, 5.65, 6.27, 6.97, 5.12, 5.59, 6.06, 5.69, 5.94]
})

st.markdown("""
<h3 style="margin-bottom:2px;">
    PRODUK DOMESTIK REGIONAL BRUTO (PRDB) 2024 - 2026
    <span style="font-style:italic; font-weight:400;">(Y-ON-Y) (persen)</span>
</h3>
""", unsafe_allow_html=True)

fig_tren = go.Figure()
fig_tren = go.Figure()

# --------------------------------------------
# Garis + AREA bayangan di bawah kurva (BARU)
# --------------------------------------------
fig_tren.add_trace(go.Scatter(
    x=data_tren["Triwulan"],
    y=data_tren["PDRB"],
    mode="lines",
    line=dict(color="#B5651D", width=2),
    fill="tozeroy",                          # <-- ini yang bikin ada bayangan di bawah garis
    fillcolor="rgba(197, 106, 45, 0.15)",    # oranye-coklat, transparan 15%
    showlegend=False
))

# --------------------------------------------
# Titik data pakai emoji kardus
# --------------------------------------------
fig_tren.add_trace(go.Scatter(
    x=data_tren["Triwulan"],
    y=data_tren["PDRB"],
    mode="markers+text",
    marker=dict(size=34, symbol="square", color="rgba(0,0,0,0)"),
    text=["📦"] * len(data_tren),
    textposition="middle center",
    textfont=dict(size=22),
    showlegend=False
))

# --------------------------------------------
# Label angka di atas tiap kardus
# --------------------------------------------
fig_tren.add_trace(go.Scatter(
    x=data_tren["Triwulan"],
    y=[v + 0.55 for v in data_tren["PDRB"]],   # jaraknya dikecilin dari 0.9 -> 0.55
    mode="text",
    text=[f"<b>{v}</b>" for v in data_tren["PDRB"]],
    textfont=dict(size=17, color="black"),
    showlegend=False
))

# --------------------------------------------
# Highlight titik TERAKHIR
# --------------------------------------------
titik_terakhir = data_tren.iloc[-1]
fig_tren.add_annotation(
    x=titik_terakhir["Triwulan"],
    y=titik_terakhir["PDRB"] + 0.55,
    text=f"<b>{titik_terakhir['PDRB']}</b>",
    showarrow=False,
    font=dict(size=18, color="black"),
    bgcolor="#F9C846",
    bordercolor="#C85A1A",
    borderwidth=2,
    borderpad=6,
    xanchor="center"
)

# --------------------------------------------
# Layout: range Y dipersempit + margin atas diperbesar
# --------------------------------------------
fig_tren.update_layout(
    plot_bgcolor="#FDF6E9",
    paper_bgcolor="#FDF6E9",
    height=380,
    margin=dict(l=20, r=20, t=60, b=20),   # t (top) dinaikin dari 30 -> 60, biar kardus nggak kepotong
    yaxis=dict(visible=False, range=[3, 9]),  # range dipersempit dari [0,9] -> [3,9]
    xaxis=dict(
        showgrid=False,
        showline=True,
        linecolor="#C85A1A",
        linewidth=2,
        tickfont=dict(size=13, color="#333")
    )
)

st.plotly_chart(fig_tren, width='stretch')

# --------------------------------------------
# FUNGSI - taruh SEMUA definisi fungsi di paling atas
# --------------------------------------------
def buat_bar_chart(data, judul_kolom, judul_grafik):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data["Kategori"],
        y=data["Nilai"],
        text=[f"{v}".replace(".", ",") for v in data["Nilai"]],
        textposition="outside",
        textfont=dict(size=16, color="black"),
        marker_color="#F07C2A",
        showlegend=False
    ))
    fig.update_layout(
        title=dict(text=judul_grafik, font=dict(size=15, color="#C85A1A")),
        plot_bgcolor="#FDF6E9",
        paper_bgcolor="#FDF6E9",
        height=280,
        margin=dict(l=10, r=10, t=50, b=10),
        yaxis=dict(visible=False),
        xaxis=dict(showticklabels=False, showgrid=False)
    )
    return fig


# --------------------------------------------
# Bar CHART PDRB PER SEKTOR
# --------------------------------------------

# --------------------------------------------
# FUNGSI BAR CHART (pastikan ini di ATAS file)
# --------------------------------------------
def buat_bar_chart(data, judul_kolom, judul_grafik):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data["Kategori"],
        y=data["Nilai"],
        text=[f"{v}".replace(".", ",") for v in data["Nilai"]],
        textposition="outside",
        textfont=dict(size=16, color="black"),
        marker_color="#F07C2A",
        showlegend=False
    ))
    fig.update_layout(
        title=dict(text=judul_grafik, font=dict(size=15, color="#C85A1A")),
        plot_bgcolor="#FDF6E9",
        paper_bgcolor="#FDF6E9",
        height=280,
        margin=dict(l=10, r=10, t=50, b=10),
        yaxis=dict(visible=False),
        xaxis=dict(showticklabels=False, showgrid=False)
    )
    return fig


# --------------------------------------------
# FUNGSI BARU: bungkus 1 panel LENGKAP (chart + ikon + pagination)
# Biar nggak nulis kode yang sama 2x buat kiri & kanan
# --------------------------------------------
def render_panel(data_lengkap, judul_grafik, key_halaman, item_per_halaman=5):

    # "Nginget" halaman aktif utk panel INI (pakai key unik)
    if key_halaman not in st.session_state:
        st.session_state[key_halaman] = 1

    total_item = len(data_lengkap)
    total_halaman = -(-total_item // item_per_halaman)
    halaman_aktif = st.session_state[key_halaman]

    awal = (halaman_aktif - 1) * item_per_halaman
    akhir = awal + item_per_halaman
    data_halaman_ini = data_lengkap.iloc[awal:akhir].reset_index(drop=True)

    # Chart
    fig = buat_bar_chart(data_halaman_ini, "Kategori", judul_grafik)
    st.plotly_chart(fig, width='stretch', key=f"chart_{key_halaman}")

    # Ikon
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

    # Tombol pagination
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("⬅️", key=f"prev_{key_halaman}", disabled=(halaman_aktif == 1)):
            st.session_state[key_halaman] -= 1
            st.rerun()
    with col_info:
        st.markdown(
            f"<p style='text-align:center; padding-top:8px; font-size:13px;'>Halaman {halaman_aktif}/{total_halaman}</p>",
            unsafe_allow_html=True
        )
    with col_next:
        if st.button("➡️", key=f"next_{key_halaman}", disabled=(halaman_aktif == total_halaman)):
            st.session_state[key_halaman] += 1
            st.rerun()


# --------------------------------------------
# CSS: garis putus-putus di masing-masing panel
# --------------------------------------------
st.markdown("""
<style>
    .st-key-panel_kiri, .st-key-panel_kanan {
        border: 3px dashed #F07C2A;
        border-radius: 16px;
        padding: 16px;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------
# DATA (ganti sesuai data asli kamu)
# --------------------------------------------
data_lapangan_usaha_full = pd.DataFrame({
    "Kategori": [
        "Administrasi Pemerintahan", "Konstruksi", "Jasa Keuangan",
        "Transportasi dan Pergudangan", "Perdagangan dan Reparasi",
        "Informasi dan Komunikasi", "Jasa Pendidikan", "Real Estate",
        "Pertanian, Kehutanan, Perikanan", "Jasa Kesehatan"
    ],
    "Nilai": [11.33, 8.15, 8.08, 7.09, 4.19, 6.5, 5.8, 5.2, 3.9, 4.5],
    "Ikon": ["🏛️", "🏗️", "💰", "🚚", "🤝", "📡", "🎓", "🏢", "🌾", "🏥"]
}).sort_values("Nilai", ascending=False).reset_index(drop=True)

data_sumber_pertumbuhan_full = pd.DataFrame({
    "Kategori": [
        "Administrasi Pemerintahan", "Lainnya", "Perdagangan dan Reparasi",
        "Transportasi dan Pergudangan", "Jasa Keuangan", "Konstruksi",
        "Real Estate", "Jasa Pendidikan", "Jasa Kesehatan", "Informasi dan Komunikasi"
    ],
    "Nilai": [2.00, 0.94, 0.87, 0.73, 0.72, 0.68, 0.55, 0.48, 0.40, 0.35],
    "Ikon": ["🏛️", "❔", "🤝", "🚚", "💰", "🏗️", "🏢", "🎓", "🏥", "📡"]
}).sort_values("Nilai", ascending=False).reset_index(drop=True)

# --------------------------------------------
# TAMPILKAN 2 PANEL BERSEBELAHAN
# --------------------------------------------
col_kiri, col_kanan = st.columns(2)

with col_kiri:
    with st.container(key="panel_kiri"):
        render_panel(
            data_lapangan_usaha_full,
            "PERTUMBUHAN PDRB MENURUT LAPANGAN USAHA (Y-ON-Y)",
            key_halaman="halaman_kiri"
        )

with col_kanan:
    with st.container(key="panel_kanan"):
        render_panel(
            data_sumber_pertumbuhan_full,
            "SUMBER PERTUMBUHAN PDRB MENURUT LAPANGAN USAHA",
            key_halaman="halaman_kanan"
        )



# def buat_bar_chart(data, judul_kolom, judul_grafik):
#     fig = go.Figure()

#     fig.add_trace(go.Bar(
#         x=data["Kategori"],
#         y=data["Nilai"],
#         text=[f"{v}".replace(".", ",") for v in data["Nilai"]],
#         textposition="outside",
#         textfont=dict(size=16, color="black"),
#         marker_color="#F07C2A",
#         showlegend=False
#     ))

#     fig.update_layout(
#         title=dict(text=judul_grafik, font=dict(size=15, color="#C85A1A")),
#         plot_bgcolor="#FDF6E9",
#         paper_bgcolor="#FDF6E9",
#         height=280,
#         margin=dict(l=10, r=10, t=50, b=10),
#         yaxis=dict(visible=False),
#         xaxis=dict(showticklabels=False, showgrid=False)
#     )
#     return fig


# # --------------------------------------------
# # CSS: garis putus-putus, ditarget LANGSUNG ke masing-masing panel
# # --------------------------------------------
# st.markdown("""
# <style>
#     .st-key-panel_kiri, .st-key-panel_kanan {
#         border: 3px dashed #F07C2A;
#         border-radius: 16px;
#         padding: 16px;
#     }
# </style>
# """, unsafe_allow_html=True)

# col_kiri, col_kanan = st.columns(2)

# with col_kiri:
#     with st.container(key="panel_kiri"):
#         fig_kiri = buat_bar_chart(
#             data_lapangan_usaha,
#             "Kategori",
#             "PERTUMBUHAN PDRB MENURUT LAPANGAN USAHA (Y-ON-Y) (persen)"
#         )
#         st.plotly_chart(fig_kiri, width='stretch')

#         kolom_ikon = st.columns(len(data_lapangan_usaha))
#         for i, kol in enumerate(kolom_ikon):
#             with kol:
#                 st.markdown(f"""
#                 <div style="text-align:center;">
#                     <div style="width:50px; height:50px; border-radius:50%; border:2px solid #1B4F72;
#                                 display:flex; align-items:center; justify-content:center; margin:0 auto; font-size:22px;">
#                         {data_lapangan_usaha['Ikon'][i]}
#                     </div>
#                     <p style="font-size:11px; margin-top:6px;">{data_lapangan_usaha['Kategori'][i].replace(chr(10), '<br>')}</p>
#                 </div>
#                 """, unsafe_allow_html=True)

# with col_kanan:
#     with st.container(key="panel_kanan"):
#         fig_kanan = buat_bar_chart(
#             data_sumber_pertumbuhan,
#             "Kategori",
#             "SUMBER PERTUMBUHAN PDRB MENURUT LAPANGAN USAHA (persen)"
#         )
#         st.plotly_chart(fig_kanan, width='stretch')

#         kolom_ikon2 = st.columns(len(data_sumber_pertumbuhan))
#         for i, kol in enumerate(kolom_ikon2):
#             with kol:
#                 st.markdown(f"""
#                 <div style="text-align:center;">
#                     <div style="width:50px; height:50px; border-radius:50%; border:2px solid #1B4F72;
#                                 display:flex; align-items:center; justify-content:center; margin:0 auto; font-size:22px;">
#                         {data_sumber_pertumbuhan['Ikon'][i]}
#                     </div>
#                     <p style="font-size:11px; margin-top:6px;">{data_sumber_pertumbuhan['Kategori'][i].replace(chr(10), '<br>')}</p>
#                 </div>
#                 """, unsafe_allow_html=True)