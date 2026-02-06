from flask import Flask, render_template, request, jsonify, send_file
import os
import yt_dlp
from pathlib import Path
import json
from datetime import datetime
import uuid
import subprocess

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

# Criar pasta de downloads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_videos', methods=['POST'])
def process_videos():
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        
        if not urls:
            return jsonify({'error': 'Nenhum URL fornecido'}), 400
        
        results = []
        
        for url in urls:
            try:
                result = process_single_video(url)
                results.append(result)
            except Exception as e:
                results.append({
                    'url': url,
                    'error': str(e),
                    'success': False
                })
        
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_single_video(url):
    """Processa um único vídeo: download e transcrição"""
    video_id = str(uuid.uuid4())[:8]
    
    # Detectar plataforma
    is_tiktok = 'tiktok.com' in url.lower()
    is_instagram = 'instagram.com' in url.lower()
    
    # Configurações base do yt-dlp
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'extractor_retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
    }
    
    # Configurações específicas para TikTok
    if is_tiktok:
        ydl_opts.update({
            'impersonate': 'chrome', # Simula um navegador Chrome
            'http_headers': {
                'Referer': 'https://www.tiktok.com/',
            }
        })
    
    # Configurações específicas para Instagram
    if is_instagram:
        ydl_opts.update({
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
        })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if not info:
                raise Exception("Não foi possível extrair informações do vídeo")
            
            video_title = info.get('title', 'Vídeo sem título')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration', 0)
            
            video_filename = ydl.prepare_filename(info)
            
            if not os.path.exists(video_filename):
                downloads_dir = app.config['UPLOAD_FOLDER']
                matching_files = [f for f in os.listdir(downloads_dir) 
                                if f.startswith(video_id) and f.endswith(('.mp4', '.webm', '.mkv'))]
                if matching_files:
                    video_filename = os.path.join(downloads_dir, matching_files[0])
                else:
                    raise Exception("Arquivo de vídeo não encontrado após download")
            
            # Extrair áudio
            audio_file = extract_audio(video_id, url, is_tiktok, is_instagram)
            
            # Transcrever com ElevenLabs
            if os.path.exists(audio_file):
                transcription = transcribe_with_elevenlabs(audio_file)
                os.remove(audio_file)
            else:
                transcription = {
                    'text': 'Transcrição não disponível (áudio não extraído)',
                    'language': 'unknown',
                    'segments': []
                }
            
            return {
                'success': True,
                'video_id': video_id,
                'title': video_title,
                'thumbnail': thumbnail,
                'duration': duration,
                'video_id': video_id,
                #'download_path': os.path.basename(video_filename),
                'transcription': transcription,
                'url': url
            }
    
    except Exception as e:
        error_message = str(e)
        if 'Unable to extract' in error_message:
            error_message = "Este vídeo não pode ser baixado. Pode estar privado ou bloqueado."
        elif 'HTTP Error 404' in error_message:
            error_message = "Vídeo não encontrado. Verifique se o link está correto."
        
        raise Exception(error_message)

def extract_audio(video_id, url, is_tiktok, is_instagram):
    """Extrai áudio do vídeo"""
    audio_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_%(title).50s.%(ext)s'),
        'restrictfilenames': True, # Isso remove espaços e caracteres especiais do nome do arquivo
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
    }
    
    if is_tiktok or is_instagram:
        audio_opts['http_headers'] = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    with yt_dlp.YoutubeDL(audio_opts) as ydl_audio:
        ydl_audio.download([url])
    
    audio_file = os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_audio.mp3')
    
    if not os.path.exists(audio_file):
        downloads_dir = app.config['UPLOAD_FOLDER']
        audio_files = [f for f in os.listdir(downloads_dir) 
                     if f.startswith(f'{video_id}_audio')]
        if audio_files:
            audio_file = os.path.join(downloads_dir, audio_files[0])
    
    return audio_file

