UTILITÁRIO ABRIR PORTA
======================

Este utilitário permite abrir a porta diretamente do desktop, sem precisar acessar o painel web.

CONFIGURAÇÃO:
- IP do servidor: 192.168.24.154:5000
- Protocolo: HTTPS
- Endpoint: /api/porta/abrir

COMO USAR:
1. Execute o arquivo abrir_porta.py
2. Uma janela pequena aparecerá no canto da tela
3. Clique em "Abrir Porta" para acionar a porta
4. O status será mostrado na janela

REQUISITOS:
- Python 3.x instalado
- Biblioteca requests instalada (pip install requests)
- Servidor principal rodando em 192.168.24.154:5000

INSTALAÇÃO DAS DEPENDÊNCIAS:
pip install requests tkinter

OBSERVAÇÕES:
- A janela fica sempre visível (topmost)
- Verifica automaticamente se o sistema está bloqueado
- Se bloqueado, o botão fica desabilitado
- Atualiza o status a cada 2 segundos 