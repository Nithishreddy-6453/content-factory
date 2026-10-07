import asyncio
import edge_tts
from core.logger import logger

class EdgeTTSClient:
    async def _generate(self, text: str, output_path: str, voice: str):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    def generate_audio(self, text: str, output_path: str, voice: str = "en-US-ChristopherNeural"):
        logger.info(f"Generating audio with EdgeTTS for {output_path}")
        asyncio.run(self._generate(text, output_path, voice))
