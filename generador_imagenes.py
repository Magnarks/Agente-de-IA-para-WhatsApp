import requests
from config import settings
from gradio_client import Client, handle_file

def generar_imagen(prompt: str, width: int = 1024, height: int = 1024, seed: int = 2, steps: int = 8, image: str = None):
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
    # client = Client("laruss5/Z-Image-Turbo", token=settings.GRADIO_API_TOKEN)
    # result = client.predict(
    #     prompt=prompt,
    #     height=height,
    #     width=width,
    #     num_inference_steps=steps,
    #     seed=seed,
    #     randomize_seed=True,
    #     api_name="/generate_image"
    # )
    # print(result)
    # return result
    client = Client("Magnarks/Krea-2-Turbo_I2I", token=settings.GRADIO_API_TOKEN)
    result = client.predict(
        param_0="text2image",
        param_1=prompt,
        param_2="",
        param_3=handle_file('https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png'),
        param_4=handle_file('https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png'),
        param_5=width,
        param_6=height,
        param_7=1.4,
        param_8=768,
        param_9=1,
        param_10=1,
        param_11=steps,
        param_12=1,
        param_13="euler",
        param_14="beta",
        param_15=seed,
        param_16=True,
        param_17=0,
        param_18="pornmasterKrea2_v2TurboInt8.safetensors",
        param_19="Hello!!",
        param_20="Hello!!",
        param_21="Hello!!",
        param_22={"headers":["repo_id","filename","revision","weight"],"data":[],"metadata":None},
        param_23=0,
        param_24=0,
        param_25=0,
        param_26=0,
        param_27=0,
        param_28=0,
        param_29=0,
        param_30=0,
        param_31=0,
        param_32=0,
        param_33=0,
        param_34=0,
        param_35=0,
        param_36=0,
        param_37=0,
        param_38=0,
        param_39=0,
        param_40=0,
        api_name="/_generate_wrapper"
    )
    print(result)
    return result

# generar_imagen("A beautiful landscape with mountains and a river")

