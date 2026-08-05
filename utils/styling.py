import streamlit as st

def apply_custom_css():
    """CSS umum untuk seluruh halaman - background, warna heading, dst"""
    st.markdown("""
    <style>
        .stApp { background-color: #FDF6E9; }
        h3 { color: #C85A1A !important; font-weight: 700 !important; }
        hr { border-top: 3px dashed #F07C2A !important; }
    </style>
    """, unsafe_allow_html=True)