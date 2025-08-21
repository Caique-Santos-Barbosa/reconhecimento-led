#!/bin/bash
set -e

echo "🚀 Iniciando build personalizado..."

# Verificar versão do Python
python3.11 --version || {
    echo "❌ Python 3.11 não encontrado, tentando Python 3.11"
    python3.11 --version || {
        echo "❌ Python 3.11 não disponível, usando Python padrão"
        python3 --version
        python3 -m pip install --upgrade pip setuptools wheel
        python3 -m pip install -r requirements_render.txt
        exit 0
    }
}

# Usar Python 3.11 se disponível
echo "✅ Python 3.11 encontrado, usando para build..."
python3.11 -m pip install --upgrade pip setuptools wheel
python3.11 -m pip install -r requirements_render.txt

echo "✅ Build concluído com sucesso!" 