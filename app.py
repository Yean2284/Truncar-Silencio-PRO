from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import io
import os
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='.')
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuración
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac', 'wma'}

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_audio_file(file_data, filename):
    """Procesa el audio y retorna el buffer del MP3"""
    try:
        # Cargar audio usando pydub
        audio = AudioSegment.from_file(io.BytesIO(file_data))
        
        print(f"✅ Audio cargado: {len(audio)}ms, {audio.channels} canales, {audio.frame_rate}Hz")
        
        # Detectar segmentos no silenciosos
        # min_silence_len=600ms (0.6s), silence_thresh=-30dB
        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=600,
            silence_thresh=-30,
            seek_step=1
        )
        
        if not nonsilent_ranges:
            return None, "El archivo solo contiene silencio"
        
        print(f"🔍 Detectados {len(nonsilent_ranges)} segmentos de audio")
        
        # Construir audio sin silencios largos
        output = AudioSegment.empty()
        
        for i, (start, end) in enumerate(nonsilent_ranges):
            output += audio[start:end]
            # Agregar 100ms de pausa entre segmentos (excepto el último)
            if i < len(nonsilent_ranges) - 1:
                output += AudioSegment.silent(duration=100)
        
        print(f"✂️ Audio procesado: {len(audio)}ms → {len(output)}ms (ahorro: {((len(audio)-len(output))/len(audio)*100):.1f}%)")
        
        # Exportar a MP3
        buffer = io.BytesIO()
        output.export(
            buffer, 
            format='mp3', 
            bitrate='128k',
            parameters=["-q:a", "2"]  # Calidad media-alta
        )
        buffer.seek(0)
        
        return buffer, None
        
    except Exception as e:
        print(f"❌ Error procesando audio: {str(e)}")
        return None, str(e)

# Servir archivos estáticos (HTML, JS, CSS, etc)
@app.route('/')
def index():
    """Servir index.html"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """Servir archivos estáticos"""
    return send_from_directory('.', path)

@app.route('/api/health')
def health():
    """Endpoint de health check"""
    return jsonify({
        'status': 'online',
        'service': 'Truncar Silencio PRO API',
        'version': '1.0.0',
        'max_file_size_mb': MAX_FILE_SIZE / (1024 * 1024),
        'supported_formats': list(ALLOWED_EXTENSIONS)
    })

@app.route('/api/process', methods=['POST', 'OPTIONS'])
def process():
    """Endpoint principal para procesar audio"""
    
    # Manejar preflight CORS
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        # Verificar que se envió un archivo
        if 'audio' not in request.files:
            return jsonify({
                'error': 'No se recibió ningún archivo',
                'details': 'Debes enviar un archivo con el nombre "audio" en el FormData'
            }), 400
        
        file = request.files['audio']
        
        # Verificar que el archivo tiene nombre
        if file.filename == '':
            return jsonify({
                'error': 'Archivo sin nombre',
                'details': 'El archivo debe tener un nombre válido'
            }), 400
        
        # Verificar extensión
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'Formato no soportado',
                'details': f'Formatos permitidos: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Leer archivo
        file_data = file.read()
        file_size_mb = len(file_data) / (1024 * 1024)
        
        print(f"📦 Archivo recibido: {file.filename} ({file_size_mb:.2f}MB)")
        
        # Verificar tamaño
        if len(file_data) > MAX_FILE_SIZE:
            return jsonify({
                'error': 'Archivo demasiado grande',
                'details': f'El archivo pesa {file_size_mb:.1f}MB. Máximo permitido: {MAX_FILE_SIZE/(1024*1024):.0f}MB'
            }), 413
        
        # Procesar audio
        buffer, error = process_audio_file(file_data, file.filename)
        
        if error:
            return jsonify({
                'error': 'Error al procesar audio',
                'details': error
            }), 500
        
        print(f"✅ Audio procesado exitosamente")
        
        # Retornar archivo procesado
        return send_file(
            buffer,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=f"sin_silencio_{secure_filename(file.filename.rsplit('.', 1)[0])}.mp3"
        )
    
    except Exception as e:
        print(f"❌ Error interno: {str(e)}")
        return jsonify({
            'error': 'Error interno del servidor',
            'details': str(e)
        }), 500

# Para desarrollo local
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
