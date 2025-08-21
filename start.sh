#!/bin/bash

echo "🚀 Iniciando aplicação Facial LED no Render..."

# Verificar se estamos no ambiente virtual
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Usando ambiente virtual: $VIRTUAL_ENV"
    PYTHON_CMD="$VIRTUAL_ENV/bin/python"
    GUNICORN_CMD="$VIRTUAL_ENV/bin/gunicorn"
else
    echo "⚠️ Ambiente virtual não detectado, usando Python padrão"
    PYTHON_CMD="python3"
    GUNICORN_CMD="gunicorn"
fi

# Verificar se o gunicorn está disponível
if command -v $GUNICORN_CMD &> /dev/null; then
    echo "✅ Gunicorn encontrado em: $GUNICORN_CMD"
    exec $GUNICORN_CMD --worker-class eventlet -w 1 app_render:app
else
    echo "❌ Gunicorn não encontrado, tentando instalar..."
    $PYTHON_CMD -m pip install gunicorn
    exec $PYTHON_CMD -m gunicorn --worker-class eventlet -w 1 app_render:app
fi 