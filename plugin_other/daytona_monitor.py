#!/usr/bin/env python3
"""
Daytona USA Event Monitor (Standalone / Direct Memory)
=====================================================
HANYA untuk mendeteksi trigger event 'MOBIL NABRAK' langsung dari
Sega Model 2 Emulator di Windows. Tanpa Arduino, tanpa socket.
"""

import sys
import time

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
else:
    kernel32 = None
    user32 = None


def find_emulator_pid():
    """Mencari PID emulator lewat Judul Jendela (Window) atau Nama Proses."""
    if not IS_WINDOWS:
        return None, "Non-Windows OS"

    # Strategi 1: Cari lewat Window Title (Sangat Akurat)
    window_titles = [
        "Daytona USA",
        "Daytona USA '93 Edition",
        "Daytona USA (Saturn Ads)",
        "Daytona USA Special Edition",
        "Daytona USA Turbo",
        "Model 2 Emulator",
        "EMULATOR"
    ]
    
    for title in window_titles:
        hwnd = user32.FindWindowA(None, title.encode("ascii", errors="ignore"))
        if hwnd:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value > 0:
                return pid.value, f"Jendela Game Ditemukan: '{title}'"

    # Strategi 2: Cari lewat Nama File Proses (.exe)
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

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snapshot != -1:
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        if kernel32.Process32First(snapshot, ctypes.byref(entry)):
            while True:
                name = entry.szExeFile.decode("utf-8", errors="ignore").lower()
                if "emulator" in name:
                    pid_val = entry.th32ProcessID
                    kernel32.CloseHandle(snapshot)
                    return pid_val, f"Proses Ditemukan: '{name}'"
                if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                    break
        kernel32.CloseHandle(snapshot)

    return None, None


def read_byte_from_process(h_process, address):
    """Membaca 1 byte dari virtual memory emulator."""
    buffer = ctypes.c_ubyte()
    bytes_read = ctypes.c_size_t()
    success = kernel32.ReadProcessMemory(
        h_process,
        ctypes.c_void_p(address),
        ctypes.byref(buffer),
        1,
        ctypes.byref(bytes_read)
    )
    if success and bytes_read.value == 1:
        return buffer.value
    return None


def main():
    print("=" * 60)
    print("   DAYTONA USA EVENT MONITOR (Sega Model 2)")
    print("   Fokus: Deteksi Trigger 'MOBIL NABRAK'")
    print("=" * 60)

    if not IS_WINDOWS:
        print("\n[PERINGATAN] Anda sedang menjalankan script ini di macOS/Linux.")
        print("Script ini dirancang untuk membaca RAM emulator di Windows.")
        print("Buka file ini di komputer Windows yang menjalankan Sega Model 2 Emulator!\n")
        return

    # Alamat memori Register Drive Board FFB Daytona USA di Sega Model 2
    # Alamat ini sama persis dengan yang dipakai plugin C++ (M2Emulator.cpp:1136)
    TARGET_ADDRESS = 0x0057285B

    print("\n[1/3] Mencari emulator Sega Model 2...")
    print("      (Pastikan EMULATOR.EXE dan game Daytona USA sudah dibuka!)")

    pid = None
    info = None

    while True:
        pid, info = find_emulator_pid()
        if pid:
            break
        time.sleep(1.0)

    print(f"\n[2/3] BERHASIL TERHUBUNG!")
    print(f"      -> {info} (PID: {pid})")

    # Buka akses memori proses emulator
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    h_process = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

    if not h_process:
        err = kernel32.GetLastError()
        print(f"\n[ERROR] Gagal membuka proses (Error Code: {err})")
        print("SOLUSI: Klik kanan Command Prompt > 'Run as Administrator', lalu jalankan lagi script ini.")
        return

    print(f"[3/3] Monitoring Alamat Memori Drive Board: 0x{TARGET_ADDRESS:08X}")
    print("=" * 60)
    print("Status: MENDENGARKAN EVENT GAME... (Silakan kemudikan mobil)\n")

    prev_ff = 0
    last_crash_tick = 0

    try:
        while True:
            ff = read_byte_from_process(h_process, TARGET_ADDRESS)

            if ff is None:
                # Cek apakah emulator ditutup
                err = kernel32.GetLastError()
                print(f"\n[WARN] Emulator tertutup atau memori tidak terbaca (Error: {err}).")
                break

            # Rentang getaran benturan Sega Model 2 (0x40 s/d 0x47)
            if 0x3F < ff < 0x48:
                now = time.time() * 1000.0
                force = ((ff - 63) / 8.0) * 100.0
                is_new_impact = (prev_ff <= 0x3F or prev_ff >= 0x48)

                # Debounce 350ms agar tidak spam ribuan baris saat bergesekan di tembok
                if is_new_impact and (now - last_crash_tick > 350):
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] >>> MOBIL NABRAK! <<< (Raw Value: 0x{ff:02X} | Kekuatan: {force:.0f}%)")
                    last_crash_tick = now

            prev_ff = ff
            time.sleep(0.016)  # 16 ms = 60 kali per detik

    except KeyboardInterrupt:
        print("\nMonitor dihentikan oleh pengguna.")
    finally:
        kernel32.CloseHandle(h_process)


if __name__ == "__main__":
    main()
