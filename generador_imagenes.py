import asyncio
import time
from huggingface_hub import HfApi
from gradio_client import Client, handle_file
 
def _espacio_esta_dormido_sync(space_id: str, hf_token: str) -> bool:
    try:
        runtime = HfApi().get_space_runtime(space_id, token=hf_token)
        return runtime.stage in ("SLEEPING", "BUILDING")
    except Exception as e:
        print(f"[WARN] No se pudo consultar el estado del Space '{space_id}': {e}")
        # Si no se pudo saber, asumimos que está despierto para no
        # mandar avisos de más cuando en realidad sí respondía rápido.
        return False
 
 
async def espacio_esta_dormido(space_id: str, hf_token: str) -> bool:
    return await asyncio.to_thread(_espacio_esta_dormido_sync, space_id, hf_token=hf_token)
 
 
def _generar_imagen_sync(space_id: str, prompt: str, hf_token: str = None, timeout_segundos: int = 180, max_intentos: int = 2, width: int = 1024, height: int = 1024, seed: int = 2, steps: int = 8):
    ultimo_error = None
    for intento in range(1, max_intentos + 1):
        try:
            client = Client(
                space_id,
                token=hf_token,
                httpx_kwargs={"timeout": timeout_segundos},
            )
            return client.predict(
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
        except Exception as e:
            ultimo_error = e
            print(f"[WARN] Intento {intento}/{max_intentos} generando imagen falló: {e}")
            if intento < max_intentos:
                time.sleep(10)
    raise ultimo_error
 
 
async def generar_imagen_con_reintentos(space_id: str, prompt: str, hf_token: str = None):
    return await asyncio.to_thread(_generar_imagen_sync, space_id, prompt, hf_token, width=1024, height=1024, seed=2, steps=8)

# def generar_imagen(prompt: str, width: int = 1024, height: int = 1024, seed: int = 2, steps: int = 8, image: str = None):

#     client = Client("Magnarks/Krea-2-Turbo_I2I", token=settings.GRADIO_API_TOKEN)
#     result = client.predict(
#         param_0="text2image",
#         param_1=prompt,
#         param_2="",
#         param_3=handle_file('https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png'),
#         param_4=handle_file('https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png'),
#         param_5=width,
#         param_6=height,
#         param_7=1.4,
#         param_8=768,
#         param_9=1,
#         param_10=1,
#         param_11=steps,
#         param_12=1,
#         param_13="euler",
#         param_14="beta",
#         param_15=seed,
#         param_16=True,
#         param_17=0,
#         param_18="pornmasterKrea2_v2TurboInt8.safetensors",
#         param_19="Hello!!",
#         param_20="Hello!!",
#         param_21="Hello!!",
#         param_22={"headers":["repo_id","filename","revision","weight"],"data":[],"metadata":None},
#         param_23=0,
#         param_24=0,
#         param_25=0,
#         param_26=0,
#         param_27=0,
#         param_28=0,
#         param_29=0,
#         param_30=0,
#         param_31=0,
#         param_32=0,
#         param_33=0,
#         param_34=0,
#         param_35=0,
#         param_36=0,
#         param_37=0,
#         param_38=0,
#         param_39=0,
#         param_40=0,
#         api_name="/_generate_wrapper"
#     )
#     print(result)
#     return result

# generar_imagen("A beautiful landscape with mountains and a river")

