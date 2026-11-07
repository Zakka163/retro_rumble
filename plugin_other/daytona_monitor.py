#!/usr/bin/env python3
"""
Daytona USA Event & Rumble Monitor (Python Alternative)
======================================================
Membaca memory Sega Model 2 Emulator secara langsung dari luar (tanpa injeksi DLL).
Mendeteksi event getaran benturan (0x40 - 0x47) dan mengeksekusi trigger:
1. Cetak console '>>> MOBIL NABRAK! <<<'
2. Getarkan stik Xbox / XInput langsung via ctypes
3. Kirim event via UDP Socket
4. Kirim trigger ke Arduino via Serial COM Port
"""

import sys
import os
import time
import socket
import configparser

# Cek OS untuk import ctypes Windows
IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    try:
        xinput = ctypes.windll.xinput1_4
    except Exception:
        try:
            xinput = ctypes.windll.xinput1_3
        except Exception:
            xinput = None
else:
    kernel32 = None
    xinput = None

# Struktur XInput untuk getaran controller di Windows
if IS_WINDOWS and xinput:
    class XINPUT_VIBRATION(ctypes.Structure):
        _fields_ = [
            ("wLeftMotorSpeed", wintypes.WORD),
            ("wRightMotorSpeed", wintypes.WORD)
        ]


class ProcessMemoryReader:
    """Membaca virtual memory process Sega Model 2 Emulator via Win32 API."""
    PROCESS_ALL_ACCESS = 0x1F0FFF
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400

    TH32CS_SNAPPROCESS = 0x00000002
    TH32CS_SNAPMODULE = 0x00000008
    TH32CS_SNAPMODULE32 = 0x00000010

    def __init__(self, target_names):
        self.target_names = [name.lower() for name in target_names]
        self.pid = None
        self.h_process = None
        self.base_address = None

    def find_process(self):
        if not IS_WINDOWS:
            return False

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

        snapshot = kernel32.CreateToolhelp32Snapshot(self.TH32CS_SNAPPROCESS, 0)
        if snapshot == -1:
            return False

        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

        found = False
        if kernel32.Process32First(snapshot, ctypes.byref(entry)):
            while True:
                exe_name = entry.szExeFile.decode('utf-8', errors='ignore').lower()
                if exe_name in self.target_names:
                    self.pid = entry.th32ProcessID
                    found = True
                    break
                if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                    break

        kernel32.CloseHandle(snapshot)
        return found

    def open(self):
        if not self.find_process():
            return False

        self.h_process = kernel32.OpenProcess(
            self.PROCESS_VM_READ | self.PROCESS_QUERY_INFORMATION,
            False,
            self.pid
        )
        if not self.h_process:
            return False

        self.base_address = self._get_module_base()
        return True

    def _get_module_base(self):
        class MODULEENTRY32(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD),
                ('th32ModuleID', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD),
                ('GlblcntUsage', wintypes.DWORD),
                ('ProccntUsage', wintypes.DWORD),
                ('modBaseAddr', ctypes.c_void_p),
                ('modBaseSize', wintypes.DWORD),
                ('hModule', wintypes.HMODULE),
                ('szModule', ctypes.c_char * 256),
                ('szExePath', ctypes.c_char * 260)
            ]

        snapshot = kernel32.CreateToolhelp32Snapshot(
            self.TH32CS_SNAPMODULE | self.TH32CS_SNAPMODULE32, self.pid
        )
        if snapshot == -1:
            return 0x00400000  # Default fallback image base Model 2

        entry = MODULEENTRY32()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32)
        base = 0x00400000

        if kernel32.Module32First(snapshot, ctypes.byref(entry)):
            base = entry.modBaseAddr

        kernel32.CloseHandle(snapshot)
        return base

    def read_byte(self, address):
        buffer = ctypes.c_ubyte()
        bytes_read = ctypes.c_size_t()
        success = kernel32.ReadProcessMemory(
            self.h_process,
            ctypes.c_void_p(address),
            ctypes.byref(buffer),
            1,
            ctypes.byref(bytes_read)
        )
        if success and bytes_read.value == 1:
            return buffer.value
        return None

    def close(self):
        if self.h_process:
            kernel32.CloseHandle(self.h_process)
            self.h_process = None


class MockMemoryReader:
    """Simulasi memory untuk pengujian di non-Windows atau saat emulator belum berjalan."""
    def __init__(self):
        self.step = 0
        self.base_address = 0x00400000

    def open(self):
        return True

    def read_byte(self, address):
        self.step += 1
        # Setiap ~60 tick (~1 detik), simulasikan mobil nabrak dengan nilai 0x44 (vibration)
        if (self.step % 60) in (0, 1, 2, 3, 4):
            return 0x44
        return 0x00  # Keadaan normal / jalan lurus

    def close(self):
        pass


