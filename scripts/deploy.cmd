@echo off
cd C:\Users\danilombsantos\Desktop\Desenvolvimento_Crypto\092025\092025

REM === Cria o executável com PyInstaller ===
pyinstaller --onefile --collect-all dateparser main.py

REM === Caminho do executável final ===
echo Executável gerado em: dist\main.exe

REM === Cria pasta de backup com data atual ===
set _folder=BKP_%date:~-4,4%-%date:~-7,2%-%date:~-10,2%
mkdir "%_folder%"

REM === Move build e dist para a pasta de backup ===
move /Y build "%_folder%"
move /Y dist "%_folder%"

REM === Copia arquivos restantes para o backup (sem copiar a própria pasta de backup e sem arquivos .zip) ===
for %%f in (*.*) do (
    if /I not "%%f"=="%_folder%" (
        if /I not "%%f"==*.zip (
            copy /Y "%%f" "%_folder%"
        )
    )
)

REM === Cria ZIP da pasta de backup (sem incluir outros arquivos .zip) ===
"C:\Program Files\7-Zip\7z.exe" a "%_folder%.zip" "%_folder%\*" -xr!*.zip

REM === Remove pasta de backup após zipar ===
rmdir /s /q "%_folder%"

move /Y "%_folder%.zip" .\backups\

pause
