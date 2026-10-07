import urllib.request
import urllib.parse
import json
import uuid

class ComfyUIClient:
    def __init__(self, host='http://localhost:8188'):
        self.host = host
        self.client_id = str(uuid.uuid4())

    def check_connection(self):
        try:
            req = urllib.request.Request(f"{self.host}/history")
            urllib.request.urlopen(req, timeout=5).read()
            return True
        except Exception:
            return False

    def queue_prompt(self, prompt):
        p = {'prompt': prompt, 'client_id': self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"{self.host}/prompt", data=data)
        req.add_header('Content-Type', 'application/json')
        try:
            response = json.loads(urllib.request.urlopen(req, timeout=10).read())
            if isinstance(response, dict) and (response.get('error') or response.get('node_errors')):
                raise RuntimeError(f"ComfyUI prompt error: {response.get('error') or response.get('node_errors')}")
            return response
        except Exception as e:
            raise RuntimeError(f"ComfyUI unavailable: {e}")

    def get_history(self, prompt_id):
        if not prompt_id or prompt_id == "stub_id":
            raise ValueError(f"Invalid prompt_id for get_history: {prompt_id}")
        req = urllib.request.Request(f"{self.host}/history/{prompt_id}")
        try:
            return json.loads(urllib.request.urlopen(req, timeout=10).read())
        except Exception as e:
            raise RuntimeError(f"Failed to get history for prompt {prompt_id}: {e}")
        
    def get_image(self, filename, subfolder, folder_type):
        data = {'filename': filename, 'subfolder': subfolder, 'type': folder_type}
        url_values = urllib.parse.urlencode(data)
        req = urllib.request.Request(f"{self.host}/view?{url_values}")
        try:
            return urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:
            raise RuntimeError(f"Failed to get image {filename}: {e}")

    def generate_image(self, workflow_json):
        response = self.queue_prompt(workflow_json)
        prompt_id = response.get('prompt_id') if isinstance(response, dict) else None
        if not prompt_id or not isinstance(prompt_id, str) or prompt_id == "stub_id":
            raise RuntimeError(f"ComfyUI queue_prompt failed to return a valid prompt_id. Response: {response}")
        return prompt_id
