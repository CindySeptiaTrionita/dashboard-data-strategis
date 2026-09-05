import streamlit as st


def apply_custom_css():
    """CSS global untuk tema dashboard PDRB (oranye/krem ala BPS)."""
    st.markdown("""
    <style>
        /* Background utama */
        .stApp {
            background-color: #FDF6E9;
        }

        /* Rapikan padding bawaan container utama.
           padding-left/right SENGAJA di-set eksplisit (bukan dibiarkan
           default bawaan Streamlit) supaya nilainya pasti dan bisa
           ditiru persis oleh pembungkus teks di banner header, sehingga
           teks judul banner sejajar dengan tepi konten di bawahnya. */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 1300px;
        }

        /* Baris "judul grafik + tombol sumber data" yang dipasang di
           atas tiap grafik/tabel. */
        .baris-judul-grafik {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 4px;
        }
        .baris-judul-grafik h3, .baris-judul-grafik h5 {
            margin: 0 !important;
        }
        div[class*="st-key-tombol_sumber_"] div[data-testid="stButton"] > button,
        div[class*="st-key-tombol_sumber_"] a[data-testid="stBaseLinkButton"] {
            background-color: #FBE4A6;
            border: 2px solid #C85A1A;
            border-radius: 50px;
            color: #7A3B10;
            font-weight: 700;
            font-size: 12px;
            width: auto;
            height: auto;
            padding: 6px 16px;
            white-space: nowrap;
        }
        div[class*="st-key-tombol_sumber_"] a[data-testid="stBaseLinkButton"]:hover {
            background-color: #F07C2A;
            color: white;
        }

        /* Sembunyikan menu & footer bawaan streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* Judul section */
        h3 {
            color: #C85A1A;
        }

        /* Divider lebih tipis & senada tema */
        hr {
            border-top: 1px solid #E8C79A;
        }

        /* Tombol pagination (prev/next) bulat & senada tema */
        div[data-testid="stButton"] > button {
            background-color: #F9C846;
            border: 2px solid #C85A1A;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            font-weight: 700;
        }
        div[data-testid="stButton"] > button:hover {
            background-color: #F07C2A;
            border-color: #C85A1A;
            color: white;
        }
        div[data-testid="stButton"] > button:disabled {
            background-color: #EFE3C8;
            border-color: #D9C39A;
            opacity: 0.6;
        }

        /* Card panel kiri/kanan (dipakai lewat st.container(key=...)) */
        .st-key-panel_kiri, .st-key-panel_kanan {
            background-color: #FFFFFF;
        }
    </style>
    """, unsafe_allow_html=True)