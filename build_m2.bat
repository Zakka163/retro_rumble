@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo  Build Script: retro_rumble (FFBArcadePlugin Win32)
echo ====================================================================

:: 1. Cari lokasi MSBuild otomatis menggunakan vswhere jika tersedia
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "MSBUILD_PATH="

if exist "!VSWHERE!" (
    for /f "usebackq tokens=*" %%i in (`"!VSWHERE!" -latest -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe`) do (
        set "MSBUILD_PATH=%%i"
    )
)

:: Jika vswhere tidak menemukan, coba path umum Visual Studio 2022 & 2019
if not defined MSBUILD_PATH (
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" (
        set "MSBUILD_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe" (
        set "MSBUILD_PATH=C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe"
    ) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe" (
        set "MSBUILD_PATH=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe"
    ) else (
        set "MSBUILD_PATH=msbuild"
    )
)

echo Menggunakan MSBuild: "!MSBUILD_PATH!"
echo.

:: 2. Jalankan Build dengan target Release | Win32
echo [1/3] Menjalankan kompilasi (Release ^| Win32)...
"!MSBUILD_PATH!" "FFBArcadePlugin\Dinput8Wrapper.sln" /p:Configuration=Release /p:Platform=Win32 /t:Restore,Build

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build gagal! Pastikan Visual Studio memiliki workload "Desktop development with C++".
    pause
    exit /b %ERRORLEVEL%
)

:: 3. Siapkan folder output siap pakai (dist\Sega_Model_2)
echo.
echo [2/3] Mengumpulkan file deployment siap pasang...
set "DIST_DIR=dist\Sega_Model_2"
if not exist "!DIST_DIR!" mkdir "!DIST_DIR!"

copy /y "FFBArcadePlugin\Release.Win32\dinput8.dll" "!DIST_DIR!\" >nul
copy /y "FFBArcadePlugin\Release.Win32\SDL2.dll" "!DIST_DIR!\" >nul
copy /y "FFBArcadePlugin\FFBPlugin.ini" "!DIST_DIR!\" >nul

echo.
echo ====================================================================
echo  [SUKSES] Build dan bundling selesai!
echo ====================================================================
echo File siap pakai telah dibuat di folder:
echo   -> !DIST_DIR!\
echo.
echo File yang ada di dalamnya:
echo   1. dinput8.dll      (Plugin wrapper)
echo   2. SDL2.dll         (Library controller/rumble)
echo   3. FFBPlugin.ini    (Config GameId=25 Daytona USA)
echo.
echo LANGKAH TERAKHIR:
echo Salin ketiga file di atas ke dalam folder root Sega Model 2 Emulator Anda,
echo lalu buka EMULATOR.EXE dan jalankan Daytona USA!
echo ====================================================================
echo.
pause
