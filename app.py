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
app.config['UPLOAD_FOLDER'] = '/app/downloads'  # Caminho absoluto
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'downloads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Carregar modelo Whisper (usa o modelo base por padrão)
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        import whisper
        whisper_model = whisper.load_model("base")
    return whisper_model

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
    """Processa um único vídeo: download e transcrição - APENAS ID, SEM NOME"""
    video_id = str(uuid.uuid4()).replace('-', '')[:16]  # ID de 16 caracteres sem hífens
    
    print(f"[INFO] Processando vídeo ID: {video_id}")
    print(f"[INFO] URL: {url}")
    print(f"[INFO] Pasta downloads: {app.config['UPLOAD_FOLDER']}")
    
    # Detectar plataforma
    is_tiktok = 'tiktok.com' in url.lower()
    is_instagram = 'instagram.com' in url.lower()
    
    # Nome do arquivo: APENAS ID.ext
    video_filename = os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}.mp4')
    
    # Configurações base do yt-dlp com caminho absoluto e APENAS ID
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': video_filename,  # Caminho completo e absoluto
        'quiet': False,
        'no_warnings': False,
        'extractor_retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
    }
    
    # Configurações específicas para TikTok
    if is_tiktok:
        ydl_opts.update({
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.tiktok.com/',
            },
            'extractor_args': {
                'tiktok': {
                    'api_hostname': 'api22-normal-c-useast2a.tiktokv.com'
                }
            }
        })
    
    # Configurações específicas para Instagram
    if is_instagram:
        ydl_opts.update({
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
        })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrair informações do vídeo
            info = ydl.extract_info(url, download=True)
            
            if not info:
                raise Exception("Não foi possível extrair informações do vídeo")
            
            video_title = info.get('title', 'Vídeo sem título')
            thumbnail = info.get('thumbnail', '')
            duration = info.get('duration', 0)
            
            # Verificar extensão do arquivo baixado
            actual_file = None
            for ext in ['.mp4', '.webm', '.mkv', '.avi', '.mov']:
                test_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}{ext}')
                if os.path.exists(test_path):
                    actual_file = test_path
                    break
            
            # Se não encontrou com extensões comuns, procurar qualquer arquivo com o ID
            if not actual_file:
                for file in os.listdir(app.config['UPLOAD_FOLDER']):
                    if file.startswith(video_id):
                        actual_file = os.path.join(app.config['UPLOAD_FOLDER'], file)
                        break
            
            if not actual_file or not os.path.exists(actual_file):
                raise Exception(f"Arquivo de vídeo não encontrado. ID: {video_id}")
            
            print(f"[INFO] Vídeo baixado: {actual_file}")
            
            # Renomear para formato padrão se necessário
            final_ext = os.path.splitext(actual_file)[1]
            final_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}{final_ext}')
            
            if actual_file != final_path:
                os.rename(actual_file, final_path)
                print(f"[INFO] Renomeado para: {final_path}")
            
            # Extrair áudio para transcrição - APENAS ID
            audio_filename = os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_audio.mp3')
            
            audio_opts = {
                'format': 'bestaudio/best',
                'outtmpl': audio_filename,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': False,
            }
            
            # Adicionar headers se for TikTok ou Instagram
            if is_tiktok or is_instagram:
                audio_opts['http_headers'] = ydl_opts.get('http_headers', {})
            
            print(f"[INFO] Extraindo áudio...")
            with yt_dlp.YoutubeDL(audio_opts) as ydl_audio:
                ydl_audio.download([url])
            
            # Procurar arquivo de áudio
            audio_file = None
            for ext in ['.mp3', '.m4a', '.opus', '.ogg']:
                test_audio = os.path.join(app.config['UPLOAD_FOLDER'], f'{video_id}_audio{ext}')
                if os.path.exists(test_audio):
                    audio_file = test_audio
                    break
            
            # Transcrever áudio
            transcription = {
                'text': 'Transcrição não disponível',
                'language': 'unknown',
                'segments': []
            }
            
            if audio_file and os.path.exists(audio_file):
                print(f"[INFO] Transcrevendo áudio: {audio_file}")
                transcription = transcribe_audio(audio_file)
                # Limpar arquivo de áudio
                os.remove(audio_file)
                print(f"[INFO] Áudio temporário removido")
            else:
                print(f"[WARNING] Áudio não encontrado para transcrição")
            
            return {
                'success': True,
                'video_id': video_id,
                'title': video_title,
                'thumbnail': thumbnail,
                'duration': duration,
                'filename': os.path.basename(final_path),
                'transcription': transcription,
                'url': url
            }
    
    except Exception as e:
        error_message = str(e)
        print(f"[ERROR] Falha ao processar vídeo: {error_message}")
        
        # Mensagens de erro mais amigáveis
        if 'Unable to extract' in error_message or 'extract webpage' in error_message:
            error_message = "Este vídeo não pode ser baixado. Pode estar privado, restrito por região, ou a plataforma bloqueou o acesso."
        elif 'HTTP Error 404' in error_message:
            error_message = "Vídeo não encontrado. Verifique se o link está correto."
        elif 'Private video' in error_message:
            error_message = "Este vídeo é privado e não pode ser baixado."
        
        raise Exception(error_message)

def transcribe_audio(audio_path):
    """Transcreve áudio usando Whisper"""
    try:
        model = get_whisper_model()
        result = model.transcribe(audio_path, language=None)  # Auto-detecta idioma
        
        return {
            'text': result['text'],
            'language': result.get('language', 'desconhecido'),
            'segments': [
                {
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text']
                }
                for seg in result.get('segments', [])
            ]
        }
    except Exception as e:
        print(f"[ERROR] Erro na transcrição: {str(e)}")
        return {
            'text': f'Erro na transcrição: {str(e)}',
            'language': 'error',
            'segments': []
        }

@app.route('/download/<video_id>')
def download_file(video_id):
    """Rota para download de arquivos usando apenas o ID"""
    try:
        print(f"[INFO] Requisição de download para ID: {video_id}")
        
        # Procurar arquivo que começa com o video_id (sem incluir _audio)
        downloads_dir = app.config['UPLOAD_FOLDER']
        
        matching_files = [f for f in os.listdir(downloads_dir) 
                         if f.startswith(video_id) and '_audio' not in f]
        
        if not matching_files:
            print(f"[ERROR] Nenhum arquivo encontrado com ID: {video_id}")
            print(f"[INFO] Arquivos disponíveis: {os.listdir(downloads_dir)}")
            return jsonify({'error': 'Arquivo não encontrado'}), 404
        
        filename = matching_files[0]
        file_path = os.path.join(downloads_dir, filename)
        
        print(f"[INFO] Enviando arquivo: {file_path}")
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=f'{video_id}{os.path.splitext(filename)[1]}')
        else:
            return jsonify({'error': 'Arquivo não encontrado'}), 404
            
    except Exception as e:
        print(f"[ERROR] Erro no download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Remove arquivos antigos da pasta de downloads"""
    try:
        count = 0
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                count += 1
        
        print(f"[INFO] {count} arquivos removidos")
        return jsonify({'success': True, 'message': f'{count} arquivos removidos com sucesso'})
    except Exception as e:
        print(f"[ERROR] Erro na limpeza: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Verificar se pasta downloads existe
    print(f"[INFO] Pasta de downloads: {app.config['UPLOAD_FOLDER']}")
    print(f"[INFO] Pasta existe: {os.path.exists(app.config['UPLOAD_FOLDER'])}")
    
    # Modo produção para Docker
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)