# Daytona USA Python Monitor & Rumble Bridge (`plugin_other`)

Pendekatan alternatif **100% Python** untuk mendeteksi event tabrakan dan mengontrol rumble dari game **Daytona USA** di **Sega Model 2 Emulator**, **tanpa perlu kompilasi C++ Visual Studio** dan **tanpa perlu modifikasi/injeksi file ke emulator**.

---

## 🚀 Perbandingan: C++ DLL vs Python Reader

| Fitur | C++ DLL (`FFBArcadePlugin`) | Python Reader (`plugin_other`) |
| :--- | :--- | :--- |
| **Kompilasi** | Wajib Visual Studio Win32 C++ | **Tanpa kompilasi** (Langsung `python daytona_monitor.py`) |
| **Injeksi File** | Harus copy `dinput8.dll` ke folder emulator | **Zero modification** (Emulator tetap 100% original) |
| **Integrasi Hardware** | Kaku, butuh library C++ tambahan | **Sangat mudah** (Bisa kontrol Arduino via Serial, UDP, XInput) |
| **Mode Simulasi** | Tidak ada (harus jalan di Windows asli) | **Bisa dites di Mac/Linux** via flag `--simulate` |
| **Bahasa** | C++ | Python 3 (menggunakan built-in `ctypes`) |

---

## 🛠️ Cara Kerja

Script Python membaca memori virtual emulator secara *real-time* dari luar proses menggunakan Windows API (`OpenProcess` & `ReadProcessMemory`):

1. **Auto-Detect Process:** Otomatis mendeteksi saat `EMULATOR.EXE` atau `EMULATOR_MULTICPU.EXE` sedang berjalan.
2. **Membaca Register Drive Board Model 2:** Membaca register FFB di alamat `base + 0x17285B` (atau `0x0057285B`) setiap 16 ms (60 Hz).
3. **Deteksi Benturan:** Nilai byte getaran `0x40` s/d `0x47` disaring dengan *edge-trigger* dan debounce (350 ms).
4. **Trigger Aksi Otomatis:**
   - 📢 **Console Output:** Mencetak `[TRIGGER] >>> MOBIL NABRAK! <<< (Raw: 0xXX | Force: YY%)`.
   - 🎮 **Xbox / XInput Gamepad Rumble:** Menggetarkan motor stik Xbox secara langsung lewat `xinput1_4.dll`.
   - 🔌 **Arduino / Microcontroller:** Mengirim karakter `'C'` lewat USB Serial COM port.
   - 🌐 **UDP Broadcast:** Mengirim pesan `CRASH:<force>` ke `127.0.0.1:9999` untuk dashboard atau aplikasi lain.

---

## 📂 Struktur File

- [`daytona_monitor.py`](daytona_monitor.py) : Script utama monitor & rumble engine (pure Python standard library).
- [`config.ini`](config.ini) : Pengaturan polling rate, debounce, COM port Arduino, UDP socket, dan nama proses.
- [`arduino_rumble_example.ino`](arduino_rumble_example.ino) : Contoh kode Arduino untuk menyalakan motor getar fisik saat menerima signal `'C'`.

---

## 💻 Cara Menggunakan

### A. Uji Coba Cepat (Mode Simulasi di Mac / Windows)
Anda dapat langsung menguji logika dan output trigger bahkan di macOS sekarang juga:
```bash
python3 daytona_monitor.py --simulate
```
*Script akan mensimulasikan kejadian mobil menabrak dinding secara periodik.*

### B. Menjalankan di Windows (Bersama Emulator)
1. Jalankan Sega Model 2 Emulator (`EMULATOR.EXE`) dan buka game **Daytona USA**.
2. Di command prompt Windows, jalankan:
   ```cmd
   python daytona_monitor.py
   ```
3. Begitu terhubung, script akan mendeteksi `EMULATOR.EXE` dan menampilkan:
   ```text
   [OK] Terhubung ke Sega Model 2 Emulator!
        Base Address: 0x00400000
        Monitoring FFB Drive Register: 0x0057285B
   ```
4. Tabrakkan mobil di game Daytona USA, dan trigger akan langsung aktif seketika!

