# ==========================================
# 🌐 KONFIGURASI PUBLIKASI (SITUS & MONETISASI)
# Isi nilai di bawah setelah kamu punya akunnya.
# File ini AMAN di-push (tidak ada kredensial, hanya ID/URL publik).
# ==========================================

# --- Identitas situs ---
SITE_URL = "https://dadungdadung87-cloud.github.io/SAHAM-SCREENING/"
SITE_NAME = "AlgoTrade Screener IHSG"
SITE_DESC = "Screener saham IHSG gratis: detektor akumulasi bandar, anomali volume, dan radar BSJP — diperbarui otomatis setiap hari bursa."

# --- App Streamlit (tujuan tombol CTA) ---
APP_URL = "https://minhaz0305.streamlit.app/"

# --- Google AdSense ---
# 1. Daftar di https://adsense.google.com, tambahkan situs, tunggu disetujui.
# 2. Salin "client" ca-pub-XXXXXXXXXXXXXXXX dan ganti di sini.
# 3. (Opsional) salin ID slot iklan per posisi bila mengatur tampilan di dashboard.
ADSENSE_CLIENT = ""          # contoh: "ca-pub-1234567890123456" — kosong = skrip iklan TIDAK dimuat
ADSENSE_SLOT_ATAS = ""       # ID unit iklan puncak artikel (opsional)
ADSENSE_SLOT_TENGAH = ""     # ID unit iklan tengah artikel (opsional)
ADSENSE_SLOT_BAWAH = ""      # ID unit iklan bawah artikel (opsional)

# --- Affiliate broker (ganti dengan link referral kamu sendiri) ---
BROKER_REF = [
    {"nama": "Stockbit", "url": "https://stockbit.com/", "deskripsi": "Watchlist, broker summary & komunitas trader."},
    {"nama": "Ajaib", "url": "https://ajaib.co.id/", "deskripsi": "Trading saham & reksadana, registrasi cepat."},
]

# --- Telegram (opsional, tombol komunitas) ---
TELEGRAM_URL = ""            # contoh: "https://t.me/namachannel" — kosong = tombol disembunyikan

# --- Kata kunci SEO ---
SEO_KEYWORDS = "screener saham, IHSG, analisa saham hari ini, akumulasi bandar, radar BSJP, saham paling aktif, deteksi bandar, stock screening Indonesia"