def transcribe_with_elevenlabs(audio_path):
    """
    Transcreve áudio usando ElevenLabs Scribe v2
    
    Vantagens:
    - 90+ idiomas (PT, EN, ES inclusos)
    - Speaker diarization (até 32 speakers)
    - Audio event detection (risos, aplausos)
    - Character-level timestamps
    - Alta precisão
    """
    try:
        from elevenlabs.client import ElevenLabs
        
        # Configurar cliente
        api_key = os.environ.get('ELEVENLABS_API_KEY')
        if not api_key:
            return {
                'text': 'ERRO: ELEVENLABS_API_KEY não configurada. Configure a variável de ambiente.',
                'language': 'error',
                'segments': []
            }
        
        client = ElevenLabs(api_key=api_key)
        
        # Transcrever
        with open(audio_path, 'rb') as audio_file:
            result = client.speech_to_text.transcribe(
                audio=audio_file,
                model="scribe-v2",
                language=None,  # Auto-detecta: pt, en, es
                diarize=True,   # Identifica speakers
                tag_audio_events=True,  # Detecta risos, aplausos, etc
            )
        
        # Processar resultado
        full_text = result.text
        language = getattr(result, 'language', 'pt')  # Fallback para português
        
        # Extrair segmentos se disponíveis
        segments = []
        if hasattr(result, 'words') and result.words:
            segments = [
                {
                    'start': word.start,
                    'end': word.end,
                    'text': word.text,
                    'speaker': getattr(word, 'speaker', None)
                }
                for word in result.words
            ]
        
        return {
            'text': full_text,
            'language': language,
            'segments': segments,
            'speakers': getattr(result, 'num_speakers', 1)
        }
        
    except ImportError:
        return {
            'text': 'Erro: Biblioteca elevenlabs não instalada. Execute: pip install elevenlabs',
            'language': 'error',
            'segments': []
        }
    except Exception as e:
        return {
            'text': f'Erro na transcrição com ElevenLabs: {str(e)}',
            'language': 'error',
            'segments': []
        }

@app.route('/download/<video_id>')
def download_file(video_id):
    try:
        downloads_dir = app.config['UPLOAD_FOLDER']
        
        # Filtramos para pegar o VÍDEO (evitando pegar o .mp3 da transcrição se ele ainda existir)
        # E garantimos que o nome comece exatamente com o video_id
        matching_files = [
            f for f in os.listdir(downloads_dir)
            if f.startswith(video_id) and f.lower().endswith(('.mp4', '.mkv', '.webm'))
        ]

        if not matching_files:
            return jsonify({'error': 'Arquivo de vídeo não encontrado'}), 404

        # Escolhe o primeiro arquivo de vídeo encontrado
        file_path = os.path.join(downloads_dir, matching_files[0])
        
        # O send_file cuida do path seguro
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Remove arquivos antigos da pasta de downloads"""
    try:
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return jsonify({'success': True, 'message': 'Arquivos removidos com sucesso'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ROTA FUTURA: GERAÇÃO DE NARRAÇÃO =====
@app.route('/generate_narration', methods=['POST'])
def generate_narration():
    """
    Rota para gerar narração a partir do texto transcrito
    Implementar quando quiser adicionar esta funcionalidade
    """
    try:
        from elevenlabs.client import ElevenLabs
        
        data = request.get_json()
        text = data.get('text', '')
        voice_id = data.get('voice_id', '21m00Tcm4TlvDq8ikWAM')  # Rachel (padrão)
        
        if not text:
            return jsonify({'error': 'Texto não fornecido'}), 400
        
        api_key = os.environ.get('ELEVENLABS_API_KEY')
        client = ElevenLabs(api_key=api_key)
        
        # Gerar áudio
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2"
        )
        
        # Salvar áudio
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'narration_{uuid.uuid4()}.mp3')
        with open(output_path, 'wb') as f:
            for chunk in audio:
                f.write(chunk)
        
        return jsonify({
            'success': True,
            'audio_path': os.path.basename(output_path),
            'download_url': f'/download/{os.path.basename(output_path)}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)