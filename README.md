# Dashboard PDRB Kota Palangka Raya

Dashboard interaktif untuk menampilkan data Produk Domestik Regional Bruto (PDRB)
Kota Palangka Raya, dilengkapi popup fenomena dan peta tematik.

## Struktur Folder

Dashboard_PDRB/

│

├── app.py # Halaman utama (dashboard publik)

│

├── pages/ # Halaman tambahan (dibaca otomatis oleh Streamlit)

│ └── 1_🔒_Admin.py # Halaman khusus admin (input data, pakai password)

│

├── database.py # Fungsi untuk membaca/menyimpan/mengubah data

├── data_pdrb.db # File database SQLite (dibuat otomatis saat app dijalankan)

│

├── utils/ # Kumpulan fungsi pembantu

│ ├── styling.py # CSS custom untuk tampilan (tema oranye BPS)

│ └── helpers.py # Fungsi kecil lainnya (format angka, dll)

│

├── assets/ # File gambar & data statis

│ ├── logo_bps.png

│ └── kalteng.geojson # Data batas wilayah untuk peta tematik

│

├── requirements.txt # Daftar library yang dibutuhkan

└── README.md # File ini

## Cara Menjalankan

1. Install semua library yang dibutuhkan:

```bash
   pip install -r requirements.txt
```

2. Jalankan dashboard:

```bash
   streamlit run app.py
```

3. Dashboard akan otomatis terbuka di browser.

## Halaman Admin

- Buka menu **Admin** di sidebar kiri
- Masukkan password untuk mengakses fitur edit/tambah/hapus data
- Password saat ini diatur langsung di dalam file `pages/1_🔒_Admin.py`

## Sumber Data

Data bersumber dari publikasi Badan Pusat Statistik (BPS) Kota Palangka Raya,
rilis Pertumbuhan Ekonomi Triwulan I - 2026.
