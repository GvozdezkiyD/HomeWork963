@echo off
chcp 65001 >nul
title Система проверки приказов МЭР

cd /d "%~dp0"

echo ============================================================
echo   СИСТЕМА ПРОВЕРКИ ПРИКАЗОВ МИНЭКОНОМРАЗВИТИЯ РОССИИ
echo ============================================================
echo.

:: Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python 3.8+ с сайта https://www.python.org
    pause
    exit /b 1
)

:: Проверяем наличие ключевых библиотек
python -c "import torch, transformers, tkinter" >nul 2>&1
if errorlevel 1 (
    echo [!] Установка необходимых библиотек...
    echo     Это может занять несколько минут...
    echo.
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось установить библиотеки
        echo Запустите вручную: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo [OK] Библиотеки установлены
    echo.
)

echo [OK] Запуск программы...
echo     Окно откроется через 1-2 секунды
echo     Модель ИИ загрузится в фоне (10-15 сек)
echo.

python gui_app.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Программа завершилась с ошибкой
    echo Описание ошибки показано выше
    pause
)
