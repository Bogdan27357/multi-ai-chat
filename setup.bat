@echo off
chcp 65001 >nul
echo ============================================
echo   Multi-AI Chat — Автоустановка (Windows)
echo ============================================
echo.

:: 1. Python venv
echo [1/5] Создаю виртуальное окружение...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo       Готово.
echo.

:: 2. Python dependencies
echo [2/5] Устанавливаю Python-зависимости...
pip install -r requirements.txt -q
echo       Готово.
echo.

:: 3. Tesseract OCR
echo [3/5] Проверяю Tesseract OCR...
where tesseract >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo       Tesseract не найден. Устанавливаю через winget...
    winget install --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements -e
    if %ERRORLEVEL% neq 0 (
        echo.
        echo  *** winget не сработал. Пробую chocolatey... ***
        where choco >nul 2>&1
        if %ERRORLEVEL% equ 0 (
            choco install tesseract -y
        ) else (
            echo.
            echo  !!! Установите Tesseract вручную: !!!
            echo  https://github.com/UB-Mannheim/tesseract/wiki
            echo  При установке отметьте галочку "Russian" в языках.
            echo  После установки перезапустите терминал.
            echo.
        )
    )
) else (
    echo       Tesseract уже установлен.
)
echo.

:: 4. Ollama
echo [4/5] Проверяю Ollama...
where ollama >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo       Ollama не найдена. Устанавливаю через winget...
    winget install --id Ollama.Ollama --accept-package-agreements --accept-source-agreements -e
    if %ERRORLEVEL% neq 0 (
        echo.
        echo  !!! Установите Ollama вручную: https://ollama.com/download !!!
        echo.
    ) else (
        echo       Ollama установлена. Перезапустите терминал после установки.
    )
) else (
    echo       Ollama уже установлена.
)
echo.

:: 5. Pull model
echo [5/5] Скачиваю модель llama3.1:8b (может занять несколько минут)...
ollama pull llama3.1:8b
echo.

echo ============================================
echo   Установка завершена!
echo ============================================
echo.
echo   Для запуска выполните:
echo     start.bat
echo.
pause
