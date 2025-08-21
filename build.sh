#!/bin/bash
set -e

echo "🚀 Iniciando build minimalista para Render..."

# Configurar variáveis de ambiente para otimização
export PIP_NO_CACHE_DIR=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONDONTWRITEBYTECODE=1

# Verificar se estamos no ambiente virtual do Render
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Usando ambiente virtual do Render: $VIRTUAL_ENV"
    PYTHON_CMD="python"
    PIP_CMD="pip"
elif command -v python3.11 &> /dev/null; then
    echo "✅ Python 3.11 encontrado, usando para build..."
    PYTHON_CMD="python3.11"
    PIP_CMD="python3.11 -m pip"
else
    echo "❌ Python 3.11 não encontrado, usando Python padrão"
    PYTHON_CMD="python3"
    PIP_CMD="python3 -m pip"
fi

# Instalar dependências de build primeiro
echo "📦 Instalando dependências de build..."
$PIP_CMD install --upgrade pip setuptools wheel

# Instalar requirements minimalistas com otimizações
echo "🔧 Instalando dependências mínimas do projeto..."
$PIP_CMD install --no-cache-dir --prefer-binary -r requirements_render_minimal.txt

echo "✅ Build minimalista concluído com sucesso!"
echo "📝 NOTA: Reconhecimento facial temporariamente desabilitado para compatibilidade com Render" 