import requests
from config import settings

def generar_imagen(prompt: str, width: int = 1024, height: int = 1024, seed: int = 0, steps: int = 4):
    invoke_url = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"

    headers = {
        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
        "Accept": "application/json",
    }

    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "seed": seed,
        "steps": steps
    }

    response = requests.post(invoke_url, headers=headers, json=payload)

    response.raise_for_status()
    response_body = response.json()
    return response_body

