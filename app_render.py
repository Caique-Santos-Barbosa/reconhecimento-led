from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, send_file, session
from flask_socketio import SocketIO, emit
import os
import json
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'Gds2024aa@@_PainelFacial_2024_!@#_Un1c0_S3gr3d0'
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

# --- Rotas Básicas ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_master/login', methods=['GET', 'POST'])
def admin_master_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_MASTER_PASSWORD:
            session['admin_master'] = True
            return redirect(url_for('admin_master_painel'))
        return render_template('admin_master_login.html', error='Senha incorreta')
    return render_template('admin_master_login.html')

@app.route('/admin_master/painel')
def admin_master_painel():
    if not session.get('admin_master'):
        return redirect(url_for('admin_master_login'))
    licenca = load_licenca()
    return render_template('admin_master_painel.html', licenca=licenca)

@app.route('/admin_master/atualizar_licenca', methods=['POST'])
def admin_master_atualizar_licenca():
    if not session.get('admin_master'):
        return redirect(url_for('admin_master_login'))
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

# --- Rotas Protegidas ---
@app.route('/painel')
@require_licenca
def painel_led():
    return render_template('painel_led.html')

@app.route('/user_mode')
@require_licenca
def user_mode():
    return render_template('user_mode.html')

# --- API de Status ---
@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'ok',
        'message': 'Sistema funcionando (versão Render)',
        'timestamp': datetime.now().isoformat(),
        'note': 'Reconhecimento facial temporariamente desabilitado para compatibilidade com Render'
    })

# --- Contato Licenciamento ---
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