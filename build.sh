#!/bin/bash
set -e

echo "🚀 Iniciando build minimalista para Render..."

# Configurar variáveis de ambiente para otimização
export PIP_NO_CACHE_DIR=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONDONTWRITEBYTECODE=1

# Verificar versão do Python
python3.11 --version || {
    echo "❌ Python 3.11 não encontrado, tentando Python padrão"
    python3 --version
    python3 -m pip install --upgrade pip setuptools wheel
    python3 -m pip install --no-cache-dir -r requirements_render_minimal.txt
    exit 0
}

# Usar Python 3.11 se disponível
echo "✅ Python 3.11 encontrado, usando para build..."

# Instalar dependências de build primeiro
echo "📦 Instalando dependências de build..."
python3.11 -m pip install --upgrade pip setuptools wheel

# Instalar requirements minimalistas com otimizações
echo "🔧 Instalando dependências mínimas do projeto..."
python3.11 -m pip install --no-cache-dir --prefer-binary -r requirements_render_minimal.txt

echo "✅ Build minimalista concluído com sucesso!"
echo "📝 NOTA: Reconhecimento facial temporariamente desabilitado para compatibilidade com Render" 