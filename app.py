from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, send_file, session
from flask_socketio import SocketIO, emit
import os
from werkzeug.utils import secure_filename
import threading
import cv2
import face_recognition
import numpy as np
import base64
import time
from PIL import Image
import io
import requests
import json
from datetime import datetime, timedelta
from shutil import rmtree
from flask import session as flask_session
import mimetypes
import unicodedata
from functools import wraps

app = Flask(__name__)
app.secret_key = 'Gds2024aa@@_PainelFacial_2024_!@#_Un1c0_S3gr3d0'  # Chave secreta forte para sessões Flask
app.config['UPLOAD_FOLDER'] = 'static/videos'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['USERS_FOLDER'] = 'static/users'
socketio = SocketIO(app, cors_allowed_origins="*")

# Criar diretórios necessários
for folder in [app.config['UPLOAD_FOLDER'], app.config['USERS_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- Sistema de Licenciamento ---
LICENCA_PATH = 'licenca.json'
ADMIN_MASTER_PASSWORD = 'Gds2024aa@@'

def load_licenca():
    if not os.path.exists(LICENCA_PATH):
        return {'tipo': 'indeterminado'}
    with open(LICENCA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_licenca(data):
    with open(LICENCA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def licenca_status():
    lic = load_licenca()
    if lic.get('bloqueio_imediato'):
        return {'status': 'expirada', 'mensagem': 'Sistema bloqueado imediatamente pelo administrador.', 'licenca': lic}
    now = datetime.now().date()
    if lic.get('tipo') == 'indeterminado':
        return {'status': 'ok', 'mensagem': 'Licença indeterminada', 'licenca': lic}
    elif lic.get('tipo') == 'data_fixa':
        data_exp = datetime.strptime(lic.get('data_expiracao'), '%Y-%m-%d').date()
        if now > data_exp:
            return {'status': 'expirada', 'mensagem': 'Licença expirada em ' + data_exp.strftime('%d/%m/%Y'), 'licenca': lic}
        else:
            dias = (data_exp - now).days
            return {'status': 'ok', 'mensagem': f'Licença válida até {data_exp.strftime("%d/%m/%Y")} ({dias} dias restantes)', 'licenca': lic}
    elif lic.get('tipo') == 'dias':
        dias_rest = lic.get('dias_restantes', 0)
        data_ativacao = lic.get('data_ativacao')
        if data_ativacao:
            ativacao = datetime.strptime(data_ativacao, '%Y-%m-%dT%H:%M:%S')
            expira = ativacao + timedelta(days=dias_rest)
            agora = datetime.now()
            segundos_restantes = int((expira - agora).total_seconds())
            lic['segundos_restantes'] = max(0, segundos_restantes)
        else:
            lic['segundos_restantes'] = dias_rest * 24 * 3600
        ultima = lic.get('data_ultima_validacao')
        if ultima:
            ultima = datetime.strptime(ultima, '%Y-%m-%d').date()
            if ultima < now:
                dias_rest -= (now - ultima).days
                lic['dias_restantes'] = dias_rest
                lic['data_ultima_validacao'] = now.strftime('%Y-%m-%d')
                save_licenca(lic)
        if dias_rest < 0 or lic.get('segundos_restantes', 1) <= 0:
            return {'status': 'expirada', 'mensagem': 'Licença expirada (dias esgotados)', 'licenca': lic}
        return {'status': 'ok', 'mensagem': f'Licença válida por {dias_rest} dias', 'licenca': lic}
    return {'status': 'expirada', 'mensagem': 'Licença inválida', 'licenca': lic}

def require_licenca(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        status = licenca_status()
        if status['status'] != 'ok':
            if request.path.startswith('/painel'):
                return render_template('painel_bloqueado.html', mensagem=status['mensagem'])
            elif request.path.startswith('/user_mode'):
                return render_template('painel_bloqueado.html', mensagem=status['mensagem'])
            elif request.path.startswith('/api/porta/abrir') or request.path.startswith('/api/user_recognition'):
                return jsonify({'status': 'error', 'message': status['mensagem'], 'licenca': status['licenca']}), 403
        return f(*args, **kwargs)
    return decorated

# --- Sistema de Reconhecimento Facial ---
class FacialRecognitionSystem:
    def __init__(self, socketio=None):
        self.known_face_encodings = []
        self.known_face_names = []
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.process_this_frame = True
        self.last_recognition_time = {}
        self.recognition_cooldown = 5
        self.socketio = socketio
        print("Reconhecimento facial integrado ao servidor!")

    def load_known_faces(self):
        users_dir = app.config['USERS_FOLDER']
        self.known_face_encodings = []
        self.known_face_names = []
        print("Carregando rostos conhecidos dos usuários...")
        for email in os.listdir(users_dir):
            user_dir = os.path.join(users_dir, email)
            foto_path = os.path.join(user_dir, 'foto.jpg')
            if os.path.exists(foto_path):
                try:
                    image = face_recognition.load_image_file(foto_path)
                    face_encoding = face_recognition.face_encodings(image)[0]
                    usuario = carregar_usuario(email)
                    nome = usuario.nome if usuario else email
                    self.known_face_encodings.append(face_encoding)
                    self.known_face_names.append(nome)
                    print(f"Rosto carregado: {nome}")
                except Exception as e:
                    print(f"Erro ao carregar {foto_path}: {e}")
        print(f"Total de rostos carregados: {len(self.known_face_names)}")

class UserProfile:
    def __init__(self, nome, email, cargo=None):
        self.nome = nome
        self.email = email
        self.cargo = cargo
        self.foto = None
        self.musica_personalizada = None
        self.fundo_personalizado = None
        self.tipo_fundo = 'video'  # ou 'imagem'
        self.data_cadastro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.ultimo_acesso = None
        self.permissoes = {
            'acesso_24h': False,
            'acesso_restrito': False,
            'horario_inicio': '08:00',
            'horario_fim': '18:00'
        }

    def to_dict(self):
        return {
            'nome': self.nome,
            'email': self.email,
            'cargo': self.cargo,
            'foto': self.foto,
            'musica_personalizada': self.musica_personalizada,
            'fundo_personalizado': self.fundo_personalizado,
            'tipo_fundo': self.tipo_fundo,
            'data_cadastro': self.data_cadastro,
            'ultimo_acesso': self.ultimo_acesso,
            'permissoes': self.permissoes
        }

    @classmethod
    def from_dict(cls, data):
        user = cls(data['nome'], data['email'], data.get('cargo'))
        user.foto = data.get('foto')
        user.musica_personalizada = data.get('musica_personalizada')
        user.fundo_personalizado = data.get('fundo_personalizado')
        user.tipo_fundo = data.get('tipo_fundo', 'video')
        user.data_cadastro = data.get('data_cadastro')
        user.ultimo_acesso = data.get('ultimo_acesso')
        user.permissoes = data.get('permissoes', {})
        return user

# Funções de gerenciamento de usuários
def salvar_usuario(usuario):
    user_dir = os.path.join(app.config['USERS_FOLDER'], usuario.email)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    
    with open(os.path.join(user_dir, 'profile.json'), 'w', encoding='utf-8') as f:
        json.dump(usuario.to_dict(), f, ensure_ascii=False, indent=2)

def carregar_usuario(email):
    user_dir = os.path.join(app.config['USERS_FOLDER'], email)
    profile_path = os.path.join(user_dir, 'profile.json')
    
    if os.path.exists(profile_path):
        with open(profile_path, 'r', encoding='utf-8') as f:
            return UserProfile.from_dict(json.load(f))
    return None

def listar_usuarios():
    usuarios = []
    for email in os.listdir(app.config['USERS_FOLDER']):
        usuario = carregar_usuario(email)
        if usuario:
            usuarios.append(usuario.to_dict())
    return usuarios

# Rotas para gerenciamento de usuários
@app.route('/api/usuarios', methods=['GET'])
def api_listar_usuarios():
    return jsonify({'usuarios': listar_usuarios()})

@app.route('/api/usuarios', methods=['POST'])
def api_criar_usuario():
    data = request.get_json()
    nome = data.get('nome')
    email = data.get('email')
    cargo = data.get('cargo')
    
    if not nome or not email:
        return jsonify({'status': 'error', 'message': 'Nome e email são obrigatórios'})
    
    if carregar_usuario(email):
        return jsonify({'status': 'error', 'message': 'Usuário já existe'})
    
    usuario = UserProfile(nome, email, cargo)
    salvar_usuario(usuario)
    return jsonify({'status': 'success', 'message': 'Usuário criado com sucesso'})

@app.route('/api/usuarios/<email>', methods=['GET'])
def api_obter_usuario(email):
    usuario = carregar_usuario(email)
    if usuario:
        return jsonify({'status': 'success', 'usuario': usuario.to_dict()})
    return jsonify({'status': 'error', 'message': 'Usuário não encontrado'})

@app.route('/api/usuarios/<email>', methods=['PUT'])
def api_atualizar_usuario(email):
    usuario = carregar_usuario(email)
    if not usuario:
        return jsonify({'status': 'error', 'message': 'Usuário não encontrado'})
    
    data = request.get_json()
    user_dir = os.path.join(app.config['USERS_FOLDER'], email)
    if 'nome' in data:
        usuario.nome = data['nome']
    if 'cargo' in data:
        usuario.cargo = data['cargo']
    if 'permissoes' in data:
        usuario.permissoes.update(data['permissoes'])
    if 'tipo_fundo' in data:
        usuario.tipo_fundo = data['tipo_fundo']
    # Remover foto
    if data.get('removerFoto'):
        usuario.foto = None
        foto_path = os.path.join(user_dir, 'foto.jpg')
        if os.path.exists(foto_path):
            os.remove(foto_path)
    # Remover música personalizada
    if data.get('removerMusica'):
        usuario.musica_personalizada = None
        musica_path = os.path.join(user_dir, 'musica.mp3')
        if os.path.exists(musica_path):
            os.remove(musica_path)
    # Remover fundo personalizado
    if data.get('removerFundo'):
        usuario.fundo_personalizado = None
        for ext in ['mp4', 'jpg', 'png']:
            fundo_path = os.path.join(user_dir, f'fundo.{ext}')
            if os.path.exists(fundo_path):
                os.remove(fundo_path)
    # NÃO sobrescreva fundo_personalizado nem tipo_fundo se não for para remover!
    salvar_usuario(usuario)
    return jsonify({'status': 'success', 'message': 'Usuário atualizado com sucesso'})

@app.route('/api/usuarios/<email>/foto', methods=['POST'])
def api_upload_foto_usuario(email):
    usuario = carregar_usuario(email)
    if not usuario:
        return jsonify({'status': 'error', 'message': 'Usuário não encontrado'})
    
    data = request.get_json()
    imagem = data.get('imagem')
    if not imagem:
        return jsonify({'status': 'error', 'message': 'Imagem não enviada'})
    
    try:
        user_dir = os.path.join(app.config['USERS_FOLDER'], email)
        img_bytes = base64.b64decode(imagem.split(',')[1])
        path = os.path.join(user_dir, 'foto.jpg')
        with open(path, 'wb') as f:
            f.write(img_bytes)
        
        usuario.foto = f'/static/users/{email}/foto.jpg'
        salvar_usuario(usuario)
        return jsonify({'status': 'success', 'message': 'Foto atualizada com sucesso', 'foto': usuario.foto})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/usuarios/<email>/midia', methods=['POST'])
def api_upload_midia_usuario(email):
    usuario = carregar_usuario(email)
    if not usuario:
        return jsonify({'status': 'error', 'message': 'Usuário não encontrado'})
    
    data = request.get_json()
    tipo = data.get('tipo')  # 'musica' ou 'fundo'
    arquivo = data.get('arquivo')
    if not arquivo:
        return jsonify({'status': 'error', 'message': 'Arquivo não enviado'})
    
    try:
        user_dir = os.path.join(app.config['USERS_FOLDER'], email)
        file_bytes = base64.b64decode(arquivo.split(',')[1])
        
        if tipo == 'musica':
            path = os.path.join(user_dir, 'musica.mp3')
            usuario.musica_personalizada = f'/static/users/{email}/musica.mp3'
            with open(path, 'wb') as f:
                f.write(file_bytes)
            salvar_usuario(usuario)
            return jsonify({'status': 'success', 'message': 'Música atualizada com sucesso', 'musica_personalizada': usuario.musica_personalizada})
        else:  # fundo
            ext = 'mp4' if data.get('tipo_fundo') == 'video' else 'jpg'
            path = os.path.join(user_dir, f'fundo.{ext}')
            usuario.fundo_personalizado = f'/static/users/{email}/fundo.{ext}'
            usuario.tipo_fundo = data.get('tipo_fundo', 'video')
            with open(path, 'wb') as f:
                f.write(file_bytes)
            salvar_usuario(usuario)
            return jsonify({'status': 'success', 'message': 'Fundo atualizado com sucesso', 'fundo_personalizado': usuario.fundo_personalizado, 'tipo_fundo': usuario.tipo_fundo})
    except Exception as e:
        import traceback
        print("Erro detalhado ao salvar fundo:", traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/usuarios/<email>', methods=['DELETE'])
def api_remover_usuario(email):
    user_dir = os.path.join(app.config['USERS_FOLDER'], email)
    if os.path.exists(user_dir):
        try:
            rmtree(user_dir)
            return jsonify({'status': 'success', 'message': 'Usuário removido com sucesso'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    else:
        return jsonify({'status': 'error', 'message': 'Usuário não encontrado'})

# Iniciar reconhecimento facial
facial_system = FacialRecognitionSystem(socketio)
facial_system.load_known_faces()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    files = request.files.getlist('videos')
    saved = []
    for file in files:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        saved.append(filename)
    return jsonify({'uploaded': saved})

@app.route('/videos')
def list_videos():
    files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.mp4')]
    return jsonify({'videos': files})

@app.route('/static/videos/<filename>')
def serve_video(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/boas_vindas', methods=['POST'])
def boas_vindas():
    data = request.json
    nome = data.get('nome')
    foto = data.get('foto')  # base64 ou url
    print(f"[SOCKETIO] Emitindo boas-vindas para {nome}")
    socketio.emit('boas_vindas', {'nome': nome, 'foto': foto})
    return jsonify({'status': 'ok'})

@app.route('/api/user_recognition', methods=['POST'])
@require_licenca
def user_recognition():
    data = request.get_json()
    image_data = data.get('image')
    if not image_data:
        return jsonify({'status': 'error', 'message': 'Imagem não enviada'})
    try:
        image_bytes = base64.b64decode(image_data.split(',')[1])
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        for face_encoding, loc in zip(face_encodings, face_locations):
            matches = facial_system.known_face_encodings and face_recognition.compare_faces(facial_system.known_face_encodings, face_encoding, tolerance=0.6)
            name = None
            if True in matches:
                first_match_index = matches.index(True)
                name = facial_system.known_face_names[first_match_index]
                # Buscar perfil do usuário pelo nome
                usuarios = listar_usuarios()
                perfil = next((u for u in usuarios if u['nome'] == name), None)
                foto_url = perfil['foto'] if perfil and perfil['foto'] else f'/static/known_faces/{name}.jpg'
                # Dispara evento de boas-vindas com dados personalizados
                socketio.emit('boas_vindas', {
                    'nome': name,
                    'foto': foto_url,
                    'musica': perfil['musica_personalizada'] if perfil else None,
                    'fundo': perfil['fundo_personalizado'] if perfil else None,
                    'tipo_fundo': perfil['tipo_fundo'] if perfil else 'video'
                })
                abrir_porta()
                registrar_acesso(name, 'Acesso concedido')
                return jsonify({'status': 'success', 'name': name})
        return jsonify({'status': 'fail'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/admin_mode')
def admin_mode():
    return render_template('admin_mode.html')

# Configurações da API da porta
PORTA_BASE_URL = "http://187.50.63.194:8080"
LOGIN_URL = f"{PORTA_BASE_URL}/ACT_ID_1"
PORTA_URL = f"{PORTA_BASE_URL}/ACT_ID_701"

def check_porta_connectivity():
    """Verifica se o servidor da porta está acessível"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('187.50.63.194', 8080))
        sock.close()
        return result == 0
    except:
        return False

def get_porta_session():
    session = requests.Session()
    login_data = {
        "username": "abc",
        "pwd": "123",
        "logId": "20101222"
    }
    try:
        # Etapa 1: login e salvar cookie
        print(f"Tentando conectar com {LOGIN_URL}")
        login_resp = session.post(LOGIN_URL, data=login_data, timeout=3)
        print("Login status:", login_resp.status_code)
        print("Cookies após login:", session.cookies.get_dict())
        return session
    except requests.exceptions.ConnectTimeout:
        print(f"Timeout ao conectar com {LOGIN_URL}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"Erro de conexão com {LOGIN_URL}: {e}")
        return None
    except Exception as e:
        print(f"Erro ao fazer login: {e}")
        return None

@app.route('/api/porta/abrir', methods=['POST'])
@require_licenca
def abrir_porta():
    # Verificar conectividade primeiro
    if not check_porta_connectivity():
        print("Servidor da porta não está acessível - usando modo simulação")
        # Modo simulação - registrar o acesso mas não abrir a porta fisicamente
        registrar_acesso("Administrador", "Acesso simulado (servidor da porta offline)")
        return jsonify({
            "message": "Acesso registrado (modo simulação - servidor da porta offline)",
            "simulation": True
        })
    
    try:
        session = get_porta_session()
        if not session:
            return jsonify({"error": "Erro ao autenticar - Servidor da porta não está acessível"}), 500

        # Etapa 2: acionar porta usando cookie
        porta_data = {
            "UNCLOSE1": "Remote Open #1 Door"
        }
        porta_resp = session.post(PORTA_URL, data=porta_data, timeout=3)
        print("Porta status:", porta_resp.status_code)
        print("Resposta porta:", porta_resp.text)

        if porta_resp.status_code == 200:
            registrar_acesso("Administrador", "Acesso autorizado")
            return jsonify({"message": "Porta aberta com sucesso"})
        else:
            return jsonify({"error": f"Erro ao abrir porta - Status: {porta_resp.status_code}"}), 500
    except requests.exceptions.ConnectTimeout:
        print("Timeout ao conectar com servidor da porta")
        return jsonify({"error": "Timeout ao conectar com servidor da porta (187.50.63.194:8080)"}), 500
    except requests.exceptions.ConnectionError:
        print("Erro de conexão com servidor da porta")
        return jsonify({"error": "Servidor da porta não está acessível (187.50.63.194:8080)"}), 500
    except Exception as e:
        print("Erro ao abrir porta:", e)
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@app.route('/api/porta/fechar', methods=['POST'])
def fechar_porta():
    try:
        session = get_porta_session()
        if not session:
            return jsonify({"error": "Erro ao autenticar"}), 500

        # Etapa 2: acionar porta usando cookie
        porta_data = {
            "UNCLOSE1": "Remote Close #1 Door"
        }
        porta_resp = session.post(PORTA_URL, data=porta_data, timeout=3)
        print("Porta status:", porta_resp.status_code)
        print("Resposta porta:", porta_resp.text)

        if porta_resp.status_code == 200:
            return jsonify({"message": "Porta fechada com sucesso"})
        else:
            return jsonify({"error": "Erro ao fechar porta"}), 500
    except Exception as e:
        print("Erro ao fechar porta:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/porta/status', methods=['GET'])
def status_porta():
    try:
        # Verificar conectividade
        conectividade = check_porta_connectivity()
        
        if not conectividade:
            return jsonify({
                "status": "offline", 
                "message": "Servidor da porta não está acessível",
                "connectivity": False
            })
        
        session = get_porta_session()
        if not session:
            return jsonify({
                "status": "error", 
                "message": "Erro ao autenticar",
                "connectivity": True
            }), 500

        # Consultar status da porta
        status_resp = session.get(f"{PORTA_BASE_URL}/ACT_ID_702", timeout=3)
        print("Status porta:", status_resp.status_code)
        print("Resposta status:", status_resp.text)

        if status_resp.status_code == 200:
            # Aqui você pode adicionar a lógica para interpretar a resposta
            # e determinar o status real da porta
            return jsonify({
                "status": "online", 
                "message": status_resp.text,
                "connectivity": True
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Erro ao obter status da porta",
                "connectivity": True
            }), 500
    except Exception as e:
        print("Erro ao verificar status:", e)
        return jsonify({
            "status": "error", 
            "message": str(e),
            "connectivity": check_porta_connectivity()
        }), 500

# --- Histórico de acessos (JSON) ---
HISTORICO_PATH = 'acessos.json'

def registrar_acesso(nome, status):
    foto_url = f'/static/known_faces/{nome}.jpg' if os.path.exists(f'static/known_faces/{nome}.jpg') else None
    registro = {
        'nome': nome,
        'foto': foto_url,
        'status': status,
        'datahora': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    try:
        if os.path.exists(HISTORICO_PATH):
            with open(HISTORICO_PATH, 'r', encoding='utf-8') as f:
                historico = json.load(f)
        else:
            historico = []
        historico.insert(0, registro)
        with open(HISTORICO_PATH, 'w', encoding='utf-8') as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print('Erro ao registrar acesso:', e)

@app.route('/api/historico_acessos')
def api_historico_acessos():
    try:
        if os.path.exists(HISTORICO_PATH):
            with open(HISTORICO_PATH, 'r', encoding='utf-8') as f:
                historico = json.load(f)
        else:
            historico = []
        return jsonify({'historico': historico})
    except Exception as e:
        return jsonify({'historico': [], 'erro': str(e)})

# --- Upload de rosto ---
@app.route('/api/upload_rosto', methods=['POST'])
def api_upload_rosto():
    data = request.get_json()
    nome = data.get('nome')
    imagem = data.get('imagem')
    if not nome or not imagem:
        return jsonify({'status': 'error', 'message': 'Nome e imagem são obrigatórios'})
    try:
        img_bytes = base64.b64decode(imagem.split(',')[1])
        path = f'static/known_faces/{nome}.jpg'
        with open(path, 'wb') as f:
            f.write(img_bytes)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- Remover rosto ---
@app.route('/api/remover_rosto', methods=['POST'])
def api_remover_rosto():
    data = request.get_json()
    nome = data.get('nome')
    path = f'static/known_faces/{nome}.jpg'
    try:
        if os.path.exists(path):
            os.remove(path)
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Arquivo não encontrado'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- Upload de logo ---
@app.route('/api/upload_logo', methods=['POST'])
def api_upload_logo():
    data = request.get_json()
    imagem = data.get('image')
    if not imagem:
        return jsonify({'status': 'error', 'message': 'Imagem não enviada'})
    try:
        img_bytes = base64.b64decode(imagem.split(',')[1])
        path = 'static/logo.png'
        with open(path, 'wb') as f:
            f.write(img_bytes)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- Playlist e upload de vídeos de fundo ---
PLAYLIST_PATH = 'static/videos/playlist.json'
VIDEOS_DIR = 'static/videos'

@app.route('/api/playlist', methods=['GET'])
def api_playlist_get():
    videos = [f for f in os.listdir(VIDEOS_DIR) if f.lower().endswith(('.mp4', '.webm', '.mov', '.avi'))]
    playlist = []
    if os.path.exists(PLAYLIST_PATH):
        with open(PLAYLIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            playlist = data.get('playlist', [])
            # Garantir que todos os vídeos na playlist ainda existem
            playlist = [v for v in playlist if os.path.exists(os.path.join(VIDEOS_DIR, v))]
    return jsonify({'videos': videos, 'playlist': playlist})

@app.route('/api/playlist', methods=['POST'])
def api_playlist_post():
    data = request.get_json()
    playlist = data.get('playlist', [])
    
    # Validar se todos os vídeos existem
    valid_playlist = []
    for video in playlist:
        if os.path.exists(os.path.join(VIDEOS_DIR, video)):
            valid_playlist.append(video)
    
    with open(PLAYLIST_PATH, 'w', encoding='utf-8') as f:
        json.dump({'playlist': valid_playlist}, f, ensure_ascii=False, indent=2)
    
    # Emitir evento para atualizar todos os painéis
    socketio.emit('playlist_updated', {'playlist': valid_playlist})
    
    return jsonify({'status': 'success', 'message': 'Playlist atualizada com sucesso'})

@app.route('/api/upload_video', methods=['POST'])
def api_upload_video():
    if 'videos' not in request.files:
        return jsonify({'status': 'error', 'message': 'Arquivo não enviado'})
    
    files = request.files.getlist('videos')
    uploaded_files = []
    
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(VIDEOS_DIR, filename)
            file.save(save_path)
            uploaded_files.append(filename)
    
    if uploaded_files:
        return jsonify({'status': 'success', 'message': f'{len(uploaded_files)} vídeos enviados com sucesso'})
    return jsonify({'status': 'error', 'message': 'Nenhum vídeo válido enviado'})

# Configurações de volume
VOLUME_CONFIG_FILE = 'volume_config.json'

def load_volume_config():
    try:
        if os.path.exists(VOLUME_CONFIG_FILE):
            with open(VOLUME_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar configurações de volume: {e}")
    return {"volume_videos": 100, "volume_musicas": 100}

def save_volume_config(config):
    try:
        with open(VOLUME_CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Erro ao salvar configurações de volume: {e}")

@app.route('/api/configuracoes/volume', methods=['GET'])
def get_volume_config():
    config = load_volume_config()
    return jsonify(config)

@app.route('/api/configuracoes/volume', methods=['POST'])
def set_volume_config():
    try:
        data = request.get_json()
        config = {
            "volume_videos": int(data.get('volume_videos', 100)),
            "volume_musicas": int(data.get('volume_musicas', 100))
        }
        save_volume_config(config)
        # Emitir evento para todos os clientes conectados
        socketio.emit('volume_config', config)
        return jsonify({"message": "Configurações salvas com sucesso"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Modificar a rota de boas-vindas para incluir os volumes
@socketio.on('connect')
def handle_connect():
    config = load_volume_config()
    socketio.emit('volume_config', config)

@app.route('/api/simular_autenticacao/<email>', methods=['POST'])
def simular_autenticacao(email):
    usuario = carregar_usuario(email)
    if not usuario:
        return jsonify({'status': 'error', 'message': 'Usuário não encontrado'})
    perfil = usuario.to_dict()
    foto_url = perfil['foto'] if perfil['foto'] else f'/static/users/{email}/foto.jpg'
    socketio.emit('boas_vindas', {
        'nome': perfil['nome'],
        'foto': foto_url,
        'musica': perfil['musica_personalizada'],
        'fundo': perfil['fundo_personalizado'],
        'tipo_fundo': perfil['tipo_fundo']
    })
    return jsonify({'status': 'success', 'message': 'Simulação enviada'})

# --- Configuração de horário dos vídeos de fundo ---
HORARIO_VIDEOS_PATH = 'horario_videos.json'

@app.route('/api/configuracoes/horario_videos', methods=['GET'])
def get_horario_videos():
    if os.path.exists(HORARIO_VIDEOS_PATH):
        with open(HORARIO_VIDEOS_PATH, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({'inicio': '', 'fim': '', 'dias': []})

@app.route('/api/configuracoes/horario_videos', methods=['POST'])
def set_horario_videos():
    data = request.get_json()
    inicio = data.get('inicio', '')
    fim = data.get('fim', '')
    dias = data.get('dias', [])
    try:
        with open(HORARIO_VIDEOS_PATH, 'w', encoding='utf-8') as f:
            json.dump({'inicio': inicio, 'fim': fim, 'dias': dias}, f, ensure_ascii=False, indent=2)
        # Emitir evento para todos os painéis conectados
        socketio.emit('horario_videos_config', {'inicio': inicio, 'fim': fim, 'dias': dias})
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

painel_status = {
    'video_atual': None,
    'idx': 0,
    'playlist': [],
    'horario': {'inicio': '', 'fim': '', 'dias': []},
    'volume_videos': 100,
    'status': 'desconhecido',
    'tempo_restante_video': 0,
    'tempo_restante_horario': 0,
    'dia_atual': '',
    'hora_atual': '',
}

@app.route('/api/painel_status', methods=['GET', 'POST'])
def api_painel_status():
    global painel_status
    if request.method == 'POST':
        data = request.get_json()
        print('[PAINEL_STATUS] Recebido:', data)
        painel_status.update(data)
        return jsonify({'status': 'ok'})
    return jsonify(painel_status)

@app.route('/api/video/<filename>', methods=['DELETE'])
def api_delete_video(filename):
    from werkzeug.utils import secure_filename
    filename_url = filename
    filename = secure_filename(filename)
    path = os.path.join('static/videos', filename)
    print(f'[DELETE VIDEO] Solicitado: {filename_url} | Secure: {filename} | Path: {path}')
    arquivos = os.listdir('static/videos')
    print(f'[DELETE VIDEO] Arquivos na pasta: {arquivos}')
    # Busca ultra-flexível (ignora espaços, hífens, underlines, acentos, case)
    def normalizar_nome(nome):
        nome = nome.lower()
        nome = nome.replace(' ', '').replace('-', '').replace('_', '')
        nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
        return nome
    nome_base = normalizar_nome(filename)
    arquivo_real = None
    for arq in arquivos:
        if normalizar_nome(arq) == nome_base:
            arquivo_real = arq
            break
    if not arquivo_real:
        print(f'[DELETE VIDEO] Arquivo não encontrado (busca ultra-flexível): {filename}')
        return jsonify({'status': 'error', 'message': 'Arquivo não encontrado'}), 404
    path_real = os.path.join('static/videos', arquivo_real)
    try:
        if os.path.exists(path_real):
            os.remove(path_real)
            print(f'[DELETE VIDEO] Removido: {path_real}')
            return jsonify({'status': 'success'})
        else:
            print(f'[DELETE VIDEO] Arquivo não encontrado (path): {path_real}')
            return jsonify({'status': 'error', 'message': 'Arquivo não encontrado'}), 404
    except Exception as e:
        print(f'[DELETE VIDEO] Erro ao remover {path_real}: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/admin_master', methods=['GET', 'POST'])
def admin_master_login():
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha == ADMIN_MASTER_PASSWORD:
            session['admin_master'] = True
            return redirect(url_for('admin_master_painel'))
        return render_template('admin_master_login.html', erro='Senha incorreta')
    return render_template('admin_master_login.html')

@app.route('/admin_master/painel', methods=['GET', 'POST'])
def admin_master_painel():
    if not session.get('admin_master'):
        return redirect(url_for('admin_master_login'))
    lic = load_licenca()
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        if tipo == 'indeterminado':
            lic = {'tipo': 'indeterminado'}
        elif tipo == 'data_fixa':
            data_exp = request.form.get('data_expiracao')
            lic = {'tipo': 'data_fixa', 'data_expiracao': data_exp}
        elif tipo == 'dias':
            dias = int(request.form.get('dias_restantes', 0))
            lic = {
                'tipo': 'dias',
                'dias_restantes': dias,
                'data_ultima_validacao': datetime.now().strftime('%Y-%m-%d'),
                'data_ativacao': datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            }
        save_licenca(lic)
        return render_template('admin_master_painel.html', licenca=lic, mensagem='Licença atualizada com sucesso!')
    return render_template('admin_master_painel.html', licenca=lic)

@app.route('/admin_master/logout')
def admin_master_logout():
    session.pop('admin_master', None)
    return redirect(url_for('admin_master_login'))

@app.route('/api/licenca_status')
def api_licenca_status():
    return jsonify(licenca_status())

@app.route('/admin_master/bloquear', methods=['POST'])
def admin_master_bloquear():
    if not session.get('admin_master'):
        return jsonify({'status': 'error', 'message': 'Não autorizado'}), 403
    lic = load_licenca()
    lic['bloqueio_imediato'] = True
    save_licenca(lic)
    socketio.emit('licenca_bloqueada', {'status': 'expirada', 'mensagem': 'Sistema bloqueado imediatamente pelo administrador.'})
    return jsonify({'status': 'success', 'message': 'Sistema bloqueado imediatamente.'})

@app.route('/admin_master/desbloquear', methods=['POST'])
def admin_master_desbloquear():
    if not session.get('admin_master'):
        return jsonify({'status': 'error', 'message': 'Não autorizado'}), 403
    lic = load_licenca()
    lic['bloqueio_imediato'] = False
    save_licenca(lic)
    socketio.emit('licenca_desbloqueada', {'status': 'ok'})
    return jsonify({'status': 'success', 'message': 'Sistema desbloqueado.'})

# Proteger rotas sensíveis
@app.route('/painel')
@require_licenca
def painel_led():
    return render_template('painel_led.html')

@app.route('/user_mode')
@require_licenca
def user_mode():
    return render_template('user_mode.html')

CONTATO_LICENCIAMENTO_PATH = 'contato_licenciamento.json'

def load_contato_licenciamento():
    if not os.path.exists(CONTATO_LICENCIAMENTO_PATH):
        return {
            'nome': 'Caique Santos Barbosa',
            'foto': 'https://avatars.githubusercontent.com/u/10201519?v=4',
            'whatsapp': '+55 (11) 96419-6205',
            'email': 'caiquesantosbarbosa@gmail.com',
            'github': 'https://github.com/caique300797',
            'linkedin': '',
            'observacoes': ''
        }
    with open(CONTATO_LICENCIAMENTO_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_contato_licenciamento(data):
    with open(CONTATO_LICENCIAMENTO_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/admin_master/contato', methods=['GET', 'POST'])
def admin_master_contato():
    if not session.get('admin_master'):
        return redirect(url_for('admin_master_login'))
    contato = load_contato_licenciamento()
    if request.method == 'POST':
        contato['nome'] = request.form.get('nome', '')
        contato['foto'] = request.form.get('foto', '')
        contato['whatsapp'] = request.form.get('whatsapp', '')
        contato['email'] = request.form.get('email', '')
        contato['github'] = request.form.get('github', '')
        contato['linkedin'] = request.form.get('linkedin', '')
        contato['observacoes'] = request.form.get('observacoes', '')
        save_contato_licenciamento(contato)
        return render_template('admin_master_contato.html', contato=contato, mensagem='Informações atualizadas com sucesso!')
    return render_template('admin_master_contato.html', contato=contato)

@app.route('/api/contato_licenciamento')
def api_contato_licenciamento():
    return jsonify(load_contato_licenciamento())

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 