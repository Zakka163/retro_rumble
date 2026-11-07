#!/usr/bin/env python3
"""
Daytona USA Event Monitor & Live Diagnostic
===========================================
Mendeteksi trigger benturan 'MOBIL NABRAK' di Sega Model 2 Emulator.
Dilengkapi mode diagnostik visual agar Anda tahu persis apa yang sedang terjadi.
"""

import sys
import time

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    try:
        psapi = ctypes.windll.psapi
    except Exception:
        psapi = None
else:
    kernel32 = None
    user32 = None
    psapi = None


def get_base_address(h_process):
    """Mendapatkan base address proses (kompatibel Python 32-bit & 64-bit)."""
    if not IS_WINDOWS or not psapi:
        return 0x00400000

    try:
        # LIST_MODULES_32BIT (0x02) | LIST_MODULES_ALL (0x03)
        h_mods = (wintypes.HMODULE * 512)()
        cb_needed = wintypes.DWORD()
        # Coba EnumProcessModulesEx jika tersedia (Windows 7+)
        if hasattr(psapi, "EnumProcessModulesEx"):
            res = psapi.EnumProcessModulesEx(h_process, ctypes.byref(h_mods), ctypes.sizeof(h_mods), ctypes.byref(cb_needed), 0x03)
            if res and h_mods[0]:
                return h_mods[0]
        # Fallback ke EnumProcessModules biasa
        res = psapi.EnumProcessModules(h_process, ctypes.byref(h_mods), ctypes.sizeof(h_mods), ctypes.byref(cb_needed))
        if res and h_mods[0]:
            return h_mods[0]
    except Exception:
        pass

    return 0x00400000  # Default base address Sega Model 2


def find_emulator_candidates():
    """Mencari jendela dan proses emulator yang cocok secara komprehensif."""
    candidates = []

    if not IS_WINDOWS:
        return candidates

    # 1. Scan semua jendela yang sedang terbuka (Case-Insensitive)
    def enum_windows_callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                t_lower = title.lower()
                # Cocokkan jika judul jendela memuat kata kunci ini:
                if any(k in t_lower for k in ["daytona", "model 2", "emulator", "m2"]):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value > 0:
                        candidates.append((pid.value, f"Jendela: '{title}'", hwnd))
        return True

    cb_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(cb_type(enum_windows_callback), 0)

    # 2. Jika lewat jendela belum ketemu, scan daftar proses Windows
    if not candidates:
        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD),
                ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.c_size_t),
                ('th32ModuleID', wintypes.DWORD),
                ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD),
                ('pcPriClassBase', wintypes.LONG),
                ('dwFlags', wintypes.DWORD),
                ('szExeFile', ctypes.c_char * 260)
            ]

        snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
        if snapshot != -1:
            entry = PROCESSENTRY32()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
            if kernel32.Process32First(snapshot, ctypes.byref(entry)):
                while True:
                    name = entry.szExeFile.decode("utf-8", errors="ignore").lower()
                    if any(k in name for k in ["emulator", "model2", "daytona", "m2"]):
                        candidates.append((entry.th32ProcessID, f"Proses: '{name}'", None))
                        break
                    if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                        break
            kernel32.CloseHandle(snapshot)

    return candidates


def read_byte_safe(h_process, address):
    """Membaca 1 byte dengan aman."""
    buf = ctypes.c_ubyte()
    bytes_read = ctypes.c_size_t()
    res = kernel32.ReadProcessMemory(
        h_process,
        ctypes.c_void_p(address),
        ctypes.byref(buf),
        1,
        ctypes.byref(bytes_read)
    )
    if res and bytes_read.value == 1:
        return buf.value
    return None


