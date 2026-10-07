import os
import soundfile as sf
import tempfile
import imageio_ffmpeg
import subprocess
from core.logger import logger
from kokoro_onnx import Kokoro

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class KokoroClient:
    _instance = None
    
    def __init__(self):
        if KokoroClient._instance is None:
            # Assumes models were downloaded to project_root/models/
            model_path = os.path.join(PROJECT_ROOT, 'models', 'kokoro-v1.0.onnx')
            voices_path = os.path.join(PROJECT_ROOT, 'models', 'voices-v1.0.bin')
            
            logger.info(f"Initializing Kokoro ONNX model from {model_path}")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found at {model_path}")
            KokoroClient._instance = Kokoro(model_path, voices_path)
        self.kokoro = KokoroClient._instance

    def generate_audio(self, text: str, output_path: str, voice: str = "default"):
        if voice == "default":
            voice = "af_bella"
            
        logger.info(f"Generating audio with Kokoro (voice: {voice}) for {output_path}")
        
        try:
            samples, sample_rate = self.kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
            
            # Save as WAV temporarily
            fd, temp_wav = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            
            sf.write(temp_wav, samples, sample_rate)
            
            if output_path.endswith('.mp3'):
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                subprocess.run([
                    ffmpeg_exe, '-y', '-i', temp_wav, output_path
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                os.remove(temp_wav)
            else:
                import shutil
                shutil.move(temp_wav, output_path)
                
            return output_path
        except Exception as e:
            logger.error(f"Kokoro TTS generation failed: {str(e)}")
            raise
