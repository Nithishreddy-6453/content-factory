import json
import os
from pydub import AudioSegment
from core.base_agent import BaseAgent
from core.config import config
from plugins.kokoro_client import KokoroClient
from plugins.edge_tts_client import EdgeTTSClient
import imageio_ffmpeg
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()


class AudioAgent(BaseAgent):
    def __init__(self, run_id: str, niche: str):
        super().__init__(run_id)
        self.niche = niche
        # paths will be dynamically set in execute
        
        if config.audio_primary == "kokoro":
            self.primary_tts = KokoroClient()
            self.fallback_tts = EdgeTTSClient()
        else:
            self.primary_tts = EdgeTTSClient()
            self.fallback_tts = KokoroClient()

    def generate_scene_audio(self, scene_id: str, text: str):
        output_path = os.path.join(self.audio_dir, f"{scene_id}.wav")
        try:
            self.primary_tts.generate_audio(text, output_path)
        except Exception as e:
            self.logger.warning(f"Primary TTS failed for {scene_id}: {str(e)}. Using fallback.")
            self.fallback_tts.generate_audio(text, output_path)
        return output_path

    def execute(self) -> bool:
        self.script_path = os.path.join(config.system_run_dir, self.run_id, "script.json")
        self.audio_dir = os.path.join(config.system_run_dir, self.run_id, "audio")
        self.final_audio_path = os.path.join(config.system_run_dir, self.run_id, "final_audio.mp3")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        self.logger.info(f"Starting Audio Generation for run {self.run_id}")
        if not os.path.exists(self.script_path):
            self.logger.error("No script found.")
            return False
            
        with open(self.script_path, 'r') as f:
            script = json.load(f)
            
        # We start with empty audio and append
        # Ensure that pydub is installed and ffmpeg is on PATH
        try:
            combined = AudioSegment.empty()
        except Exception as e:
            self.logger.error(f"Failed to initialize pydub AudioSegment. Is FFmpeg installed? {str(e)}")
            return False
            
        for scene in script.get('scenes', []):
            scene_id = scene.get('scene_id')
            text = scene.get('voiceover', '')
            if text:
                audio_path = self.run_with_retry(self.generate_scene_audio, retries=2, scene_id=scene_id, text=text)
                
                if os.path.exists(audio_path):
                    # Edge-tts sometimes saves as wav or webm despite .mp3 extension if not forced
                    # We assume it's loadable by pydub.
                    try:
                        if audio_path.endswith(".wav"):
                            segment = AudioSegment.from_wav(audio_path)
                        else:
                            segment = AudioSegment.from_file(audio_path)
                        combined += segment
                    except Exception as e:
                        self.logger.error(f"Failed to load audio for {scene_id}: {str(e)}")
            else:
                self.logger.warning(f"No voiceover text for {scene_id}")

        try:
            combined.export(self.final_audio_path, format="mp3")
            self.logger.info(f"Audio Generation complete. Combined output saved to {self.final_audio_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to export final audio: {str(e)}")
            return False
