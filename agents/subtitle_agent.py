import json
import os
from datetime import timedelta
from core.base_agent import BaseAgent
from core.config import config
from plugins.whisper_client import WhisperClient

class SubtitleAgent(BaseAgent):
    def __init__(self, run_id: str, niche: str):
        super().__init__(run_id)
        self.niche = niche
        self.whisper = WhisperClient()

    def format_time(self, seconds: float) -> str:
        """Format seconds into SRT time format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = td.microseconds // 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        
    def format_time_ass(self, seconds: float) -> str:
        """Format seconds into ASS time format (H:MM:SS.cc)."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        centiseconds = (td.microseconds // 1000) // 10
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    def generate_srt(self, words: list) -> str:
        srt_content = ""
        for idx, word in enumerate(words):
            srt_content += f"{idx+1}\n"
            srt_content += f"{self.format_time(word['start'])} --> {self.format_time(word['end'])}\n"
            srt_content += f"{word['word'].strip()}\n\n"
        return srt_content
        
    def generate_ass(self, words: list) -> str:
        # Basic ASS header for kinetic typography
        ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,90,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,5,10,10,500,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        for word in words:
            start = self.format_time_ass(word['start'])
            end = self.format_time_ass(word['end'])
            text = word['word'].strip()
            # Simple highlight effect
            ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\k10}}{text}\n"
        return ass_content

    def execute(self) -> bool:
        self.audio_path = os.path.join(config.system_run_dir, self.run_id, "final_audio.mp3")
        self.word_path = os.path.join(config.system_run_dir, self.run_id, "word_timestamps.json")
        self.sentence_path = os.path.join(config.system_run_dir, self.run_id, "sentence_timestamps.json")
        self.srt_path = os.path.join(config.system_run_dir, self.run_id, "captions.srt")
        self.ass_path = os.path.join(config.system_run_dir, self.run_id, "captions.ass")

        self.logger.info(f"Starting Subtitle Engine for run {self.run_id}")
        if not os.path.exists(self.audio_path):
            self.logger.error("No final audio found. Cannot generate subtitles.")
            return False

        # 1. Transcribe with Whisper
        segments = self.run_with_retry(self.whisper.transcribe, retries=2, audio_path=self.audio_path)
        
        word_timestamps = []
        sentence_timestamps = []
        
        for segment in segments:
            sentence_timestamps.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
            if segment.words:
                for word in segment.words:
                    word_timestamps.append({
                        "start": word.start,
                        "end": word.end,
                        "word": word.word
                    })
            else:
                # Fallback if words aren't available but segment is
                word_timestamps.append({
                    "start": segment.start,
                    "end": segment.end,
                    "word": segment.text
                })
            
        # Save JSON files
        with open(self.word_path, 'w') as f:
            json.dump(word_timestamps, f, indent=2)
            
        with open(self.sentence_path, 'w') as f:
            json.dump(sentence_timestamps, f, indent=2)
            
        # Generate SRT and ASS
        srt_text = self.generate_srt(word_timestamps)
        with open(self.srt_path, 'w') as f:
            f.write(srt_text)
            
        ass_text = self.generate_ass(word_timestamps)
        with open(self.ass_path, 'w') as f:
            f.write(ass_text)
            
        self.logger.info(f"Subtitle Generation complete. Outputs saved to {self.srt_path} and {self.ass_path}")
        return True
