# 🚀 Facial LED - Versão Render

## 📋 Sobre Esta Versão

Esta é uma versão **simplificada** do sistema Facial LED, otimizada para funcionar no **plano gratuito do Render** sem problemas de memória.

## ⚠️ Limitações da Versão Render

### ❌ **Funcionalidades Desabilitadas:**
- **Reconhecimento facial** (OpenCV + dlib)
- **Processamento de imagens** complexo
- **Integração com câmera** em tempo real

### ✅ **Funcionalidades Mantidas:**
- **Sistema de licenciamento** completo
- **Interface web** responsiva
- **Painel administrativo** master
- **WebSockets** para comunicação em tempo real
- **Sistema de usuários** e perfis
- **Upload de arquivos** e vídeos
- **Controle de acesso** e autenticação

## 🔧 Arquivos Específicos para Render

- **`app_render.py`** - Aplicação principal simplificada
- **`requirements_render_minimal.txt`** - Dependências mínimas
- **`build.sh`** - Script de build otimizado
- **`render.yaml`** - Configuração do Render

## 🚀 Deploy no Render

### **1. Configuração:**
- **Build Command:** `chmod +x build.sh && ./build.sh`
- **Start Command:** `python3.11 -m gunicorn --worker-class eventlet -w 1 app_render:app`

### **2. Variáveis de Ambiente:**
- `PYTHON_VERSION`: `3.11.0`
- `PYTHONUNBUFFERED`: `1`
- `PIP_NO_CACHE_DIR`: `1`

## 📊 Diferenças da Versão Original

| Funcionalidade | Original | Render |
|----------------|----------|---------|
| Reconhecimento Facial | ✅ | ❌ |
| Sistema de Licenciamento | ✅ | ✅ |
| Interface Web | ✅ | ✅ |
| WebSockets | ✅ | ✅ |
| Upload de Arquivos | ✅ | ✅ |
| Painel Admin | ✅ | ✅ |

## 🔄 Migração para Versão Completa

Para usar a versão completa com reconhecimento facial:

1. **Upgrade para plano pago** no Render
2. **Substituir** `app_render.py` por `app.py`
3. **Usar** `requirements_render.txt` completo
4. **Reconfigurar** variáveis de ambiente

## 📝 Notas Técnicas

- **Memória:** Otimizada para < 512MB (plano gratuito)
- **Build:** Sem compilação de bibliotecas C++
- **Dependências:** Apenas Python puro + Flask
- **Performance:** Adequada para demonstração e testes

## 🆘 Suporte

Para dúvidas sobre esta versão ou migração para versão completa:
- **Email:** caiquesantosbarbosa@gmail.com
- **WhatsApp:** +55 (11) 96419-6205
- **GitHub:** https://github.com/caique300797

---

**Versão:** 1.1.3  
**Data:** Agosto 2025  
**Compatibilidade:** Render (plano gratuito) 