def set_controller_vibration(motor_left, motor_right):
    """Menyetel getaran controller Xbox (0 s/d 65535)."""
    if IS_WINDOWS and xinput:
        vib = XINPUT_VIBRATION()
        vib.wLeftMotorSpeed = int(motor_left)
        vib.wRightMotorSpeed = int(motor_right)
        try:
            xinput.XInputSetState(0, ctypes.byref(vib))
        except Exception:
            pass


def main():
    simulate = ("--simulate" in sys.argv) or (not IS_WINDOWS)

    config_path = os.path.join(os.path.dirname(__file__), "config.ini")
    config = configparser.ConfigParser()
    config.read(config_path)

    poll_interval = config.getint("General", "PollIntervalMs", fallback=16) / 1000.0
    debounce_ms = config.getint("General", "CrashDebounceMs", fallback=350)
    process_names = config.get("General", "ProcessNames", fallback="EMULATOR.EXE,EMULATOR_MULTICPU.EXE").split(",")

    enable_xinput = config.getboolean("Hardware_Rumble", "EnableXInputRumble", fallback=True)
    enable_udp = config.getboolean("Hardware_Rumble", "EnableUDP", fallback=True)
    udp_host = config.get("Hardware_Rumble", "UDPHost", fallback="127.0.0.1")
    udp_port = config.getint("Hardware_Rumble", "UDPPort", fallback=9999)

    enable_serial = config.getboolean("Hardware_Rumble", "EnableSerial", fallback=False)
    serial_port = config.get("Hardware_Rumble", "SerialPort", fallback="COM3")
    serial_baud = config.getint("Hardware_Rumble", "SerialBaud", fallback=115200)

    # Inisialisasi Serial COM (Arduino) jika diaktifkan
    ser = None
    if enable_serial:
        try:
            import serial
            ser = serial.Serial(serial_port, serial_baud, timeout=0.1)
            print(f"[SERIAL] Terhubung ke Arduino di {serial_port}")
        except Exception as e:
            print(f"[SERIAL] Gagal membuka port {serial_port}: {e}")

    # Inisialisasi UDP Socket
    udp_sock = None
    if enable_udp:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"[UDP] Siap broadcast event ke {udp_host}:{udp_port}")

    print("=" * 65)
    print("   DAYTONA USA EVENT & RUMBLE MONITOR (Python Engine)")
    print("=" * 65)

    if simulate:
        print("[MODE] SIMULASI (Mock Mode) Aktif.")
        print("       (Mobil disimulasikan menabrak dinding secara periodik)")
        reader = MockMemoryReader()
    else:
        print("[MODE] Mencari proses emulator: " + ", ".join(process_names) + "...")
        reader = ProcessMemoryReader(process_names)

    while True:
        if not reader.open():
            time.sleep(1.0)
            continue

        print("\n[OK] Terhubung ke Sega Model 2 Emulator!")
        print(f"     Base Address: 0x{reader.base_address:08X}")
        # Offset Drive Board Model 2 = 0x17285B
        target_addr = reader.base_address + 0x17285B
        print(f"     Monitoring FFB Drive Register: 0x{target_addr:08X}\n")

        prev_ff = 0
        last_crash_time = 0

        try:
            while True:
                ff = reader.read_byte(target_addr)
                if ff is None:
                    print("[WARN] Emulator tertutup atau memory tidak dapat dibaca.")
                    break

                # Deteksi benturan: nilai register uncentering/rumble (0x40 - 0x47)
                if 0x3F < ff < 0x48:
                    now = time.time() * 1000.0
                    force_percent = ((ff - 63) / 8.0) * 100.0
                    is_new_impact = (prev_ff <= 0x3F or prev_ff >= 0x48)

                    if is_new_impact and (now - last_crash_time > debounce_ms):
                        timestamp = time.strftime("%H:%M:%S")
                        print(f"[{timestamp}] [TRIGGER] >>> MOBIL NABRAK! <<< (Raw: 0x{ff:02X} | Force: {force_percent:.0f}%)")

                        # 1. Trigger Getaran Gamepad Xbox
                        if enable_xinput:
                            motor_strength = int((force_percent / 100.0) * 65535)
                            set_controller_vibration(motor_strength, motor_strength)

                        # 2. Trigger UDP Socket
                        if udp_sock:
                            payload = f"CRASH:{force_percent:.1f}".encode("utf-8")
                            try:
                                udp_sock.sendto(payload, (udp_host, udp_port))
                            except Exception:
                                pass

                        # 3. Trigger Serial Arduino
                        if ser and ser.is_open:
                            try:
                                ser.write(b"C\n")  # 'C' = Crash signal
                            except Exception:
                                pass

                        last_crash_time = now
                else:
                    # Matikan getaran jika sudah tidak nabrak
                    if enable_xinput and (prev_ff > 0x3F and prev_ff < 0x48):
                        set_controller_vibration(0, 0)

                prev_ff = ff
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\nMonitor dihentikan oleh pengguna.")
            break
        finally:
            reader.close()
            if enable_xinput:
                set_controller_vibration(0, 0)


if __name__ == "__main__":
    main()
