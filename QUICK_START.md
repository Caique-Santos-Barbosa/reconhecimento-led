# 🚀 Guia Rápido de Início

## Instalação Rápida (Windows)

1. **Execute o instalador automático:**
   ```bash
   install.bat
   ```

2. **Ou instale manualmente:**
   ```bash
   pip install -r requirements.txt
   ```

## Teste o Sistema

Execute o script de teste para verificar se tudo está funcionando:
```bash
python test_system.py
```

## Primeiro Uso

### 1. Registrar Rostos
```bash
python register_face.py
```
- Escolha opção 1: "Registrar novo rosto"
- Digite o nome da pessoa
- Posicione o rosto na câmera
- Pressione 'c' para capturar

### 2. Executar Sistema Principal
```bash
python facial_recognition_system.py
```

## Controles Durante Execução

- **'q'** - Sair
- **'s'** - Mostrar status
- **'r'** - Modo registro (básico)

## Com Arduino (Opcional)

1. **Carregue o código no Arduino:**
   - Abra `arduino_switch_example.ino` no Arduino IDE
   - Conecte um LED no pino 13 (com resistor 220Ω)
   - Faça upload do código

2. **Execute com Arduino:**
   ```bash
   python facial_recognition_with_arduino.py
   ```

## Solução de Problemas

### Erro ao instalar dlib
```bash
pip install dlib-binary
```

### Câmera não funciona
- Verifique se a câmera está conectada
- Teste com outros aplicativos
- Mude `camera_index = 1` no código

### Arduino não conecta
- Verifique a porta COM no Gerenciador de Dispositivos
- Mude a porta no código: `arduino_port='COM4'`

## Estrutura de Arquivos

```
├── facial_recognition_system.py      # Sistema principal
├── facial_recognition_with_arduino.py # Versão com Arduino
├── register_face.py                  # Gerenciador de rostos
├── test_system.py                    # Script de teste
├── install.bat                       # Instalador Windows
├── requirements.txt                  # Dependências
├── arduino_switch_example.ino        # Código Arduino
├── known_faces/                      # Rostos registrados
└── README.md                         # Documentação completa
```

## Próximos Passos

1. Registre alguns rostos conhecidos
2. Teste o reconhecimento
3. Ajuste a sensibilidade se necessário
4. Conecte um Arduino para interruptor real

## Ajuda

- Execute `python test_system.py` para diagnóstico
- Consulte `README.md` para documentação completa
- Verifique os logs no console para erros 