import requests
from config import settings
from gradio_client import Client, handle_file

def generar_imagen(prompt: str, width: int = 1024, height: int = 1024, seed: int = 42, steps: int = 20, image: str = None):
    # invoke_url = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"

    # headers = {
    #     "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
    #     "Accept": "application/json",
    # }

    # payload = {
    #     "prompt": prompt,
    #     "width": width,
    #     "height": height,
    #     "seed": seed,
    #     "steps": steps
    # }
    # if image is not None:
    #     payload["image"] = image

    # response = requests.post(invoke_url, headers=headers, json=payload)

    # response.raise_for_status()
    # response_body = response.json()
    # return response_body
    client = Client("laruss5/Z-Image-Turbo", token=settings.GRADIO_API_TOKEN)
    result = client.predict(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=steps,
        seed=seed,
        randomize_seed=True,
        api_name="/generate_image"
    )
    print(result)
    return result

