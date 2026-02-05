# Video Downloader & Transcriber

Aplicação Flask profissional para download e transcrição automática de vídeos de múltiplas plataformas (YouTube, Instagram, TikTok, Pinterest).

## 🎯 Funcionalidades

- ✅ Download de vídeos de YouTube, Instagram, TikTok e Pinterest
- 🎤 Transcrição automática de áudio (Inglês, Português, Espanhol)
- 🎨 Interface moderna com tema escuro/claro
- 📱 Design responsivo
- ♾️ Suporte para múltiplos vídeos simultaneamente
- 🔄 Arquitetura modular para futuras melhorias (integração com IA, etc.)

## 📋 Pré-requisitos

- Python 3.8 ou superior
- FFmpeg instalado no sistema
- Conexão com internet

### Instalar FFmpeg

**Windows:**
```bash
# Usando Chocolatey
choco install ffmpeg

# Ou baixe manualmente de: https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

## 🚀 Instalação

1. **Clone ou baixe o projeto:**
```bash
cd video-downloader-transcriber
```

2. **Crie um ambiente virtual (recomendado):**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

**Nota:** A primeira instalação pode demorar, especialmente o PyTorch e o Whisper (são bibliotecas grandes).

## ▶️ Uso

1. **Inicie a aplicação:**
```bash
python app.py
```

2. **Acesse no navegador:**
```
http://localhost:5000
```

3. **Use a aplicação:**
   - Cole links de vídeos nos campos de entrada
   - Clique em "Adicionar outro link" para adicionar mais vídeos
   - Clique em "Processar Vídeos" para iniciar o download e transcrição
   - Aguarde o processamento (pode levar alguns minutos dependendo da quantidade e tamanho dos vídeos)
   - Baixe os vídeos e veja as transcrições

## 🎨 Funcionalidades da Interface

- **Tema Escuro/Claro:** Clique no ícone de sol/lua no header
- **Múltiplos Vídeos:** Adicione quantos links quiser
- **Validação:** URLs são validados automaticamente
- **Notificações:** Feedback visual para todas as ações
- **Downloads:** Botão de download para cada vídeo processado
- **Transcrições:** Texto completo com detecção automática de idioma

## 📁 Estrutura do Projeto

```
video-downloader-transcriber/
├── app.py                 # Aplicação Flask principal
├── requirements.txt       # Dependências Python
├── README.md             # Este arquivo
├── downloads/            # Pasta para vídeos baixados (criada automaticamente)
├── templates/
│   └── index.html        # Template HTML
├── static/
│   ├── css/
│   │   └── style.css     # Estilos CSS
│   └── js/
│       └── script.js     # JavaScript frontend
```

## 🔧 Configurações Avançadas

### Modelo Whisper

No arquivo `app.py`, você pode alterar o modelo Whisper para melhor precisão:

```python
# Linha ~23
whisper_model = whisper.load_model("base")  # Padrão: rápido, menos preciso

# Opções:
# - "tiny": Mais rápido, menos preciso
# - "base": Balanceado (padrão)
# - "small": Bom equilíbrio
# - "medium": Mais preciso, mais lento
# - "large": Melhor qualidade, muito lento
```

### Limite de Tamanho de Arquivo

```python
# Linha ~14
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
```

## 🔮 Futuras Melhorias (Arquitetura Preparada)

A aplicação foi desenvolvida com arquitetura modular para facilitar:

1. **Integração com IA Generativa:**
   - Criar função `generate_script_with_ai()` que recebe transcrições
   - Integrar com OpenAI GPT, Anthropic Claude, ou modelos locais
   - Gerar roteiros baseados nos vídeos processados

2. **Análise de Conteúdo:**
   - Adicionar rota `/analyze` para análise de sentimentos
   - Extrair tópicos principais
   - Criar resumos automáticos

3. **Editor de Vídeo:**
   - Adicionar função de corte baseado em timestamps da transcrição
   - Gerar clipes automáticos
   - Adicionar legendas aos vídeos

4. **Banco de Dados:**
   - Armazenar histórico de vídeos processados
   - Sistema de tags e categorização
   - Busca de transcrições antigas

### Exemplo de Integração com IA (OpenAI):

```python
# Adicionar ao app.py
import openai

@app.route('/generate_script', methods=['POST'])
def generate_script():
    data = request.get_json()
    transcriptions = data.get('transcriptions', [])
    
    # Combinar transcrições
    combined_text = "\n\n".join([t['text'] for t in transcriptions])
    
    # Gerar roteiro com GPT
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Você é um criador de roteiros para vídeos."},
            {"role": "user", "content": f"Baseado nestes vídeos, crie um novo roteiro:\n\n{combined_text}"}
        ]
    )
    
    return jsonify({'script': response.choices[0].message.content})
```

## 🐛 Troubleshooting

**Erro: FFmpeg não encontrado**
- Instale o FFmpeg e adicione ao PATH do sistema

**Erro: Modelo Whisper não carrega**
- Verifique espaço em disco (modelos podem ocupar 1-3GB)
- Tente um modelo menor: `whisper.load_model("tiny")`

**Erro: Download falha**
- Verifique se o link é válido
- Alguns vídeos podem estar com proteção de região
- TikTok pode requerer autenticação para alguns vídeos privados

**Processamento muito lento**
- Use modelo Whisper menor ("tiny" ou "small")
- Processe menos vídeos por vez
- Considere usar GPU se disponível

## 📝 Licença

Este projeto é de código aberto para uso pessoal e educacional.

## 🤝 Contribuições

Sinta-se à vontade para:
- Reportar bugs
- Sugerir novas funcionalidades
- Melhorar a documentação
- Submeter pull requests

## ⚠️ Avisos Legais

- Respeite os direitos autorais ao baixar vídeos
- Use apenas para conteúdo que você tem permissão para baixar
- Alguns sites podem ter termos de serviço que proíbem downloads
- Esta ferramenta é apenas para fins educacionais e de backup pessoal

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique a seção de Troubleshooting
2. Consulte a documentação do yt-dlp: https://github.com/yt-dlp/yt-dlp
3. Consulte a documentação do Whisper: https://github.com/openai/whisper

---

**Desenvolvido com ❤️ usando Flask, yt-dlp e OpenAI Whisper**
