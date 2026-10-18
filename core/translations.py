"""Kamus terjemahan EN → ID untuk locale/id/LC_MESSAGES/django.po.

Source string (msgid) ditulis berbahasa Inggris? TIDAK — konvensi proyek ini:
msgid = teks asli di kode (banyak berbahasa Indonesia karena situs utamanya ID),
msgstr = padanan untuk bahasa `id`. Karena LANGUAGE_CODE='id', Django memakai
katalog ini untuk bahasa default; bahasa `en` jatuh kembali ke msgid.

Kunci = string di kode/templates, nilai = hasil terjemahan untuk locale 'id'.
Karena msgid sudah hampir seluruhnya bahasa Indonesia, nilai umumnya sama —
entri tetap dicantumkan agar katalog lengkap & mudah diaudit.
"""

TRANSLATIONS_ID = {
    # ---- Umum / navigasi ----
    'Bahasa Indonesia': 'Bahasa Indonesia',
    'English': 'English',
    'Beranda': 'Beranda',
    'Tiket Bus': 'Tiket Bus',
    'Rental Mobil': 'Rental Mobil',
    'Cek Booking': 'Cek Booking',
    'Tentang': 'Tentang',
    'Kontak': 'Kontak',
    'Buka navigasi': 'Buka navigasi',
    'Pilih bahasa': 'Pilih bahasa',
    'Tutup': 'Tutup',
    'Pesan tiket bus antar kota dan sewa mobil dengan mudah, aman, dan harga terbaik. Pilih kursi, bayar via transfer/QRIS, e-tiket instan.':
        'Pesan tiket bus antar kota dan sewa mobil dengan mudah, aman, dan harga terbaik. Pilih kursi, bayar via transfer/QRIS, e-tiket instan.',
    'Pesan tiket bus antar kota dan sewa mobil dengan mudah, aman, dan harga terbaik.':
        'Pesan tiket bus antar kota dan sewa mobil dengan mudah, aman, dan harga terbaik.',

    # ---- Footer ----
    'Melayani perjalanan bus antar kota & penyewaan mobil di Jawa Timur dan sekitarnya sejak 2015. Aman, nyaman, tepat waktu.':
        'Melayani perjalanan bus antar kota & penyewaan mobil di Jawa Timur dan sekitarnya sejak 2015. Aman, nyaman, tepat waktu.',
    'Perusahaan': 'Perusahaan',
    'Tentang Kami': 'Tentang Kami',
    'Rute Populer': 'Rute Populer',
    'Semua rute…': 'Semua rute…',
    'Pembayaran: Transfer Bank & QRIS': 'Pembayaran: Transfer Bank & QRIS',
    'Semua hak dilindungi.': 'Semua hak dilindungi.',
    'Dibangun dengan Django & Bootstrap': 'Dibangun dengan Django & Bootstrap',

    # ---- Beranda ----
    'Tiket Bus Online & Rental Mobil': 'Tiket Bus Online & Rental Mobil',
    'Pesan tiket bus antar kota pilih kursi sendiri, atau sewa mobil harian dengan sopir. Pembayaran transfer & QRIS, konfirmasi cepat via WhatsApp.':
        'Pesan tiket bus antar kota pilih kursi sendiri, atau sewa mobil harian dengan sopir. Pembayaran transfer & QRIS, konfirmasi cepat via WhatsApp.',
    '#1 Travel & Rental di Jawa Timur': '#1 Travel & Rental di Jawa Timur',
    'Perjalanan Nyaman,': 'Perjalanan Nyaman,',
    'Harga Bersahabat': 'Harga Bersahabat',
    'Pesan tiket bus antar kota & rental mobil dalam satu tempat. Pilih kursi favoritmu, bayar via transfer atau QRIS, e-tiket langsung di tangan.':
        'Pesan tiket bus antar kota & rental mobil dalam satu tempat. Pilih kursi favoritmu, bayar via transfer atau QRIS, e-tiket langsung di tangan.',
    'Dari': 'Dari',
    'Ke': 'Ke',
    'Tanggal': 'Tanggal',
    'Org': 'Org',
    'Cari Bus': 'Cari Bus',
    'Tukar asal & tujuan': 'Tukar asal & tujuan',
    'Butuh mobil? Lihat katalog rental →': 'Butuh mobil? Lihat katalog rental →',
    'Pilih Kursi Sendiri': 'Pilih Kursi Sendiri',
    'Denah kursi interaktif — dapatkan tempat paling nyaman.':
        'Denah kursi interaktif — dapatkan tempat paling nyaman.',
    'Pembayaran Aman': 'Pembayaran Aman',
    'Transfer bank atau scan QRIS dari e-wallet apa pun.':
        'Transfer bank atau scan QRIS dari e-wallet apa pun.',
    'E-Tiket Instan': 'E-Tiket Instan',
    'Kode booking dikirim setelah pembayaran terverifikasi.':
        'Kode booking dikirim setelah pembayaran terverifikasi.',
    'CS Ramah 24/7': 'CS Ramah 24/7',
    'Tim siap membantu via WhatsApp setiap hari.': 'Tim siap membantu via WhatsApp setiap hari.',
    'Destinasi Favorit': 'Destinasi Favorit',
    'Rute Bus Populer': 'Rute Bus Populer',
    'Lihat semua': 'Lihat semua',
    'jadwal/hari': 'jadwal/hari',
    'mulai': 'mulai',
    'Armada Kami': 'Armada Kami',
    'Pilih Kelas Sesuai Budget': 'Pilih Kelas Sesuai Budget',
    'Semua armada dirawat rutin dan diperiksa sebelum berangkat. Pilih kelas yang paling pas untuk perjalananmu.':
        'Semua armada dirawat rutin dan diperiksa sebelum berangkat. Pilih kelas yang paling pas untuk perjalananmu.',
    'Ekonomi': 'Ekonomi',
    '2-2, AC, harga hemat': '2-2, AC, harga hemat',
    '2-2, pendingin sejuk': '2-2, pendingin sejuk',
    'Eksekutif': 'Eksekutif',
    '2-1, reclining seat': '2-1, reclining seat',
    '1-1, bisa tidur penuh': '1-1, bisa tidur penuh',
    'Sewa Mobil untuk Perjalanan Fleksibel': 'Sewa Mobil untuk Perjalanan Fleksibel',
    'Semua mobil': 'Semua mobil',
    'Mudah & Cepat': 'Mudah & Cepat',
    '4 Langkah Menuju Perjalanan': '4 Langkah Menuju Perjalanan',
    'Cari jadwal': 'Cari jadwal',
    'Tentukan kota asal, tujuan, dan tanggal.': 'Tentukan kota asal, tujuan, dan tanggal.',
    'Pilih kursi': 'Pilih kursi',
    'Ambil kursi favorit lewat denah interaktif.': 'Ambil kursi favorit lewat denah interaktif.',
    'Isi data': 'Isi data',
    'Masukkan kontak, dapatkan kode booking.': 'Masukkan kontak, dapatkan kode booking.',
    'Bayar & berangkat': 'Bayar & berangkat',
    'Transfer/QRIS, unggah bukti, tunjukkan e-tiket.': 'Transfer/QRIS, unggah bukti, tunjukkan e-tiket.',
    'Siap Berangkat Hari Ini?': 'Siap Berangkat Hari Ini?',
    'Kursi terbatas untuk jadwal populer — amankan tempatmu sekarang.':
        'Kursi terbatas untuk jadwal populer — amankan tempatmu sekarang.',
    'Pesan Tiket Sekarang': 'Pesan Tiket Sekarang',

    # ---- Cari jadwal ----
    'Cari & Pesan Tiket Bus Online': 'Cari & Pesan Tiket Bus Online',
    'Cari jadwal bus antar kota, bandingkan harga & kelas, pilih kursi favoritmu.':
        'Cari jadwal bus antar kota, bandingkan harga & kelas, pilih kursi favoritmu.',
    'Tanpa antre — pilih kursi sendiri, bayar transfer/QRIS.':
        'Tanpa antre — pilih kursi sendiri, bayar transfer/QRIS.',
    'Kota Asal': 'Kota Asal',
    'Kota Tujuan': 'Kota Tujuan',
    'Penumpang': 'Penumpang',
    'Cari': 'Cari',
    'jadwal ditemukan': 'jadwal ditemukan',
    'Belum ada jadwal untuk rute & tanggal ini': 'Belum ada jadwal untuk rute & tanggal ini',
    'Coba tanggal lain, atau hubungi kami via WhatsApp untuk charter khusus.':
        'Coba tanggal lain, atau hubungi kami via WhatsApp untuk charter khusus.',
    'Tanya CS': 'Tanya CS',
    'Rute paling dicari': 'Rute paling dicari',

    # ---- Kartu jadwal ----
    'hari': 'hari',
    'Mulai dari': 'Mulai dari',
    'kursi': 'kursi',
    'kursi tersedia': 'kursi tersedia',
    'sisa': 'sisa',
    'Pilih Kursi': 'Pilih Kursi',

    # ---- Pilih kursi ----
    'Denah Kursi': 'Denah Kursi',
    'Tersedia': 'Tersedia',
    'Terisi': 'Terisi',
    'Pilihanmu': 'Pilihanmu',
    'Sopir': 'Sopir',
    'Kursi %(label)s': 'Kursi %(label)s',
    '1 kursi sudah terisi pada tanggal ini.': '1 kursi sudah terisi pada tanggal ini.',
    '%(taken_count)s kursi sudah terisi pada tanggal ini.': '%(taken_count)s kursi sudah terisi pada tanggal ini.',
    'Ringkasan': 'Ringkasan',
    'Kursi dipilih': 'Kursi dipilih',
    'Nomor kursi': 'Nomor kursi',
    'Total': 'Total',
    'Lanjut Isi Data': 'Lanjut Isi Data',
    'Kursi dikunci %(h)s jam setelah booking dibuat.': 'Kursi dikunci %(h)s jam setelah booking dibuat.',

    # ---- Data pemesan ----
    'Data Pemesan': 'Data Pemesan',
    'Hampir selesai! Periksa ringkasan & lengkapi kontakmu.':
        'Hampir selesai! Periksa ringkasan & lengkapi kontakmu.',
    'Informasi Kontak': 'Informasi Kontak',
    'Buat Booking': 'Buat Booking',
    'Kursi langsung dikunci untuk Anda. Selesaikan pembayaran dalam %(h)s jam.':
        'Kursi langsung dikunci untuk Anda. Selesaikan pembayaran dalam %(h)s jam.',
    'Detail Perjalanan': 'Detail Perjalanan',
    'Harga/kursi': 'Harga/kursi',
    'Jumlah kursi': 'Jumlah kursi',
    'Total Bayar': 'Total Bayar',

    # ---- Detail booking ----
    'Booking': 'Booking',
    'Detail Booking': 'Detail Booking',
    'Simpan kode booking & screenshot halaman ini.': 'Simpan kode booking & screenshot halaman ini.',
    'Booking Berhasil Dibuat!': 'Booking Berhasil Dibuat!',
    'Kursi Anda dikunci selama %(h)s jam. Selesaikan pembayaran di bawah ini agar booking tidak kedaluwarsa.':
        'Kursi Anda dikunci selama %(h)s jam. Selesaikan pembayaran di bawah ini agar booking tidak kedaluwarsa.',
    'Kode Booking': 'Kode Booking',
    'Nama Pemesan': 'Nama Pemesan',
    'No. WhatsApp': 'No. WhatsApp',
    'Rute': 'Rute',
    'Keberangkatan': 'Keberangkatan',
    'Bus': 'Bus',
    'Tunjukkan kode booking & kartu identitas ke petugas saat Check-in (datang 30 menit sebelum berangkat).':
        'Tunjukkan kode booking & kartu identitas ke petugas saat Check-in (datang 30 menit sebelum berangkat).',
    'Unggah Bukti Pembayaran': 'Unggah Bukti Pembayaran',
    'Bukti sudah diterima': 'Bukti sudah diterima',
    'Metode:': 'Metode:',
    'menunggu verifikasi admin (maks. 15 menit).': 'menunggu verifikasi admin (maks. 15 menit).',
    'Metode yang digunakan': 'Metode yang digunakan',
    'Bukti pembayaran': 'Bukti pembayaran',
    'Format JPG/PNG, maks. 5 MB. Screenshot m-banking atau foto struk/QRIS.':
        'Format JPG/PNG, maks. 5 MB. Screenshot m-banking atau foto struk/QRIS.',
    'Kirim Bukti Pembayaran': 'Kirim Bukti Pembayaran',
    'Batas waktu pembayaran terlewat, booking ini kedaluwarsa. Silakan buat booking baru.':
        'Batas waktu pembayaran terlewat, booking ini kedaluwarsa. Silakan buat booking baru.',
    'Cari jadwal lagi': 'Cari jadwal lagi',
    'Pembayaran Terverifikasi': 'Pembayaran Terverifikasi',
    'E-tiket aktif. Sampai jumpa di pool!': 'E-tiket aktif. Sampai jumpa di pool!',
    'Booking ini sudah tidak aktif.': 'Booking ini sudah tidak aktif.',
    'Pesan tiket lain': 'Pesan tiket lain',
    'Butuh Bantuan?': 'Butuh Bantuan?',
    'Sebutkan kode booking Anda saat menghubungi CS:': 'Sebutkan kode booking Anda saat menghubungi CS:',
    'Chat WhatsApp': 'Chat WhatsApp',

    # ---- Cek booking ----
    'Cek Status Booking': 'Cek Status Booking',
    'Masukkan kode booking untuk melihat status & e-tiket.':
        'Masukkan kode booking untuk melihat status & e-tiket.',
    'Booking dengan kode <strong>%(code)s</strong> tidak ditemukan. Periksa kembali penulisannya.':
        'Booking dengan kode <strong>%(code)s</strong> tidak ditemukan. Periksa kembali penulisannya.',
    'Lihat Status': 'Lihat Status',
    'Kode booking terlihat seperti: NT-A7K2QP': 'Kode booking terlihat seperti: NT-A7K2QP',

    # ---- Halaman rute (SEO) ----
    'Tiket Bus %(origin)s ke %(dest)s — Jadwal & Harga': 'Tiket Bus %(origin)s ke %(dest)s — Jadwal & Harga',
    'Tiket Bus %(origin)s → %(dest)s': 'Tiket Bus %(origin)s → %(dest)s',
    'Jadwal bus %(origin)s–%(dest)s hari ini: keberangkatan, durasi, kelas armada, dan harga tiket mulai dari harga termurah. Pesan online, pilih kursi sendiri.':
        'Jadwal bus %(origin)s–%(dest)s hari ini: keberangkatan, durasi, kelas armada, dan harga tiket mulai dari harga termurah. Pesan online, pilih kursi sendiri.',
    'Bus %(origin)s ke %(dest)s': 'Bus %(origin)s ke %(dest)s',
    'Beranda': 'Beranda',
    'keberangkatan setiap hari': 'keberangkatan setiap hari',
    'Jadwal Hari Ini & Setelahnya': 'Jadwal Hari Ini & Setelahnya',
    'Jadwal untuk rute ini belum tersedia. Hubungi kami untuk info terbaru.':
        'Jadwal untuk rute ini belum tersedia. Hubungi kami untuk info terbaru.',
    'Cek Kursi Tersedia': 'Cek Kursi Tersedia',
    'Jumlah kursi berubah setiap saat. Pilih tanggal untuk melihat kursi yang masih kosong:':
        'Jumlah kursi berubah setiap saat. Pilih tanggal untuk melihat kursi yang masih kosong:',
    'Lihat Kursi Sekarang': 'Lihat Kursi Sekarang',
    'Pembatalan gratis sebelum pembayaran.': 'Pembatalan gratis sebelum pembayaran.',
    'E-tiket digital, tanpa cetak.': 'E-tiket digital, tanpa cetak.',
    'Bisa bayar lewat QRIS.': 'Bisa bayar lewat QRIS.',

    # ---- Tentang & kontak ----
    'Tentang Kami': 'Tentang Kami',
    'Tentang Nusantara Trans': 'Tentang Nusantara Trans',
    'Menghubungkan kota-kota di Jawa Timur & Bali sejak 2015':
        'Menghubungkan kota-kota di Jawa Timur & Bali sejak 2015',
    'Cerita Kami': 'Cerita Kami',
    'Berawal dari Satu Bus, Kini Layani 7+ Kota': 'Berawal dari Satu Bus, Kini Layani 7+ Kota',
    'Nusantara Trans dimulai tahun 2015 dari satu bus ekonomi rute Jember–Surabaya. Dukungan pelanggan membuat kami bertumbuh: kini kami mengoperasikan armada bus berbagai kelas dan layanan rental mobil dengan sopir berpengalaman.':
        'Nusantara Trans dimulai tahun 2015 dari satu bus ekonomi rute Jember–Surabaya. Dukungan pelanggan membuat kami bertumbuh: kini kami mengoperasikan armada bus berbagai kelas dan layanan rental mobil dengan sopir berpengalaman.',
    'Kami percaya perjalanan darat seharusnya mudah dipesan: pilih kursi sendiri, bayar dari mana saja, dan dapatkan e-tiket tanpa antre di loket.':
        'Kami percaya perjalanan darat seharusnya mudah dipesan: pilih kursi sendiri, bayar dari mana saja, dan dapatkan e-tiket tanpa antre di loket.',
    'Pesan Tiket': 'Pesan Tiket',
    'Hubungi Kami': 'Hubungi Kami',
    'Kota Terlayani': 'Kota Terlayani',
    'Rute Harian': 'Rute Harian',
    'Armada Bus': 'Armada Bus',
    'Mobil Rental': 'Mobil Rental',
    'Nilai Kami': 'Nilai Kami',
    'Tepat Waktu': 'Tepat Waktu',
    'Berangkat & tiba sesuai jadwal adalah janji utama kami.':
        'Berangkat & tiba sesuai jadwal adalah janji utama kami.',
    'Ramah Pelanggan': 'Ramah Pelanggan',
    'Sopir dan CS terlatih membantu dengan sepenuh hati.':
        'Sopir dan CS terlatih membantu dengan sepenuh hati.',
    'Armada Terawat': 'Armada Terawat',
    'Servis berkala & pemeriksaan sebelum setiap keberangkatan.':
        'Servis berkala & pemeriksaan sebelum setiap keberangkatan.',
    'Ada pertanyaan sebelum / sesudah memesan? Tim kami siap membantu.':
        'Ada pertanyaan sebelum / sesudah memesan? Tim kami siap membantu.',
    'WhatsApp': 'WhatsApp',
    'Tercepat untuk konfirmasi & bantuan booking.': 'Tercepat untuk konfirmasi & bantuan booking.',
    'Email': 'Email',
    'Untuk kerja sama, charter, & feedback.': 'Untuk kerja sama, charter, & feedback.',
    'Kantor Pusat': 'Kantor Pusat',
    'Agen & Pool': 'Agen & Pool',
    'Pool Jember — Jl. Kalimantan No. 27': 'Pool Jember — Jl. Kalimantan No. 27',
    'Agen Surabaya — Terminal Purabaya': 'Agen Surabaya — Terminal Purabaya',
    'Agen Denpasar — Terminal Ubung': 'Agen Denpasar — Terminal Ubung',
    'Temukan kami di Google Maps: "Nusantara Trans Jember"':
        'Temukan kami di Google Maps: "Nusantara Trans Jember"',
    'Buka Navigasi': 'Buka Navigasi',

    # ---- Rental ----
    'Sewa Mobil Harian dengan Sopir': 'Sewa Mobil Harian dengan Sopir',
    'Katalog rental mobil: MPV, SUV, HiAce, hingga bus kecil. Harga transparan per hari, opsi dengan sopir, bisa antar-jemput.':
        'Katalog rental mobil: MPV, SUV, HiAce, hingga bus kecil. Harga transparan per hari, opsi dengan sopir, bisa antar-jemput.',
    'Armada terawat, sopir berpengalaman, harga transparan.':
        'Armada terawat, sopir berpengalaman, harga transparan.',
    'Semua': 'Semua',
    'Belum ada mobil pada kategori ini': 'Belum ada mobil pada kategori ini',
    'Coba kategori lain atau hubungi kami.': 'Coba kategori lain atau hubungi kami.',
    'Syarat sewa:': 'Syarat sewa:',
    'KTP/SIM asli, minimal 1 hari sewa, DP 50% untuk reservasi. Unit diantar dalam kota Jember gratis — luar kota hubungi CS.':
        'KTP/SIM asli, minimal 1 hari sewa, DP 50% untuk reservasi. Unit diantar dalam kota Jember gratis — luar kota hubungi CS.',
    'Mulai': 'Mulai',
    'Detail': 'Detail',
    'Sewa %(name)s': 'Sewa %(name)s',
    'Harga sewa': 'Harga sewa',
    'jika pakai sopir': 'jika pakai sopir',
    'Sopir gratis': 'Sopir gratis',
    'Tentang Unit Ini': 'Tentang Unit Ini',
    'Pesan Sekarang': 'Pesan Sekarang',
    'Unit dipegang %(h)s jam menunggu pembayaran.': 'Unit dipegang %(h)s jam menunggu pembayaran.',
    'Mobil Lainnya': 'Mobil Lainnya',
    'Detail Pesanan Sewa': 'Detail Pesanan Sewa',
    'Simpan kode pesanan & screenshot halaman ini.': 'Simpan kode pesanan & screenshot halaman ini.',
    'Pesanan Sewa Berhasil Dibuat!': 'Pesanan Sewa Berhasil Dibuat!',
    'Unit %(name)s kami pegang selama %(h)s jam. Selesaikan pembayaran di bawah ini.':
        'Unit %(name)s kami pegang selama %(h)s jam. Selesaikan pembayaran di bawah ini.',
    'Kode Pesanan': 'Kode Pesanan',
    'Mobil': 'Mobil',
    'Penyewa': 'Penyewa',
    'Ambil': 'Ambil',
    'Kembali': 'Kembali',
    'Lokasi ambil': 'Lokasi ambil',
    'Ya, dengan sopir': 'Ya, dengan sopir',
    'Lepas kunci': 'Lepas kunci',
    'Lama sewa': 'Lama sewa',
    'Format JPG/PNG, maks. 5 MB.': 'Format JPG/PNG, maks. 5 MB.',
    'Batas waktu pembayaran terlewat. Silakan buat pesanan baru.':
        'Batas waktu pembayaran terlewat. Silakan buat pesanan baru.',
    'Lihat mobil lain': 'Lihat mobil lain',
    'Unit siap pada jadwal ambil. Tim kami menghubungi via WhatsApp.':
        'Unit siap pada jadwal ambil. Tim kami menghubungi via WhatsApp.',
    'Sewa mobil lain': 'Sewa mobil lain',

    # ---- Panel pembayaran ----
    'Cara Pembayaran': 'Cara Pembayaran',
    'Total yang harus dibayar': 'Total yang harus dibayar',
    'Bayar sebelum': 'Bayar sebelum',
    'Scan QRIS dengan aplikasi e-wallet atau m-banking apa pun, lalu masukkan nilai tepat sesuai total.':
        'Scan QRIS dengan aplikasi e-wallet atau m-banking apa pun, lalu masukkan nilai tepat sesuai total.',
    'Nomor rekening': 'Nomor rekening',
    'Atas nama': 'Atas nama',
    'Salin No. Rekening': 'Salin No. Rekening',
    'Setelah membayar, unggah bukti pembayaran pada form di bawah. Tim kami memverifikasi maksimal 15 menit (07.00–21.00 WIB).':
        'Setelah membayar, unggah bukti pembayaran pada form di bawah. Tim kami memverifikasi maksimal 15 menit (07.00–21.00 WIB).',
    'Konfirmasi via WhatsApp': 'Konfirmasi via WhatsApp',

    # ---- Langkah ----
    'Langkah pemesanan': 'Langkah pemesanan',
    'Cari Jadwal': 'Cari Jadwal',
    'Pilih Kursi': 'Pilih Kursi',
    'Data Pemesan': 'Data Pemesan',
    'Pembayaran': 'Pembayaran',

    # ---- Model: booking ----
    'dibuat': 'dibuat',
    'diperbarui': 'diperbarui',
    'kota': 'kota',
    'nama kota': 'nama kota',
    'provinsi': 'provinsi',
    'kota populer': 'kota populer',
    'rute': 'rute',
    'kota asal': 'kota asal',
    'kota tujuan': 'kota tujuan',
    'jarak (km)': 'jarak (km)',
    'durasi (menit)': 'durasi (menit)',
    'bus': 'bus',
    'kode armada': 'kode armada',
    'nama armada': 'nama armada',
    'nomor polisi': 'nomor polisi',
    'kelas': 'kelas',
    'jumlah baris': 'jumlah baris',
    'fasilitas': 'fasilitas',
    'Pisahkan dengan koma, mis. "AC, WiFi, Toilet, Snack"':
        'Pisahkan dengan koma, mis. "AC, WiFi, Toilet, Snack"',
    'aktif': 'aktif',
    'kursi': 'kursi',
    'label kursi': 'label kursi',
    'baris': 'baris',
    'kolom': 'kolom',
    'jadwal': 'jadwal',
    'jam berangkat': 'jam berangkat',
    'jam tiba': 'jam tiba',
    'harga': 'harga',
    'booking tiket': 'booking tiket',
    'kode booking': 'kode booking',
    'tanggal perjalanan': 'tanggal perjalanan',
    'nama pemesan': 'nama pemesan',
    'no. WhatsApp': 'no. WhatsApp',
    'email': 'email',
    'jumlah kursi': 'jumlah kursi',
    'status': 'status',
    'metode pembayaran': 'metode pembayaran',
    'bukti pembayaran': 'bukti pembayaran',
    'dibayar pada': 'dibayar pada',
    'catatan admin': 'catatan admin',
    'kursi booking': 'kursi booking',
    'AC': 'AC',
    'Sleeper': 'Sleeper',
    'Menunggu pembayaran': 'Menunggu pembayaran',
    'Terkonfirmasi': 'Terkonfirmasi',
    'Dibatalkan': 'Dibatalkan',
    'Kedaluwarsa': 'Kedaluwarsa',

    # ---- Model: rental ----
    'mobil rental': 'mobil rental',
    'mobil': 'mobil',
    'nama mobil': 'nama mobil',
    'kategori': 'kategori',
    'tahun': 'tahun',
    'transmisi': 'transmisi',
    'kapasitas kursi': 'kapasitas kursi',
    'harga per hari': 'harga per hari',
    'biaya sopir per hari': 'biaya sopir per hari',
    'Tambahan bila pelanggan minta disertai sopir. 0 = gratis.':
        'Tambahan bila pelanggan minta disertai sopir. 0 = gratis.',
    'foto mobil': 'foto mobil',
    'deskripsi': 'deskripsi',
    'tersedia': 'tersedia',
    'MPV (5–7 penumpang)': 'MPV (5–7 penumpang)',
    'SUV (5–7 penumpang)': 'SUV (5–7 penumpang)',
    'Van / Minibus (10–16 penumpang)': 'Van / Minibus (10–16 penumpang)',
    'Bus Kecil (20+ penumpang)': 'Bus Kecil (20+ penumpang)',
    'Matic': 'Matic',
    'Manual': 'Manual',
    'Bagasi luas': 'Bagasi luas',
    'booking rental': 'booking rental',
    'kode sewa': 'kode sewa',
    'tanggal ambil': 'tanggal ambil',
    'tanggal kembali': 'tanggal kembali',
    'lokasi ambil': 'lokasi ambil',
    'dengan sopir': 'dengan sopir',
    'nama penyewa': 'nama penyewa',
    'lama sewa (hari)': 'lama sewa (hari)',
    'total harga': 'total harga',
    'Selesai': 'Selesai',

    # ---- Form: booking ----
    'Kota asal': 'Kota asal',
    'Pilih kota asal': 'Pilih kota asal',
    'Kota tujuan': 'Kota tujuan',
    'Pilih kota tujuan': 'Pilih kota tujuan',
    'Nama lengkap': 'Nama lengkap',
    'Nama sesuai KTP/KTM': 'Nama sesuai KTP/KTM',
    'Digunakan untuk konfirmasi & e-tiket.': 'Digunakan untuk konfirmasi & e-tiket.',
    'Saya menyetujui syarat & ketentuan pemesanan.': 'Saya menyetujui syarat & ketentuan pemesanan.',
    'Tanggal perjalanan tidak boleh di masa lalu.': 'Tanggal perjalanan tidak boleh di masa lalu.',
    'Kota asal dan tujuan tidak boleh sama.': 'Kota asal dan tujuan tidak boleh sama.',
    'Nomor telepon tidak valid. Contoh: 081234567890': 'Nomor telepon tidak valid. Contoh: 081234567890',

    # ---- Form: rental ----
    'Tanggal ambil': 'Tanggal ambil',
    'Tanggal kembali': 'Tanggal kembali',
    'Mis. "Bandara Juanda Surabaya" atau alamat hotel.':
        'Mis. "Bandara Juanda Surabaya" atau alamat hotel.',
    'Sertakan sopir (+biaya/hari)': 'Sertakan sopir (+biaya/hari)',
    'Tanggal ambil tidak boleh di masa lalu.': 'Tanggal ambil tidak boleh di masa lalu.',
    'Tanggal kembali harus sama dengan atau setelah tanggal ambil.':
        'Tanggal kembali harus sama dengan atau setelah tanggal ambil.',
    'Maksimal sewa 30 hari. Untuk lebih, hubungi kami.':
        'Maksimal sewa 30 hari. Untuk lebih, hubungi kami.',

    # ---- Form: bukti pembayaran ----
    'Metode pembayaran': 'Metode pembayaran',
    'Ukuran berkas maksimal 5 MB.': 'Ukuran berkas maksimal 5 MB.',

    # ---- Views: booking ----
    'Tanggal perjalanan tidak valid.': 'Tanggal perjalanan tidak valid.',
    'Maaf, beberapa kursi yang Anda pilih baru saja diambil. Silakan pilih ulang.':
        'Maaf, beberapa kursi yang Anda pilih baru saja diambil. Silakan pilih ulang.',
    'Pilih minimal 1 kursi (maksimal 6).': 'Pilih minimal 1 kursi (maksimal 6).',
    'Ada kursi yang tidak ditemukan pada bus ini.': 'Ada kursi yang tidak ditemukan pada bus ini.',
    'Maaf, beberapa kursi baru saja diambil orang lain. Silakan pilih ulang.':
        'Maaf, beberapa kursi baru saja diambil orang lain. Silakan pilih ulang.',
    'Booking berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.':
        'Booking berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.',
    'Booking ini sudah tidak bisa menerima unggahan bukti.':
        'Booking ini sudah tidak bisa menerima unggahan bukti.',
    'Batas waktu pembayaran sudah lewat.': 'Batas waktu pembayaran sudah lewat.',
    'Bukti pembayaran terkirim. Tim kami verifikasi maksimal 15 menit.':
        'Bukti pembayaran terkirim. Tim kami verifikasi maksimal 15 menit.',

    # ---- Views: rental ----
    'Pesanan sewa berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.':
        'Pesanan sewa berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.',
    'Pesanan ini sudah tidak bisa menerima unggahan bukti.':
        'Pesanan ini sudah tidak bisa menerima unggahan bukti.',

    # ---- Templatetags ----
    '{}h': '{}j',
    '{}h {}m': '{}j {}m',
    '{}d {}h': '{}h {}j',
    '{}d {}h {}m': '{}h {}j {}m',

    # ---- Admin (panel internal) ----
    'Inti': 'Inti',
    'Pemesanan Tiket Bus': 'Pemesanan Tiket Bus',
    'Rental Mobil': 'Rental Mobil',
    'rute-rute': 'rute-rute',
    'bus-bus': 'bus-bus',
    'kursi-kursi': 'kursi-kursi',
    'jadwal-jadwal': 'jadwal-jadwal',
    'kota-kota': 'kota-kota',
    'jadwal aktif': 'jadwal aktif',
    'Konfirmasi pembayaran yang dipilih': 'Konfirmasi pembayaran yang dipilih',
    'Batalkan booking yang dipilih': 'Batalkan booking yang dipilih',
    'Batalkan pesanan yang dipilih': 'Batalkan pesanan yang dipilih',
    'Konfirmasi pembayaran yang dipilih': 'Konfirmasi pembayaran yang dipilih',
    'rute': 'rute',
    'batas bayar': 'batas bayar',
    'bukti': 'bukti',
    '(belum ada)': '(belum ada)',
    'foto': 'foto',
    'Booking': 'Booking',
    'Pembayaran': 'Pembayaran',
    'Catatan admin': 'Catatan admin',
    'Waktu': 'Waktu',
    'Pesanan': 'Pesanan',

    # ---- Tambahan (hasil audit compile_i18n) ----
    'Armada Nusantara Trans': 'Armada Nusantara Trans',
    'Armada bus Nusantara Trans': 'Armada bus Nusantara Trans',
    'Bus antar kota': 'Bus antar kota',
    'Estimasi total': 'Estimasi total',
    'Kursi': 'Kursi',
    'Pesan Tiket Bus': 'Pesan Tiket Bus',
    'Pilih Kursi Bus': 'Pilih Kursi Bus',
    'Sewa': 'Sewa',
    'Tanggal perjalanan': 'Tanggal perjalanan',
    'Sewa %(name)s mulai %(price)s/hari. Armada terawat dengan opsi sopir. Pesan online sekarang.':
        'Sewa %(name)s mulai %(price)s/hari. Armada terawat dengan opsi sopir. Pesan online sekarang.',
    'Seat': 'Kursi',
    'Total price': 'Total harga',
    'Travel date': 'Tanggal perjalanan',

    # ---- Halaman kegagalan CSRF ----
    'Sesi Berakhir': 'Sesi Berakhir',
    'Formulir tidak bisa dikirim karena masalah keamanan sesi':
        'Formulir tidak bisa dikirim karena masalah keamanan sesi',
    'Token keamanan (CSRF) dari halaman ini tidak terkirim — biasanya karena cookie browser diblokir, sesi kedaluwarsa, atau halaman terbuka terlalu lama sebelum dikirim.':
        'Token keamanan (CSRF) dari halaman ini tidak terkirim — biasanya karena cookie browser diblokir, sesi kedaluwarsa, atau halaman terbuka terlalu lama sebelum dikirim.',
    'Solusi:': 'Solusi:',
    'Muat ulang halaman ini lalu ulangi langkah terakhir.':
        'Muat ulang halaman ini lalu ulangi langkah terakhir.',
    'Pastikan cookie diizinkan di browser Anda.': 'Pastikan cookie diizinkan di browser Anda.',
    'Jika situs dibuka dalam mode pratinjau/jendela tersemat, buka di tab baru.':
        'Jika situs dibuka dalam mode pratinjau/jendela tersemat, buka di tab baru.',
    'Kembali & Ulangi': 'Kembali & Ulangi',
    'Mulai Pemesanan Ulang': 'Mulai Pemesanan Ulang',

    # ---- Dasbor admin ----
    'Panel Operasional': 'Panel Operasional',
    'Dasbor': 'Dasbor',
    'Booking Hari Ini': 'Booking Hari Ini',
    'Menunggu Verifikasi': 'Menunggu Verifikasi',
    'Belum Bayar': 'Belum Bayar',
    'Pendapatan Bulan Ini': 'Pendapatan Bulan Ini',
    'Pesanan Sewa Menunggu': 'Pesanan Sewa Menunggu',
    'Booking & Pendapatan — 14 Hari Terakhir': 'Booking & Pendapatan — 14 Hari Terakhir',
    'Status Booking': 'Status Booking',
    'Menunggu Verifikasi Pembayaran': 'Menunggu Verifikasi Pembayaran',
    'Kode': 'Kode',
    'Pemesan': 'Pemesan',
    'Bukti': 'Bukti',
    'Batas': 'Batas',
    'Verifikasi': 'Verifikasi',
    'Ada bukti': 'Ada bukti',
    'Tanpa bukti': 'Tanpa bukti',
    'Okupansi': 'Okupansi',
    'Penuh': 'Penuh',
    'Booking Terbaru': 'Booking Terbaru',
    'Pesanan Sewa Terbaru': 'Pesanan Sewa Terbaru',
    'Dibuat': 'Dibuat',
    'Belum ada booking.': 'Belum ada booking.',
    'Belum ada pesanan sewa.': 'Belum ada pesanan sewa.',
    'Rute Terpopuler — 30 Hari': 'Rute Terpopuler — 30 Hari',
    'pemesanan': 'pemesanan',
    'Belum ada data pemesanan.': 'Belum ada data pemesanan.',
    'Aksi Cepat': 'Aksi Cepat',
    'Kota': 'Kota',
    'Semua Modul': 'Semua Modul',
    'Tidak ada booking yang menunggu verifikasi. 🎉': 'Tidak ada booking yang menunggu verifikasi. 🎉',
    'Belum ada penumpang untuk keberangkatan hari ini.': 'Belum ada penumpang untuk keberangkatan hari ini.',

    # ---- Admin: filter, aksi, konfirmasi ----
    'Sudah unggah': 'Sudah unggah',
    'Belum unggah': 'Belum unggah',
    'Ekspor CSV yang dipilih': 'Ekspor CSV yang dipilih',
    'Konfirmasi pembayaran ini': 'Konfirmasi pembayaran ini',
    'Konfirmasi pembayaran sewa ini': 'Konfirmasi pembayaran sewa ini',
    'Booking %s dikonfirmasi.': 'Booking %s dikonfirmasi.',
    'Booking tidak berstatus menunggu pembayaran.': 'Booking tidak berstatus menunggu pembayaran.',
    'Pesanan sewa %s dikonfirmasi.': 'Pesanan sewa %s dikonfirmasi.',
    'Pesanan sewa tidak berstatus menunggu pembayaran.': 'Pesanan sewa tidak berstatus menunggu pembayaran.',    'Jadwal': 'Jadwal',
    'Keberangkatan Hari Ini': 'Keberangkatan Hari Ini',
    'Nusantara Trans Admin': 'Nusantara Trans Admin',
    'Nusantara Trans — Panel Operasional': 'Nusantara Trans — Panel Operasional',
    'Status': 'Status',
}


