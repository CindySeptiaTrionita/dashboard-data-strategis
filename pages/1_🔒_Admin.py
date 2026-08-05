# ==========================================
# HALAMAN ADMIN - Hanya bisa diakses dengan password
# ==========================================

import streamlit as st
from database import init_db, get_all_data, update_data, tambah_kategori_baru, hapus_kategori

init_db()

st.title("🔒 Halaman Admin")

# --------------------------------------------
# PINTU KUNCI: cek password dulu
# --------------------------------------------
# GANTI password ini sesuka kamu!
PASSWORD_ADMIN = "palangkaraya2026"

# session_state itu kayak "memori sementara" - nginget status login
if "sudah_login" not in st.session_state:
    st.session_state.sudah_login = False

if not st.session_state.sudah_login:
    st.warning("Halaman ini khusus admin. Masukkan password untuk lanjut.")
    password_input = st.text_input("Password", type="password")

    if st.button("Masuk"):
        if password_input == PASSWORD_ADMIN:
            st.session_state.sudah_login = True
            st.rerun()  # muat ulang halaman biar langsung masuk
        else:
            st.error("Password salah!")

else:
    # --------------------------------------------
    # ISI HALAMAN ADMIN (baru muncul kalau password benar)
    # --------------------------------------------
    st.success("Berhasil login sebagai admin ✅")

    if st.button("Keluar (Logout)"):
        st.session_state.sudah_login = False
        st.rerun()

    st.divider()
    st.markdown("### Data Saat Ini")
    data_sekarang = get_all_data()
    st.dataframe(data_sekarang, width='stretch')

    st.divider()
    st.markdown("### ✏️ Edit Data yang Sudah Ada")

    kategori_dipilih = st.selectbox("Pilih kategori", data_sekarang["kategori"])
    baris = data_sekarang[data_sekarang["kategori"] == kategori_dipilih].iloc[0]

    pertumbuhan_baru = st.number_input("Nilai pertumbuhan (%)", value=float(baris["pertumbuhan"]))
    fenomena_baru = st.text_area("Teks fenomena", value=baris["fenomena"], height=120)

    if st.button("Simpan Perubahan"):
        update_data(kategori_dipilih, pertumbuhan_baru, fenomena_baru)
        st.success(f"Data '{kategori_dipilih}' berhasil diupdate!")
        st.rerun()

    st.divider()
    st.markdown("### ➕ Tambah Kategori Baru")

    with st.form("form_tambah"):
        kategori_baru = st.text_input("Nama kategori baru")
        pertumbuhan_kategori_baru = st.number_input("Nilai pertumbuhan (%)", key="new_val")
        fenomena_kategori_baru = st.text_area("Teks fenomena", key="new_text")
        submit = st.form_submit_button("Tambahkan")

        if submit and kategori_baru:
            tambah_kategori_baru(kategori_baru, pertumbuhan_kategori_baru, fenomena_kategori_baru)
            st.success(f"Kategori '{kategori_baru}' berhasil ditambahkan!")
            st.rerun()

    st.divider()
    st.markdown("### 🗑️ Hapus Kategori")

    kategori_dihapus = st.selectbox("Pilih kategori yang mau dihapus", data_sekarang["kategori"], key="hapus")
    if st.button("Hapus Kategori Ini", type="primary"):
        hapus_kategori(kategori_dihapus)
        st.success(f"Kategori '{kategori_dihapus}' berhasil dihapus!")
        st.rerun()