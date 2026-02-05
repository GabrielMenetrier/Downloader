"""
Configurações da aplicação Video Downloader & Transcriber
Edite este arquivo para customizar o comportamento da aplicação
"""

import os

class Config:
    """Configurações gerais da aplicação"""
    
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Pastas
    UPLOAD_FOLDER = 'downloads'
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    
    # Whisper - Modelo de transcrição
    # Opções: tiny, base, small, medium, large
    # tiny: Mais rápido, menos preciso (~75MB)
    # base: Balanceado (~142MB) - PADRÃO
    # small: Bom equilíbrio (~466MB)
    # medium: Mais preciso (~1.5GB)
    # large: Melhor qualidade (~2.9GB)
    WHISPER_MODEL = 'base'
    
    # yt-dlp - Opções de download
    YTDLP_FORMAT = 'best[ext=mp4]/best'  # Formato preferencial
    YTDLP_QUIET = True  # Modo silencioso
    
    # Transcrição
    TRANSCRIPTION_LANGUAGE = None  # None = auto-detecta, ou 'pt', 'en', 'es'
    
    # Limpeza automática
    AUTO_CLEANUP_HOURS = 24  # Deletar arquivos após X horas (0 = desabilitado)
    
    # Performance
    MAX_CONCURRENT_DOWNLOADS = 3  # Número máximo de downloads simultâneos


class DevelopmentConfig(Config):
    """Configurações para desenvolvimento"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Configurações para produção"""
    DEBUG = False
    TESTING = False
    # Em produção, defina SECRET_KEY como variável de ambiente
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Use modelo Whisper mais leve em produção se necessário
    WHISPER_MODEL = 'small'


class TestingConfig(Config):
    """Configurações para testes"""
    TESTING = True
    DEBUG = True


# Dicionário de configurações
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env='development'):
    """Retorna a configuração baseada no ambiente"""
    return config.get(env, config['default'])