# =============================================================================
# Katalog bahasa Inggris (locale/en) — msgid → terjemahan EN.
# String yang tidak ada di sini jatuh kembali ke msgid (fallback aman).
# =============================================================================
TRANSLATIONS_EN = {
    # Umum / navigasi
    'Beranda': 'Home',
    'Tiket Bus': 'Bus Tickets',
    'Rental Mobil': 'Car Rental',
    'Cek Booking': 'Check Booking',
    'Tentang': 'About',
    'Kontak': 'Contact',
    'Buka navigasi': 'Toggle navigation',
    'Pilih bahasa': 'Choose language',
    'Tutup': 'Close',
    'Pesan tiket bus antar kota dan sewa mobil dengan mudah, aman, dan harga terbaik. Pilih kursi, bayar via transfer/QRIS, e-tiket instan.':
        'Book intercity bus tickets and rent cars easily, safely, and at the best prices. Choose your seat, pay via bank transfer/QRIS, get an instant e-ticket.',
    'Pesan tiket bus antar kota dan sewa mobil dengan mudah, aman, dan harga terbaik.':
        'Book intercity bus tickets and rent cars easily, safely, and at the best prices.',

    # Footer
    'Melayani perjalanan bus antar kota & penyewaan mobil di Jawa Timur dan sekitarnya sejak 2015. Aman, nyaman, tepat waktu.':
        'Serving intercity bus trips & car rentals across East Java and beyond since 2015. Safe, comfortable, on time.',
    'Perusahaan': 'Company',
    'Tentang Kami': 'About Us',
    'Rute Populer': 'Popular Routes',
    'Semua rute…': 'All routes…',
    'Pembayaran: Transfer Bank & QRIS': 'Payment: Bank Transfer & QRIS',
    'Semua hak dilindungi.': 'All rights reserved.',
    'Dibangun dengan Django & Bootstrap': 'Built with Django & Bootstrap',

    # Beranda
    'Tiket Bus Online & Rental Mobil': 'Online Bus Tickets & Car Rental',
    'Pesan tiket bus antar kota pilih kursi sendiri, atau sewa mobil harian dengan sopir. Pembayaran transfer & QRIS, konfirmasi cepat via WhatsApp.':
        'Book intercity bus tickets with your own seat choice, or rent a car with a driver. Bank transfer & QRIS payment, fast WhatsApp confirmation.',
    '#1 Travel & Rental di Jawa Timur': '#1 Travel & Car Rental in East Java',
    'Perjalanan Nyaman,': 'Comfortable Journeys,',
    'Harga Bersahabat': 'Friendly Prices',
    'Pesan tiket bus antar kota & rental mobil dalam satu tempat. Pilih kursi favoritmu, bayar via transfer atau QRIS, e-tiket langsung di tangan.':
        'Book intercity bus tickets & car rentals in one place. Pick your favorite seat, pay via transfer or QRIS, and get your e-ticket instantly.',
    'Dari': 'From',
    'Ke': 'To',
    'Tanggal': 'Date',
    'Org': 'Pax',
    'Cari Bus': 'Search Buses',
    'Tukar asal & tujuan': 'Swap origin & destination',
    'Butuh mobil? Lihat katalog rental →': 'Need a car? Browse the rental catalog →',
    'Pilih Kursi Sendiri': 'Choose Your Own Seat',
    'Denah kursi interaktif — dapatkan tempat paling nyaman.': 'Interactive seat map — grab the most comfortable spot.',
    'Pembayaran Aman': 'Secure Payment',
    'Transfer bank atau scan QRIS dari e-wallet apa pun.': 'Bank transfer or scan a QRIS code from any e-wallet.',
    'E-Tiket Instan': 'Instant E-Ticket',
    'Kode booking dikirim setelah pembayaran terverifikasi.': 'Your booking code is issued once payment is verified.',
    'CS Ramah 24/7': 'Friendly 24/7 Support',
    'Tim siap membantu via WhatsApp setiap hari.': 'Our team is ready to help on WhatsApp every day.',
    'Destinasi Favorit': 'Favorite Destinations',
    'Rute Bus Populer': 'Popular Bus Routes',
    'Lihat semua': 'See all',
    'jadwal/hari': 'departures/day',
    'mulai': 'from',
    'Armada Kami': 'Our Fleet',
    'Pilih Kelas Sesuai Budget': 'Pick a Class That Fits Your Budget',
    'Semua armada dirawat rutin dan diperiksa sebelum berangkat. Pilih kelas yang paling pas untuk perjalananmu.':
        'Every bus is regularly maintained and inspected before departure. Choose the class that best suits your trip.',
    'Ekonomi': 'Economy',
    '2-2, AC, harga hemat': '2-2, A/C, budget friendly',
    '2-2, pendingin sejuk': '2-2, cool air conditioning',
    'Eksekutif': 'Executive',
    '2-1, reclining seat': '2-1, reclining seats',
    '1-1, bisa tidur penuh': '1-1, fully reclined sleeping',
    'Sewa Mobil untuk Perjalanan Fleksibel': 'Rent a Car for Flexible Travel',
    'Semua mobil': 'All vehicles',
    'Mudah & Cepat': 'Easy & Fast',
    '4 Langkah Menuju Perjalanan': '4 Steps to Your Journey',
    'Cari jadwal': 'Find a schedule',
    'Tentukan kota asal, tujuan, dan tanggal.': 'Pick your origin, destination, and date.',
    'Pilih kursi': 'Choose a seat',
    'Ambil kursi favorit lewat denah interaktif.': 'Grab your favorite seat on the interactive map.',
    'Isi data': 'Fill in details',
    'Masukkan kontak, dapatkan kode booking.': 'Enter your contact info and get a booking code.',
    'Bayar & berangkat': 'Pay & go',
    'Transfer/QRIS, unggah bukti, tunjukkan e-tiket.': 'Transfer/QRIS, upload the proof, show your e-ticket.',
    'Siap Berangkat Hari Ini?': 'Ready to Depart Today?',
    'Kursi terbatas untuk jadwal populer — amankan tempatmu sekarang.': 'Seats on popular departures are limited — secure yours now.',
    'Pesan Tiket Sekarang': 'Book Tickets Now',

    # Cari jadwal
    'Cari & Pesan Tiket Bus Online': 'Search & Book Bus Tickets Online',
    'Cari jadwal bus antar kota, bandingkan harga & kelas, pilih kursi favoritmu.':
        'Search intercity bus schedules, compare prices & classes, and pick your favorite seat.',
    'Tanpa antre — pilih kursi sendiri, bayar transfer/QRIS.': 'No queues — pick your own seat, pay by transfer/QRIS.',
    'Kota Asal': 'Origin City',
    'Kota Tujuan': 'Destination City',
    'Penumpang': 'Passengers',
    'Cari': 'Search',
    'jadwal ditemukan': 'schedules found',
    'Belum ada jadwal untuk rute & tanggal ini': 'No schedules for this route & date yet',
    'Coba tanggal lain, atau hubungi kami via WhatsApp untuk charter khusus.': 'Try another date, or contact us on WhatsApp for a custom charter.',
    'Tanya CS': 'Ask Support',
    'Rute paling dicari': 'Most searched routes',

    # Kartu jadwal
    'hari': 'day',
    'Mulai dari': 'From',
    'kursi': 'seats',
    'kursi tersedia': 'seats available',
    'sisa': 'left',
    'Pilih Kursi': 'Select Seats',

    # Pilih kursi
    'Denah Kursi': 'Seat Map',
    'Tersedia': 'Available',
    'Terisi': 'Taken',
    'Pilihanmu': 'Your pick',
    'Sopir': 'Driver',
    'Kursi %(label)s': 'Seat %(label)s',
    '1 kursi sudah terisi pada tanggal ini.': '1 seat is already taken on this date.',
    '%(taken_count)s kursi sudah terisi pada tanggal ini.': '%(taken_count)s seats are already taken on this date.',
    'Ringkasan': 'Summary',
    'Kursi dipilih': 'Seats selected',
    'Nomor kursi': 'Seat numbers',
    'Total': 'Total',
    'Lanjut Isi Data': 'Continue to Details',
    'Kursi dikunci %(h)s jam setelah booking dibuat.': 'Seats are locked for %(h)s hours after booking.',

    # Data pemesan
    'Data Pemesan': 'Booking Details',
    'Hampir selesai! Periksa ringkasan & lengkapi kontakmu.': 'Almost done! Review the summary & complete your contact info.',
    'Informasi Kontak': 'Contact Information',
    'Buat Booking': 'Create Booking',
    'Kursi langsung dikunci untuk Anda. Selesaikan pembayaran dalam %(h)s jam.': 'Your seats are locked instantly. Complete payment within %(h)s hours.',
    'Detail Perjalanan': 'Trip Details',
    'Harga/kursi': 'Price/seat',
    'Jumlah kursi': 'Number of seats',
    'Total Bayar': 'Total to Pay',

    # Detail booking
    'Booking': 'Booking',
    'Detail Booking': 'Booking Details',
    'Simpan kode booking & screenshot halaman ini.': 'Save your booking code & screenshot this page.',
    'Booking Berhasil Dibuat!': 'Booking Created Successfully!',
    'Kursi Anda dikunci selama %(h)s jam. Selesaikan pembayaran di bawah ini agar booking tidak kedaluwarsa.':
        'Your seats are locked for %(h)s hours. Complete the payment below before the booking expires.',
    'Kode Booking': 'Booking Code',
    'Nama Pemesan': 'Passenger Name',
    'No. WhatsApp': 'WhatsApp Number',
    'Rute': 'Route',
    'Keberangkatan': 'Departure',
    'Bus': 'Bus',
    'Tunjukkan kode booking & kartu identitas ke petugas saat Check-in (datang 30 menit sebelum berangkat).':
        'Show your booking code & ID card to our staff at check-in (arrive 30 minutes before departure).',
    'Unggah Bukti Pembayaran': 'Upload Payment Proof',
    'Bukti sudah diterima': 'Proof received',
    'Metode:': 'Method:',
    'menunggu verifikasi admin (maks. 15 menit).': 'awaiting admin verification (max. 15 minutes).',
    'Metode yang digunakan': 'Payment method used',
    'Bukti pembayaran': 'Payment proof',
    'Format JPG/PNG, maks. 5 MB. Screenshot m-banking atau foto struk/QRIS.':
        'JPG/PNG, max. 5 MB. A screenshot of your banking app or a photo of the receipt/QRIS.',
    'Kirim Bukti Pembayaran': 'Submit Payment Proof',
    'Batas waktu pembayaran terlewat, booking ini kedaluwarsa. Silakan buat booking baru.':
        'The payment deadline has passed and this booking has expired. Please create a new booking.',
    'Cari jadwal lagi': 'Search schedules again',
    'Pembayaran Terverifikasi': 'Payment Verified',
    'E-tiket aktif. Sampai jumpa di pool!': 'Your e-ticket is active. See you at the pool!',
    'Booking ini sudah tidak aktif.': 'This booking is no longer active.',
    'Pesan tiket lain': 'Book another ticket',
    'Butuh Bantuan?': 'Need Help?',
    'Sebutkan kode booking Anda saat menghubungi CS:': 'Mention your booking code when contacting support:',
    'Chat WhatsApp': 'Chat on WhatsApp',

    # Cek booking
    'Cek Status Booking': 'Check Booking Status',
    'Masukkan kode booking untuk melihat status & e-tiket.': 'Enter your booking code to view its status & e-ticket.',
    'Booking dengan kode <strong>%(code)s</strong> tidak ditemukan. Periksa kembali penulisannya.':
        'No booking found with code <strong>%(code)s</strong>. Please check it again.',
    'Lihat Status': 'View Status',
    'Kode booking terlihat seperti: NT-A7K2QP': 'A booking code looks like: NT-A7K2QP',

    # Halaman rute (SEO)
    'Tiket Bus %(origin)s ke %(dest)s — Jadwal & Harga': 'Bus Tickets %(origin)s to %(dest)s — Schedule & Prices',
    'Tiket Bus %(origin)s → %(dest)s': 'Bus Tickets %(origin)s → %(dest)s',
    'Jadwal bus %(origin)s–%(dest)s hari ini: keberangkatan, durasi, kelas armada, dan harga tiket mulai dari harga termurah. Pesan online, pilih kursi sendiri.':
        "Today's %(origin)s–%(dest)s bus schedule: departures, duration, bus classes, and ticket prices from the lowest. Book online and choose your own seat.",
    'Bus %(origin)s ke %(dest)s': 'Bus from %(origin)s to %(dest)s',
    'keberangkatan setiap hari': 'departures every day',
    'Jadwal Hari Ini & Setelahnya': "Today's & Upcoming Schedules",
    'Jadwal untuk rute ini belum tersedia. Hubungi kami untuk info terbaru.': 'No schedules for this route yet. Contact us for the latest info.',
    'Cek Kursi Tersedia': 'Check Seat Availability',
    'Jumlah kursi berubah setiap saat. Pilih tanggal untuk melihat kursi yang masih kosong:':
        'Seat availability changes all the time. Pick a date to see the free seats:',
    'Lihat Kursi Sekarang': 'See Seats Now',
    'Pembatalan gratis sebelum pembayaran.': 'Free cancellation before payment.',
    'E-tiket digital, tanpa cetak.': 'Digital e-ticket, no printing needed.',
    'Bisa bayar lewat QRIS.': 'Pay via QRIS.',

    # Tentang & kontak
    'Tentang Nusantara Trans': 'About Nusantara Trans',
    'Menghubungkan kota-kota di Jawa Timur & Bali sejak 2015': 'Connecting cities across East Java & Bali since 2015',
    'Cerita Kami': 'Our Story',
    'Berawal dari Satu Bus, Kini Layani 7+ Kota': 'From One Bus to Serving 7+ Cities',
    'Nusantara Trans dimulai tahun 2015 dari satu bus ekonomi rute Jember–Surabaya. Dukungan pelanggan membuat kami bertumbuh: kini kami mengoperasikan armada bus berbagai kelas dan layanan rental mobil dengan sopir berpengalaman.':
        'Nusantara Trans started in 2015 with a single economy bus on the Jember–Surabaya route. Our customers made us grow: we now run buses of various classes and a car rental service with experienced drivers.',
    'Kami percaya perjalanan darat seharusnya mudah dipesan: pilih kursi sendiri, bayar dari mana saja, dan dapatkan e-tiket tanpa antre di loket.':
        'We believe land travel should be easy to book: choose your own seat, pay from anywhere, and get an e-ticket without queueing at a counter.',
    'Pesan Tiket': 'Book Tickets',
    'Hubungi Kami': 'Contact Us',
    'Kota Terlayani': 'Cities Served',
    'Rute Harian': 'Daily Routes',
    'Armada Bus': 'Buses',
    'Mobil Rental': 'Rental Cars',
    'Nilai Kami': 'Our Values',
    'Tepat Waktu': 'On Time',
    'Berangkat & tiba sesuai jadwal adalah janji utama kami.': 'Departing & arriving on schedule is our main promise.',
    'Ramah Pelanggan': 'Customer Friendly',
    'Sopir dan CS terlatih membantu dengan sepenuh hati.': 'Trained drivers and support staff who help wholeheartedly.',
    'Armada Terawat': 'Well-Maintained Fleet',
    'Servis berkala & pemeriksaan sebelum setiap keberangkatan.': 'Regular servicing & checks before every departure.',
    'Ada pertanyaan sebelum / sesudah memesan? Tim kami siap membantu.': 'Questions before or after booking? Our team is ready to help.',
    'Tercepat untuk konfirmasi & bantuan booking.': 'The fastest way to confirm & get booking assistance.',
    'Email': 'Email',
    'Untuk kerja sama, charter, & feedback.': 'For partnerships, charters, & feedback.',
    'Kantor Pusat': 'Head Office',
    'Agen & Pool': 'Agents & Pools',
    'Pool Jember — Jl. Kalimantan No. 27': 'Jember Pool — Jl. Kalimantan No. 27',
    'Agen Surabaya — Terminal Purabaya': 'Surabaya Agent — Purabaya Terminal',
    'Agen Denpasar — Terminal Ubung': 'Denpasar Agent — Ubung Terminal',
    'Temukan kami di Google Maps: "Nusantara Trans Jember"': 'Find us on Google Maps: "Nusantara Trans Jember"',
    'Buka Navigasi': 'Open Navigation',

    # Rental
    'Sewa Mobil Harian dengan Sopir': 'Daily Car Rental with Driver',
    'Katalog rental mobil: MPV, SUV, HiAce, hingga bus kecil. Harga transparan per hari, opsi dengan sopir, bisa antar-jemput.':
        'Rental catalog: MPVs, SUVs, HiAce vans, and mini buses. Transparent daily prices, optional driver, and delivery available.',
    'Armada terawat, sopir berpengalaman, harga transparan.': 'Well-maintained vehicles, experienced drivers, transparent prices.',
    'Semua': 'All',
    'Belum ada mobil pada kategori ini': 'No vehicles in this category yet',
    'Coba kategori lain atau hubungi kami.': 'Try another category or contact us.',
    'Syarat sewa:': 'Rental requirements:',
    'KTP/SIM asli, minimal 1 hari sewa, DP 50% untuk reservasi. Unit diantar dalam kota Jember gratis — luar kota hubungi CS.':
        "Original ID/driver's license, minimum 1-day rental, 50% down payment to reserve. Free delivery within Jember city — contact support for other areas.",
    'Mulai': 'From',
    'Detail': 'Details',
    'Sewa %(name)s': 'Rent %(name)s',
    'Harga sewa': 'Rental price',
    'jika pakai sopir': 'if with driver',
    'Sopir gratis': 'Driver included',
    'Tentang Unit Ini': 'About This Vehicle',
    'Pesan Sekarang': 'Book Now',
    'Unit dipegang %(h)s jam menunggu pembayaran.': 'The vehicle is held for %(h)s hours while awaiting payment.',
    'Mobil Lainnya': 'More Vehicles',
    'Detail Pesanan Sewa': 'Rental Order Details',
    'Simpan kode pesanan & screenshot halaman ini.': 'Save your order code & screenshot this page.',
    'Pesanan Sewa Berhasil Dibuat!': 'Rental Order Created Successfully!',
    'Unit %(name)s kami pegang selama %(h)s jam. Selesaikan pembayaran di bawah ini.':
        'We are holding the %(name)s for %(h)s hours. Complete the payment below.',
    'Kode Pesanan': 'Order Code',
    'Mobil': 'Vehicle',
    'Penyewa': 'Renter',
    'Ambil': 'Pick-up',
    'Kembali': 'Return',
    'Lokasi ambil': 'Pick-up location',
    'Ya, dengan sopir': 'Yes, with driver',
    'Lepas kunci': 'Self-drive',
    'Lama sewa': 'Rental length',
    'Format JPG/PNG, maks. 5 MB.': 'JPG/PNG, max. 5 MB.',
    'Batas waktu pembayaran terlewat. Silakan buat pesanan baru.': 'The payment deadline has passed. Please create a new order.',
    'Lihat mobil lain': 'See other vehicles',
    'Unit siap pada jadwal ambil. Tim kami menghubungi via WhatsApp.': 'The vehicle will be ready at pick-up. Our team will contact you via WhatsApp.',
    'Sewa mobil lain': 'Rent another car',

    # Panel pembayaran
    'Cara Pembayaran': 'How to Pay',
    'Total yang harus dibayar': 'Total amount due',
    'Bayar sebelum': 'Pay before',
    'Scan QRIS dengan aplikasi e-wallet atau m-banking apa pun, lalu masukkan nilai tepat sesuai total.':
        'Scan the QRIS code with any e-wallet or mobile banking app, then enter the exact total.',
    'Nomor rekening': 'Account number',
    'Atas nama': 'Account holder',
    'Salin No. Rekening': 'Copy account number',
    'Setelah membayar, unggah bukti pembayaran pada form di bawah. Tim kami memverifikasi maksimal 15 menit (07.00–21.00 WIB).':
        'After paying, upload your payment proof in the form below. We verify within 15 minutes (07:00–21:00 WIB).',
    'Konfirmasi via WhatsApp': 'Confirm via WhatsApp',

    # Langkah
    'Langkah pemesanan': 'Booking steps',
    'Cari Jadwal': 'Find Schedule',
    'Pilih Kursi': 'Select Seat',
    'Pembayaran': 'Payment',

    # Status & pesan (tampak pelanggan)
    'Menunggu pembayaran': 'Awaiting payment',
    'Terkonfirmasi': 'Confirmed',
    'Dibatalkan': 'Cancelled',
    'Kedaluwarsa': 'Expired',
    'Selesai': 'Completed',
    'Booking berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.': 'Booking created! Complete the payment before the deadline.',
    'Pesanan sewa berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.': 'Rental order created! Complete the payment before the deadline.',
    'Bukti pembayaran terkirim. Tim kami verifikasi maksimal 15 menit.': 'Payment proof submitted. We will verify it within 15 minutes.',
    'Booking ini sudah tidak bisa menerima unggahan bukti.': 'This booking can no longer accept proof uploads.',
    'Pesanan ini sudah tidak bisa menerima unggahan bukti.': 'This order can no longer accept proof uploads.',
    'Batas waktu pembayaran sudah lewat.': 'The payment deadline has passed.',
    'Tanggal perjalanan tidak valid.': 'Invalid travel date.',
    'Tanggal perjalanan tidak boleh di masa lalu.': 'Travel date cannot be in the past.',
    'Kota asal dan tujuan tidak boleh sama.': 'Origin and destination cannot be the same.',
    'Maaf, beberapa kursi yang Anda pilih baru saja diambil. Silakan pilih ulang.':
        'Sorry, some of your chosen seats were just taken. Please choose again.',
    'Maaf, beberapa kursi baru saja diambil orang lain. Silakan pilih ulang.':
        'Sorry, some seats were just taken by someone else. Please choose again.',
    'Pilih minimal 1 kursi (maksimal 6).': 'Select at least 1 seat (maximum 6).',
    'Ada kursi yang tidak ditemukan pada bus ini.': 'Some seats were not found on this bus.',

    # Form
    'Kota asal': 'Origin city',
    'Pilih kota asal': 'Choose origin city',
    'Kota tujuan': 'Destination city',
    'Pilih kota tujuan': 'Choose destination city',
    'Tanggal perjalanan': 'Travel date',
    'Nama lengkap': 'Full name',
    'Nama sesuai KTP/KTM': 'Name as on your ID card',
    'Digunakan untuk konfirmasi & e-tiket.': 'Used for confirmation & your e-ticket.',
    'Saya menyetujui syarat & ketentuan pemesanan.': 'I agree to the terms & conditions.',
    'Nomor telepon tidak valid. Contoh: 081234567890': 'Invalid phone number. Example: 081234567890',
    'Tanggal ambil': 'Pick-up date',
    'Tanggal kembali': 'Return date',
    'Mis. "Bandara Juanda Surabaya" atau alamat hotel.': 'E.g. "Juanda Airport Surabaya" or your hotel address.',
    'Sertakan sopir (+biaya/hari)': 'Include a driver (+fee/day)',
    'Tanggal ambil tidak boleh di masa lalu.': 'Pick-up date cannot be in the past.',
    'Tanggal kembali harus sama dengan atau setelah tanggal ambil.': 'Return date must be on or after the pick-up date.',
    'Maksimal sewa 30 hari. Untuk lebih, hubungi kami.': 'Maximum rental is 30 days. For longer periods, contact us.',
    'Metode pembayaran': 'Payment method',
    'Ukuran berkas maksimal 5 MB.': 'File size must be at most 5 MB.',
    'Kursi': 'Seat',
    'Sewa': 'Rent',
    'Sewa %(name)s mulai %(price)s/hari. Armada terawat dengan opsi sopir. Pesan online sekarang.':
        'Rent the %(name)s from %(price)s/day. Well-maintained vehicle with optional driver. Book online now.',
    'Estimasi total': 'Estimated total',
    'Pesan Tiket Bus': 'Bus Tickets',
    'Pilih Kursi Bus': 'Select Your Bus Seat',
    'Bus antar kota': 'Intercity bus',
    'Armada Nusantara Trans': 'Nusantara Trans fleet',
    'Armada bus Nusantara Trans': 'Nusantara Trans bus fleet',
    'Armada Kami': 'Our Fleet',

    # Durasi
    '{}h': '{}h',
    '{}h {}m': '{}h {}m',
    '{}d {}h': '{}d {}h',
    '{}d {}h {}m': '{}d {}h {}m',

    # Rental model (label pelanggan)
    'MPV (5–7 penumpang)': 'MPV (5–7 passengers)',
    'SUV (5–7 penumpang)': 'SUV (5–7 passengers)',
    'Van / Minibus (10–16 penumpang)': 'Van / Minibus (10–16 passengers)',
    'Bus Kecil (20+ penumpang)': 'Mini Bus (20+ passengers)',
    'Matic': 'Automatic',
    'Manual': 'Manual',
    'Bagasi luas': 'Spacious luggage',

    # ---- Halaman kegagalan CSRF ----
    'Sesi Berakhir': 'Session Expired',
    'Formulir tidak bisa dikirim karena masalah keamanan sesi':
        'The form could not be submitted due to a session security issue',
    'Token keamanan (CSRF) dari halaman ini tidak terkirim — biasanya karena cookie browser diblokir, sesi kedaluwarsa, atau halaman terbuka terlalu lama sebelum dikirim.':
        'The security token (CSRF) from this page was not sent — usually because browser cookies are blocked, the session expired, or the page stayed open too long before submitting.',
    'Solusi:': 'How to fix it:',
    'Muat ulang halaman ini lalu ulangi langkah terakhir.':
        'Reload this page and repeat your last step.',
    'Pastikan cookie diizinkan di browser Anda.': 'Make sure cookies are allowed in your browser.',
    'Jika situs dibuka dalam mode pratinjau/jendela tersemat, buka di tab baru.':
        'If the site is open in an embedded preview frame, open it in a new tab instead.',
    'Kembali & Ulangi': 'Go Back & Retry',
    'Mulai Pemesanan Ulang': 'Start a New Booking',

    # ---- Dasbor admin ----
    'Panel Operasional': 'Operations Panel',
    'Dasbor': 'Dashboard',
    'Booking Hari Ini': 'Bookings Today',
    'Menunggu Verifikasi': 'Awaiting Verification',
    'Belum Bayar': 'Unpaid',
    'Pendapatan Bulan Ini': 'Revenue This Month',
    'Pesanan Sewa Menunggu': 'Rental Orders Awaiting',
    'Booking & Pendapatan — 14 Hari Terakhir': 'Bookings & Revenue — Last 14 Days',
    'Status Booking': 'Booking Status',
    'Menunggu Verifikasi Pembayaran': 'Payments Awaiting Verification',
    'Kode': 'Code',
    'Pemesan': 'Customer',
    'Bukti': 'Proof',
    'Batas': 'Deadline',
    'Verifikasi': 'Verify',
    'Ada bukti': 'With proof',
    'Tanpa bukti': 'No proof',
    'Okupansi': 'Occupancy',
    'Penuh': 'Full',
    'Booking Terbaru': 'Latest Bookings',
    'Pesanan Sewa Terbaru': 'Latest Rental Orders',
    'Dibuat': 'Created',
    'Belum ada booking.': 'No bookings yet.',
    'Belum ada pesanan sewa.': 'No rental orders yet.',
    'Rute Terpopuler — 30 Hari': 'Top Routes — 30 Days',
    'pemesanan': 'bookings',
    'Belum ada data pemesanan.': 'No booking data yet.',
    'Aksi Cepat': 'Quick Actions',
    'Kota': 'City',
    'Semua Modul': 'All Modules',
    'Tidak ada booking yang menunggu verifikasi. 🎉': 'No bookings awaiting verification. 🎉',
    'Belum ada penumpang untuk keberangkatan hari ini.': "No passengers for today's departures yet.",

    # ---- Admin: filter, aksi, konfirmasi ----
    'Sudah unggah': 'Uploaded',
    'Belum unggah': 'Not uploaded',
    'Ekspor CSV yang dipilih': 'Export selected as CSV',
    'Konfirmasi pembayaran ini': 'Confirm this payment',
    'Konfirmasi pembayaran sewa ini': 'Confirm this rental payment',
    'Booking %s dikonfirmasi.': 'Booking %s confirmed.',
    'Booking tidak berstatus menunggu pembayaran.': 'Booking is not awaiting payment.',
    'Pesanan sewa %s dikonfirmasi.': 'Rental order %s confirmed.',
    'Pesanan sewa tidak berstatus menunggu pembayaran.': 'Rental order is not awaiting payment.',    'Jadwal': 'Schedule',
    'Keberangkatan Hari Ini': 'Departures Today',
    'Nusantara Trans Admin': 'Nusantara Trans Admin',
    'Nusantara Trans — Panel Operasional': 'Nusantara Trans — Operations Panel',
    'Status': 'Status',
}

