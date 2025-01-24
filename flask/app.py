import matplotlib
matplotlib.use('Agg')  # Menggunakan backend non-GUI untuk Matplotlib agar bisa berjalan di server tanpa tampilan grafis.

from flask import Flask, request, jsonify
import pandas as pd
import matplotlib.pyplot as plt
import io, base64
from flask_cors import CORS
import logging

# Inisialisasi Flask dan aktifkan CORS untuk menerima permintaan dari domain yang ditentukan.
app = Flask(__name__)
CORS(app)  # Mengizinkan semua origin untuk CORS. Bisa dibatasi untuk domain tertentu jika diperlukan.

# Mengonfigurasi logging untuk mencatat informasi dan kesalahan
logging.basicConfig(level=logging.INFO)

@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    if request.method == 'GET':
        # Jika permintaan menggunakan metode GET, kirimkan respons default atau pesan
        logging.info("GET request received. Returning default message.")
        return jsonify({"message": "This API endpoint only accepts POST requests for file uploads."}), 405

    # Jika metode POST, proses file upload
    if 'file' not in request.files:
        logging.error("No file uploaded.")
        return jsonify({"error": "No file uploaded"}), 400  # Jika tidak ada file yang di-upload, kirimkan error

    file = request.files['file']
    
    # Memeriksa apakah file yang di-upload berformat CSV
    if not file.filename.endswith('.csv'):
        logging.error("Invalid file format. Expected a CSV file.")
        return jsonify({"error": "Invalid file format. Please upload a CSV file."}), 400  # File bukan CSV

    try:
        # Membaca file CSV menjadi DataFrame
        df = pd.read_csv(file)

        # Memeriksa apakah semua kolom yang dibutuhkan ada dalam DataFrame
        required_columns = {'tanggal', 'produk', 'total_penjualan', 'jumlah_terjual', 'harga'}
        if not required_columns.issubset(df.columns):
            logging.error(f"Missing required columns. Expected columns: {required_columns}")
            return jsonify({"error": f"Missing columns. Required columns: {required_columns}"}), 400  # Kolom yang dibutuhkan tidak ada

        # Mengonversi kolom 'tanggal' menjadi format datetime
        df['tanggal'] = pd.to_datetime(df['tanggal'], format='%Y-%m-%d', errors='coerce')
        if df['tanggal'].isnull().any():  # Memeriksa jika ada tanggal yang tidak valid
            logging.error("Some rows have invalid dates in the 'tanggal' column.")
            return jsonify({"error": "Some rows have invalid dates in the 'tanggal' column. Please ensure the date format is 'YYYY-MM-DD'."}), 400
        
        # Menghapus baris dengan tanggal yang invalid
        df = df.dropna(subset=['tanggal'])

        # Menghapus duplikasi berdasarkan 'tanggal' dan 'produk' untuk memastikan data unik
        df = df.drop_duplicates(subset=['tanggal', 'produk'])

        # Menghitung total penjualan per produk
        total_sales = df.groupby('produk')['total_penjualan'].sum().to_dict()

        # Menghitung tren penjualan berdasarkan tanggal dan produk
        trend_sales = df.groupby(['tanggal', 'produk']).agg(
            total_penjualan=('total_penjualan', 'sum'),
            jumlah_terjual=('jumlah_terjual', 'sum'),
            harga=('harga', 'mean')  # Menghitung harga rata-rata per produk
        ).reset_index()

        trend_data = trend_sales.to_dict(orient='records')  # Mengubah data tren menjadi format dictionary

        # Menampilkan data untuk debugging
        logging.info(f"Total Sales: {total_sales}")
        logging.info(f"Trend Data: {trend_data}")

        # Membuat grafik tren penjualan
        plt.figure(figsize=(10, 5))
        plt.plot(trend_sales['tanggal'], trend_sales['total_penjualan'], marker='o', linestyle='-', color='b')
        plt.title('Tren Penjualan')
        plt.xlabel('Tanggal')
        plt.ylabel('Total Penjualan')
        plt.grid(True)

        # Menyimpan grafik ke buffer dalam format PNG
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')  # bbox_inches='tight' untuk mengurangi ruang kosong pada gambar
        img.seek(0)
        graph_url = base64.b64encode(img.getvalue()).decode()  # Mengubah gambar ke format base64 untuk dikirim via JSON

        # Mengembalikan respons JSON dengan total penjualan, data tren, dan grafik
        return jsonify({
            "total_sales": total_sales,
            "trend": trend_data,
            "trend_graph": f"data:image/png;base64,{graph_url}"  # Menyertakan grafik dalam format base64
        })
    
    except pd.errors.EmptyDataError:
        # Menangani error jika file CSV kosong
        logging.error("The uploaded CSV file is empty.")
        return jsonify({"error": "The uploaded CSV file is empty."}), 400
    except KeyError as e:
        # Menangani error jika ada kolom yang hilang
        logging.error(f"Missing required column: {e}")
        return jsonify({"error": f"Missing required column: {e}"}), 400
    except Exception as e:
        # Menangani error umum lainnya
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Menjalankan aplikasi Flask
    app.run(debug=True)
