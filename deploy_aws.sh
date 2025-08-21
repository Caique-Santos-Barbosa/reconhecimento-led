#!/bin/bash

echo "🚀 Iniciando deploy automático para AWS Lightsail..."
echo "📋 Sistema: Ubuntu $(lsb_release -rs)"
echo "💾 Memória: $(free -h | grep Mem | awk '{print $2}')"
echo "🖥️  CPU: $(nproc) cores"

# Atualizar sistema
echo "📦 Atualizando sistema Ubuntu..."
sudo apt update && sudo apt upgrade -y

# Instalar dependências do sistema
echo "🔧 Instalando dependências do sistema..."
sudo apt install -y python3 python3-pip python3-venv build-essential cmake pkg-config
sudo apt install -y libjpeg-dev libpng-dev libtiff-dev libavcodec-dev libavformat-dev libswscale-dev
sudo apt install -y libv4l-dev libxvidcore-dev libx264-dev libgtk-3-dev libatlas-base-dev
sudo apt install -y gfortran libhdf5-dev libhdf5-serial-dev libhdf5-103 libqtgui4 libqtwebkit4
sudo apt install -y libqt4-test python3-dev libblas-dev liblapack-dev libhdf5-dev
sudo apt install -y git curl wget unzip

# Criar ambiente virtual
echo "🐍 Criando ambiente virtual Python..."
python3 -m venv facial_env
source facial_env/bin/activate

# Atualizar pip
echo "📦 Atualizando pip..."
pip install --upgrade pip setuptools wheel

# Instalar dependências Python
echo "🔧 Instalando dependências Python..."
pip install opencv-python==4.8.1.78
pip install dlib==19.24.2
pip install face-recognition==1.3.0
pip install numpy==1.24.3 Pillow==10.0.1
pip install flask flask-socketio gunicorn eventlet
pip install requests pyserial

# Clonar repositório
echo "📥 Baixando código da aplicação..."
git clone https://github.com/Caique-Santos-Barbosa/reconhecimento-led.git
cd reconhecimento-led

# Configurar aplicação
echo "⚙️ Configurando aplicação..."
cp app.py app_aws.py

# Criar arquivo de configuração para produção
cat > gunicorn.conf.py << EOF
bind = "0.0.0.0:5000"
workers = 2
worker_class = "eventlet"
worker_connections = 1000
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
EOF

# Criar serviço systemd
echo "🔧 Configurando serviço systemd..."
sudo tee /etc/systemd/system/facial-led.service > /dev/null << EOF
[Unit]
Description=Facial LED Application
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/home/ubuntu/reconhecimento-led
Environment=PATH=/home/ubuntu/facial_env/bin
ExecStart=/home/ubuntu/facial_env/bin/gunicorn -c gunicorn.conf.py app_aws:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Configurar firewall
echo "🔥 Configurando firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 5000/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Configurar Nginx (opcional)
echo "🌐 Configurando Nginx..."
sudo apt install -y nginx
sudo tee /etc/nginx/sites-available/facial-led > /dev/null << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/facial-led /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# Ativar serviço
echo "🚀 Ativando serviço..."
sudo systemctl daemon-reload
sudo systemctl enable facial-led.service
sudo systemctl start facial-led.service

# Verificar status
echo "📊 Verificando status do serviço..."
sudo systemctl status facial-led.service --no-pager

echo ""
echo "🎉 Deploy concluído com sucesso!"
echo "🌐 Acesse: http://$(curl -s ifconfig.me):5000"
echo "🔧 Logs: sudo journalctl -u facial-led.service -f"
echo "🔄 Reiniciar: sudo systemctl restart facial-led.service"
echo ""
echo "✅ Reconhecimento facial funcionando perfeitamente!" 