def main():
    print("=" * 65)
    print("   DAYTONA USA EVENT MONITOR (Sega Model 2)")
    print("   Deteksi Real-Time Trigger 'MOBIL NABRAK'")
    print("=" * 65)

    if not IS_WINDOWS:
        print("\n[PERINGATAN] Anda sedang menjalankan script ini di macOS/Linux.")
        print("Buka file ini di komputer Windows tempat Sega Model 2 Emulator berjalan!\n")
        return

    print("\n[1/3] Sedang memindai jendela dan proses game...")
    print("      (Pastikan EMULATOR.EXE sudah dibuka dan game Daytona USA sudah LOAD!)")

    pid = None
    info = None

    dots = 0
    while True:
        candidates = find_emulator_candidates()
        if candidates:
            pid, info, _ = candidates[0]
            break

        dots = (dots + 1) % 4
        print(f"\r      Menunggu emulator/game dibuka{'.' * dots}   ", end="", flush=True)
        time.sleep(1.0)

    print(f"\n\n[2/3] BERHASIL MENEMUKAN EMULATOR!")
    print(f"      -> {info} (PID: {pid})")

    # Buka izin akses ke proses emulator
    PROCESS_ALL_ACCESS = 0x1F0FFF
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400

    # Coba VM_READ dulu, jika gagal coba ALL_ACCESS
    h_process = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h_process:
        h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)

    if not h_process:
        err = kernel32.GetLastError()
        print(f"\n[ERROR] Gagal membuka proses emulator (Error Code: {err})")
        print("SOLUSI: Buka Command Prompt dengan 'Run as Administrator', lalu jalankan lagi script ini.")
        return

    # Tentukan alamat memori Drive Board Model 2
    base_addr = get_base_address(h_process)
    target_addr = base_addr + 0x17285B

    print(f"[3/3] Konfigurasi Alamat Memori:")
    print(f"      - Base Address Modul : 0x{base_addr:08X}")
    print(f"      - Register FFB Target : 0x{target_addr:08X} (dan 0x0057285B)")
    print("=" * 65)
    print("Status: MENDENGARKAN EVENT GAME... (Silakan jalankan mobil Anda!)\n")

    prev_ff = 0
    last_crash_tick = 0
    last_ui_print = 0

    try:
        while True:
            # Baca alamat memori relatif base, jika gagal baca alamat absolut
            ff = read_byte_safe(h_process, target_addr)
            if ff is None and target_addr != 0x0057285B:
                ff = read_byte_safe(h_process, 0x0057285B)

            if ff is None:
                err = kernel32.GetLastError()
                print(f"\n[WARN] Gagal membaca memori (Error: {err}). Emulator mungkin ditutup.")
                break

            now = time.time() * 1000.0

            # Deteksi Benturan / Rumble (Nilai Drive Board 0x40 s/d 0x47)
            if 0x3F < ff < 0x48:
                force = ((ff - 63) / 8.0) * 100.0
                is_new_impact = (prev_ff <= 0x3F or prev_ff >= 0x48)

                if is_new_impact and (now - last_crash_tick > 350):
                    ts = time.strftime("%H:%M:%S")
                    print(f"\n[{ts}] >>> MOBIL NABRAK! <<< (Raw: 0x{ff:02X} | Kekuatan: {force:.0f}%)")
                    last_crash_tick = now

            # Tampilkan indikator live di console (setiap 200 ms) agar Anda tahu memori sedang aktif terbaca
            if now - last_ui_print > 200:
                keterangan = "Normal/Lurus"
                if 0x09 < ff < 0x18:
                    keterangan = "Spring (Tahanan Setir)"
                elif 0x2F < ff < 0x3D:
                    keterangan = "Centering (Kembali ke Tengah)"
                elif 0x3F < ff < 0x48:
                    keterangan = "** BENTURAN / RUMBLE **"
                elif 0x4F < ff < 0x58:
                    keterangan = "Roll Kiri (Belok Kiri)"
                elif 0x5F < ff < 0x68:
                    keterangan = "Roll Kanan (Belok Kanan)"

                # Cetak satu baris yang ter-update terus-menerus
                print(f"\r[LIVE FEED] Nilai FFB Saat Ini: 0x{ff:02X} ({keterangan})       ", end="", flush=True)
                last_ui_print = now

            prev_ff = ff
            time.sleep(0.016)  # 60 FPS loop

    except KeyboardInterrupt:
        print("\n\nMonitor dihentikan oleh pengguna.")
    finally:
        kernel32.CloseHandle(h_process)


if __name__ == "__main__":
    main()
