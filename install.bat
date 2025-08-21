@echo off
echo ========================================
echo  Sistema de Reconhecimento Facial
echo ========================================
echo.

echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo Por favor, instale Python 3.7 ou superior
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python encontrado!
echo.

echo Instalando dependencias...
echo.

REM --> Instalando o .whl do dlib localmente
echo Instalando dlib local (whl)...
pip install dlib-19.22.99-cp310-cp310-win_amd64.whl

echo Instalando outras dependencias...
pip install -r requirements.txt

echo.
echo ========================================
echo  Instalacao concluida!
echo ========================================
echo.
echo Para usar o sistema:
echo Execute: python app.py
echo.
echo Acesse: http://localhost:5000
echo.
echo Pressione qualquer tecla para sair...
pause >nul 