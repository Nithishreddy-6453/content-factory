import json
import os
import hashlib
from core.base_agent import BaseAgent
from core.config import config
from plugins.comfyui_client import ComfyUIClient

class VisualAgent(BaseAgent):
    def __init__(self, run_id: str, niche: str):
        super().__init__(run_id)
        self.niche = niche
        self.template_path = os.path.join('templates', 'comfyui_workflow.json')
        os.makedirs(config.system_asset_library_dir, exist_ok=True)
        self.comfy = ComfyUIClient()
        
    def _get_asset_cache_path(self, prompt: str) -> str:
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        return os.path.join(config.system_asset_library_dir, f"{prompt_hash}.png")

    def generate_image(self, scene_id: str, prompt: str, seed: int, negative_prompt: str = 'ugly, blurry, deformed, low resolution, text, watermark'):
        cache_path = self._get_asset_cache_path(prompt)
        output_file_name = f"scene_{scene_id}"
        run_output_path = os.path.join(self.visual_dir, f"{output_file_name}.png")
        
        if os.path.exists(cache_path):
            self.logger.info(f"Asset Library hit for {scene_id}. Reusing {cache_path}")
            with open(cache_path, 'rb') as f_src, open(run_output_path, 'wb') as f_dst:
                f_dst.write(f_src.read())
            return run_output_path

        if not self.comfy.check_connection():
            raise RuntimeError(f"ComfyUI is unavailable at {self.comfy.host}. Visual generation cannot continue.")

        with open(self.template_path, 'r') as f:
            workflow_str = f.read()
            
        workflow_str = workflow_str.replace('{{PROMPT}}', prompt)
        workflow_str = workflow_str.replace('{{NEGATIVE_PROMPT}}', negative_prompt)
        workflow_str = workflow_str.replace('{{FILENAME}}', output_file_name)
        
        workflow = json.loads(workflow_str)
        
        for node_id, node in workflow.items():
            if node.get('class_type') == 'KSampler':
                node['inputs']['seed'] = seed
                
        try:
            prompt_id = self.comfy.generate_image(workflow)
            if not prompt_id or not isinstance(prompt_id, str) or prompt_id == "stub_id":
                raise RuntimeError(f"Invalid prompt_id received from ComfyUI: {prompt_id}")
            
            import time
            start_time = time.time()
            max_wait_seconds = 300
            poll_interval_seconds = 2
            image_saved = False

            while True:
                if time.time() - start_time > max_wait_seconds:
                    raise TimeoutError(f"ComfyUI generation exceeded {max_wait_seconds} seconds for prompt_id {prompt_id}")
                    
                history = self.comfy.get_history(prompt_id)
                if prompt_id in history:
                    prompt_data = history[prompt_id]
                    status = prompt_data.get('status', {})
                    if status.get('status_str') == 'error':
                        raise RuntimeError(f"ComfyUI execution error for prompt {prompt_id}: {status.get('messages', 'Unknown error')}")

                    outputs = prompt_data.get('outputs', {})
                    if not outputs:
                        raise RuntimeError(f"ComfyUI returned empty or failed output for prompt_id {prompt_id}")
                    
                    for node_id, node_output in outputs.items():
                        if 'images' in node_output and node_output['images']:
                            image_info = node_output['images'][0]
                            image_data = self.comfy.get_image(image_info['filename'], image_info['subfolder'], image_info['type'])
                            with open(run_output_path, 'wb') as f:
                                f.write(image_data)
                            with open(cache_path, 'wb') as f_dst:
                                f_dst.write(image_data)
                            image_saved = True
                            break
                    if not image_saved:
                        raise RuntimeError(f"ComfyUI completed prompt {prompt_id} but no image was found in outputs: {outputs}")
                    break
                time.sleep(poll_interval_seconds)

            if not os.path.exists(run_output_path) or os.path.getsize(run_output_path) == 0:
                raise RuntimeError(f"Visual asset missing or empty at {run_output_path}")

            self.logger.info(f"Generated visual for {scene_id} at {run_output_path}")
            return run_output_path
        except Exception as e:
            self.logger.error(f"ComfyUI generation failed for {scene_id}: {str(e)}")
            raise e

    def execute(self) -> bool:
        self.scene_plan_path = os.path.join(config.system_run_dir, self.run_id, 'scene_plan.json')
        self.visual_dir = os.path.join(config.system_run_dir, self.run_id, 'images')
        self.visual_manifest_path = os.path.join(config.system_run_dir, self.run_id, 'visual_manifest.json')
        os.makedirs(self.visual_dir, exist_ok=True)
        
        self.logger.info(f"Starting Visual Generation for run {self.run_id}")
        if not os.path.exists(self.scene_plan_path):
            self.logger.error("No scene plan found.")
            return False
            
        with open(self.scene_plan_path, 'r') as f:
            plan = json.load(f)
            
        global_style = plan.get('global_visual_style', '')
        manifest = {}
        
        for idx, scene in enumerate(plan.get('scenes', [])):
            scene_id = scene.get('scene_id')
            raw_prompt = scene.get('image_prompt', '')
            full_prompt = f"{global_style}, {raw_prompt}"
            
            seed = 1000000 + idx
            
            negative_prompt = plan.get('negative_prompt', 'ugly, blurry, deformed, low resolution, text, watermark')
            image_path = self.run_with_retry(self.generate_image, retries=3, scene_id=scene_id, prompt=full_prompt, seed=seed, negative_prompt=negative_prompt)
            manifest[scene_id] = {
                'image_path': image_path,
                'prompt': full_prompt,
                'seed': seed
            }
            
        with open(self.visual_manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        self.logger.info(f"Visual Generation complete. Manifest saved to {self.visual_manifest_path}")
        return True
