import os
import streamlit as st
from utils.styling import apply_custom_css

apply_custom_css()

# --------------------------------------------
# KONFIGURASI
# --------------------------------------------
PATH_PANDUAN = "assets/panduan.pdf"
NAMA_FILE_UNDUH = "Panduan Dashboard PDRB.pdf"

st.title("\U0001F4D8 Buku Panduan")
st.markdown(
    "Unduh buku panduan penggunaan Dashboard PDRB ini dalam format PDF."
)

if not os.path.exists(PATH_PANDUAN):
    st.error(
        f"File panduan tidak ditemukan di `{PATH_PANDUAN}`. "
        "Pastikan file PDF sudah diletakkan di folder tersebut."
    )
else:
    ukuran_kb = os.path.getsize(PATH_PANDUAN) / 1024
    st.caption(f"Ukuran file: {ukuran_kb:,.0f} KB")

    with open(PATH_PANDUAN, "rb") as f:
        data_pdf = f.read()

    st.download_button(
        label="\u2B07\uFE0F Download Buku Panduan (PDF)",
        data=data_pdf,
        file_name=NAMA_FILE_UNDUH,
        mime="application/pdf",
    )

    st.divider()
    st.subheader("Pratinjau")
    st.caption("Kalau pratinjau di bawah tidak muncul (tergantung browser), langsung unduh saja filenya di atas.")

    import base64
    base64_pdf = base64.b64encode(data_pdf).decode("utf-8")
    st.markdown(
        f"""
        <iframe src="data:application/pdf;base64,{base64_pdf}"
                width="100%" height="600" style="border:1px solid #ddd; border-radius:8px;">
        </iframe>
        """,
        unsafe_allow_html=True,
    )
