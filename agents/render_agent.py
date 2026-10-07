import json
import os
import subprocess
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from core.base_agent import BaseAgent
from core.config import config
import imageio_ffmpeg


class RenderAgent(BaseAgent):
    def __init__(self, run_id: str, niche: str):
        super().__init__(run_id)
        self.niche = niche
        self.script_path = os.path.join(config.system_run_dir, self.run_id, "script.json")
        self.visual_manifest_path = os.path.join(config.system_run_dir, self.run_id, "visual_manifest.json")
        self.audio_path = os.path.join(config.system_run_dir, self.run_id, "final_audio.mp3")
        self.ass_path = os.path.join(config.system_run_dir, self.run_id, "captions.ass")
        self.temp_video_path = os.path.join(config.system_run_dir, self.run_id, "temp_render.mp4")
        self.final_video_path = os.path.join(config.system_run_dir, self.run_id, "final_video.mp4")

    def _assemble_timeline(self):
        with open(self.script_path, 'r') as f:
            script = json.load(f)
        with open(self.visual_manifest_path, 'r') as f:
            manifest = json.load(f)
            
        clips = []
        for scene in script.get('scenes', []):
            scene_id = scene.get('scene_id')
            duration = scene.get('duration', 5)
            
            image_info = manifest.get(scene_id)
            if not image_info or not os.path.exists(image_info['image_path']):
                self.logger.error(f"Missing image for scene {scene_id}")
                raise FileNotFoundError(f"Missing image for {scene_id}")
                
            clip = ImageClip(image_info['image_path']).with_duration(duration)
            clips.append(clip)
            
        final_clip = concatenate_videoclips(clips, method="compose")
        
        audio_clip = AudioFileClip(self.audio_path)
        final_clip = final_clip.with_audio(audio_clip)
        
        self.logger.info("Writing temporary timeline composition via MoviePy...")
        final_clip.write_videofile(
            self.temp_video_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            logger=None
        )

    def _apply_subtitles_ffmpeg(self):
        self.logger.info("Applying kinetic subtitles via FFmpeg...")
        escaped_ass = self.ass_path.replace('\\', '/').replace(':', '\\:')
        
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        command = [
            ffmpeg_exe,
            '-y',
            '-i', self.temp_video_path,
            '-vf', f"ass='{escaped_ass}'",
            '-c:a', 'copy',
            self.final_video_path
        ]
        
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            self.logger.error("FFmpeg not found in PATH! Simulating final output.")
            if os.path.exists(self.temp_video_path):
                os.rename(self.temp_video_path, self.final_video_path)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg render failed: {e.stderr.decode()}")
            raise e

    def execute(self) -> bool:
        self.logger.info(f"Starting Render Engine for run {self.run_id}")
        if not os.path.exists(self.script_path) or not os.path.exists(self.visual_manifest_path) or not os.path.exists(self.audio_path):
            self.logger.error("Missing critical assets for rendering.")
            return False

        try:
            self.run_with_retry(self._assemble_timeline, retries=2)
            
            if os.path.exists(self.ass_path):
                self.run_with_retry(self._apply_subtitles_ffmpeg, retries=2)
            else:
                self.logger.warning("No captions.ass found. Skipping subtitle burn-in.")
                if os.path.exists(self.temp_video_path):
                    os.rename(self.temp_video_path, self.final_video_path)
                    
            self.logger.info(f"Render complete! Final video saved to {self.final_video_path}")
            return True
        except Exception as e:
            self.logger.error(f"Render failed: {str(e)}")
            return False
