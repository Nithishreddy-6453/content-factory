from core.logger import logger

class WhisperClient:
    """Wrapper for faster-whisper to generate word-level timestamps."""
    def __init__(self, model_size="tiny"):
        self.model_size = model_size
        logger.debug(f"Initialized faster-whisper with model size {model_size}")
        
    def transcribe(self, audio_path: str):
        logger.info(f"Transcribing {audio_path} with faster-whisper")
        from faster_whisper import WhisperModel
        model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, word_timestamps=True)
        return list(segments)
