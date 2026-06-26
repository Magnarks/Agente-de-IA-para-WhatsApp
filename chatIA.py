from dotenv import load_dotenv
import openai
import json
from config import settings
# from supertonic import TTS
import os
import subprocess
import base64
from tavily import TavilyClient, TavilyKeylessLimitError
from openWA import obtener_historial_mensajes
import whisper
import tempfile
from datetime import datetime
import requests
from omnivoice import OmniVoice
import soundfile as sf
import torch
import gc

load_dotenv(override=True)

client = openai.OpenAI(base_url=settings.OPENAI_API_BASE_URL, api_key=settings.OPENAI_API_KEY)
MODEL_NAME = settings.MODEL_NAME

SYSTEM_MESSAGE = settings.SYSTEM_MESSAGE

historial_conversacion = {}

fecha_actual = datetime.now().strftime("%d/%m/%Y")

async def generar_resumen_IA(id_chat: str, numero_mensajes: int, paginacion = 1):
    if id_chat != "":
        resumen = await obtener_historial_mensajes(id_chat, numero_mensajes, paginacion)
        print("Resumen del chat obtenido: ", resumen)
        return resumen
    
async def generar_reaccion_IA(emoji: str):
    print("Emoji generado:", emoji)
    return emoji

def consultar_internet_IA(buscar: str):

    if not buscar or not buscar.strip():
        return "No se proporcionó una consulta"
    
    try:
        response = TavilyClient(api_key=settings.TAVILY_API_KEY).search(query=buscar, max_results=3, include_answer=True, include_raw_content=True , search_depth="advanced")
        resultados = []

        for r in response["results"]:
            resultados.append({
                "titulo": r["title"],
                "contenido": r["content"],
                "fuente": r["url"]
            })

        print(resultados)
        return {
            "respuesta_actualizada": response.get("answer"),
            "fuentes": [
                {
                    "titulo": r["title"],
                    "contenido": r["content"],
                    "fuente": r["url"]
                }
                for r in response["results"]
            ]
        }
    except TavilyKeylessLimitError as e:
        # Rate-limit cap reached. The exception carries the human-readable
        # message plus structured fields (code, window, retry_after_seconds,
        # next_actions) returned by the Tavily API.
        print(e)
        print("retry after:", e.retry_after_seconds, "seconds")

def consultar_resultado_deportivo_IA(partido: str):

    consulta = partido

    fecha_actual_YYYY_MM_DD = datetime.now().strftime("%Y-%m-%d")


    api_url = f"https://footballdata.io/api/v1/matches/date/{fecha_actual_YYYY_MM_DD}"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.FOOTBALLDATA_KEY}",
    }
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            respuesta_data = response.json()
            datos_respuesta = respuesta_data
            print(datos_respuesta.get("data", None))
            if datos_respuesta is not None:
                return datos_respuesta
        else:
            print("Error al obtener la información del partido.")
            return {"error": "No se pudo obtener la información del partido."}
    except requests.exceptions.Timeout:
        print("Error: La solicitud ha excedido el tiempo de espera.")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return {"error": "Error en la solicitud."}
    
def consultar_partido_deportivo_en_vivo_IA(partido: str):

    consulta = partido

    fecha_actual_YYYY_MM_DD = datetime.now().strftime("%Y-%m-%d")

    api_url = f"https://v3.football.api-sports.io/odds/live?league=1"
    headers = {
        "Accept": "*/*",
        "x-rapidapi-key": settings.API_FOOTBALL_KEY,
    }
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            respuesta_data = response.json()
            datos_respuesta = respuesta_data
            print(datos_respuesta.get("response", None))
            if datos_respuesta is not None:
                return datos_respuesta
        else:
            print("Error al obtener la información del partido.", response.status_code, response.text )
            return {"error": "No se pudo obtener la información del partido."}
    except requests.exceptions.Timeout:
        print("Error: La solicitud ha excedido el tiempo de espera.")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return {"error": "Error en la solicitud."}
    

async def transcribir_con_whisper_local(wav_bytes):
    """Transcribe WAV bytes usando Whisper local."""
    # Guardar en archivo temporal
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name
    try:
        # Cargar modelo (primera vez descarga ~140 MB)
        # Opciones: tiny, base, small, medium, large
        model = whisper.load_model("base", device="cpu")  # o "cuda" si tienes GPU
        
        # Transcribir
        result = model.transcribe(tmp_path, language="es")
        return result["text"]
    finally:
        os.remove(tmp_path)

async def generar_respuesta_audio_IA(texto, delivery_id, mensaje):
    try:
        if "femenina" in mensaje:
            voz = settings.VOZ_FEMENINIA
            texto_voz = settings.TEXTO_VOZ_FEMENINA
        else:
            voz = settings.VOZ_MASCULINA
            texto_voz = settings.TEXTO_VOZ_MASCULINA

        print("VRAM antes:", torch.cuda.memory_allocated() / 1024**3,"GB")

        filename_wav = os.path.join(settings.RUTA_AUDIOS, f"respuesta_audio_{delivery_id}.wav")
        filename_ogg = os.path.join(settings.RUTA_AUDIOS, f"respuesta_audio_{delivery_id}.ogg")

        # Metódo para GPU
        # cargar el mdelo / Load the model
        model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice",
            device_map="cuda:0",
            dtype=torch.float16
        )

        print("VRAM con OmniVoice:",torch.cuda.memory_allocated() / 1024**3,"GB")

        # Generar audio / Generate audio
        audio = model.generate(
            text=texto,
            ref_audio=voz,
            ref_text=texto_voz,
        ) # audio is a list of `np.ndarray` with shape (T,) at 24 kHz.

        sf.write(filename_wav, audio[0], 24000)
        
        # Metódo para CPU
        # tts = TTS(auto_download=True)
        # style = tts.get_voice_style(voice_name="F4")
        # wav, duration = tts.synthesize(texto, voice_style=style, total_steps=8, lang="es")
        # tts.save_audio(wav, filename_wav)

        subprocess.run([
            "ffmpeg",
            "-y",
            "-i", filename_wav,
            "-c:a", "libopus",
            "-ar", "48000",
            "-ac", "1",
            "-b:a", "32k",
            filename_ogg
        ], check=True)

        return {"audio_file": filename_ogg}
    except Exception as e:
        print(f"Error al generar el audio: {e}")
        return {"error": "No se pudo generar el audio."}
    finally:
        if 'model' in locals() and model is not None:
            # 1. Mover al CPU rompe enlaces residuales en los tensores de la GPU
            # model.cpu()             
            # 2. Eliminar el modelo y estructuras asociadas
            del model            
            # 3. Eliminar optimizadores y gradientes (CRUCIAL para liberar memoria)
            if 'optimizer' in locals():
                del optimizer            
            # 4. Forzar el recolector de basura de Python
            gc.collect()

        if torch.cuda.is_available():
            # 5. Asegurar que las operaciones de la GPU hayan terminado antes de limpiar
            torch.cuda.synchronize()            
            # 6. Vaciar el caché del asignador de memoria de PyTorch
            torch.cuda.empty_cache()            
            # 7. Liberar memoria compartida interprocesos
            torch.cuda.ipc_collect()
            print("VRAM después:",torch.cuda.memory_allocated() / 1024**3,"GB")

herramientas = [
    {
        "type": "function",
        "function": {
            "name": "generar_resumen_IA",
            "description": "Permite generar un resumen del chat del grupo basado en la cantidad solicitada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_chat": {
                        "type": "string",
                        "description": "El ID del chat del cual se desea obtener resumen."
                    },
                    "numero_mensajes": {
                        "type": "integer",
                        "description": "El número maximo de mensajes a retornar."
                    },
                    "paginacion": {
                        "type": "integer",
                        "description": "Desplazamiento para paginación."
                    }
                },
                "required": ["numero_mensajes", "paginacion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_internet_IA",
            "description": "Busca información actualizada en internet. Debe utilizarse para noticias, eventos recientes, lanzamientos de productos, cambios de versiones, resultados deportivos, clima y cualquier información que pueda haber cambiado después del entrenamiento del modelo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "buscar": {
                        "type": "string",
                        "description": "Lo que toca buscar en internet."
                    }
                },
                "required": ["buscar"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_resultado_deportivo_IA",
            "description": "Obtiene resultados de partidos ya finalizados o disputados anteriormente. Utilizar cuando el usuario pregunte quién ganó, cuánto quedó un partido, resultados históricos, estadísticas de encuentros terminados, tablas de posiciones o clasificación de torneos. No utilizar para partidos que se estén jugando en este momento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "buscar": {
                        "type": "string",
                        "description": "El resultado que toca buscar."
                    }
                },
                "required": ["buscar"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_partido_deportivo_en_vivo_IA",
            "description": "Obtiene información de partidos que se están jugando actualmente. Utilizar únicamente cuando el usuario pregunte por un partido en vivo, en curso, actualmente, hoy, ahora mismo, minuto a minuto, marcador actual o cuando mencione dos equipos específicos y quiera saber cómo va el partido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "buscar": {
                        "type": "string",
                        "description": "El resultado en vivo o en curso que toca buscar."
                    }
                },
                "required": ["buscar"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generar_reaccion_IA",
            "description": """
                Utiliza esta herramienta cuando una reacción con emoji sea suficiente.

                Ejemplos:
                - "jajaja"
                - "xd"
                - "😂"
                - "buen trabajo"
                - "felicidades"
                - "golazo"
                - "que tristeza"
                - "brutal"
                - "increíble"

                Si el mensaje puede ser respondido únicamente con un emoji,
                usa esta herramienta EN LUGAR de generar texto.

                Cuando uses esta herramienta NO escribas una respuesta adicional.
                """,
            "parameters": {
            "type": "object",
            "properties": {
                "emoji": {
                "type": "string",
                "description": "Emoji de reacción"
                }
            },
            "required": ["emoji"]
            }
        }
    }
]

async def chat(mensaje, remitente, chat_id, b64 = None):
    usuario = remitente

    if usuario not in historial_conversacion:
        historial_conversacion[usuario] = []
        historial_conversacion[usuario].append({"role": "system", "content": SYSTEM_MESSAGE})
        historial_conversacion[usuario].append({"role": "system", "content": f"Fecha actual: {fecha_actual}"})

    if b64 is None:
        historial_conversacion[usuario].append({"role": "user", "content": mensaje})
    else:
        tipo_b64 = b64.get('mimetype', None)
        if tipo_b64 == "image/jpeg":
            jpeg_base64 = b64.get("data")
            historial_conversacion[usuario].append({"role": "user", "content": [{"type": "text","text": mensaje},{"type": "image_url","image_url": {"url": f"data:image/jpeg;base64,{jpeg_base64}"}}]})
        elif tipo_b64 == "audio/ogg":
            ogg_bytes = base64.b64decode(b64.get('data', None))
            if ogg_bytes is not None:
                process = subprocess.run(
                    [
                        "ffmpeg",
                        "-i", "pipe:0",
                        "-f", "wav",
                        "-ac", "1",
                        "-ar", "16000",
                        "pipe:1"
                    ],
                    input=ogg_bytes,
                    capture_output=True
                )
                wav_bytes = process.stdout
                wav_base64 = base64.b64encode(wav_bytes).decode()
                buscando_gemma = await transcribir_con_whisper_local(wav_bytes)
                if "gema" or "gemma" in buscando_gemma.lower():
                    historial_conversacion[usuario].append({"role": "user", "content": [{"type": "text","text": "Transcribe el audio. Si NO escuchas las palabras: gemma o gema responde exactamente: IGNORAR_AUDIO Sin explicaciones adicionales. Si sí escuchas alguna de esas palabras, responde normalmente."},{"type": "input_audio","input_audio": {"data": wav_base64,"format": "wav"}}]})
                else:
                    return {"response": "No se pudo procesar el audio, o No se llamo a gemma en el mensaje."}
            else:
                return {"response": "No se pudo procesar el audio."}
        else:
            return {"response": "No se pudo obtener el tipo de archivo."}

    print(f"[DEBUG] Historial de conversación para {usuario}: {historial_conversacion[usuario]}")
    
    try:
        user_input = mensaje.strip()

        if not user_input and b64 is None:
            return {"response": "Por favor, envía un mensaje válido."}

        print(f"[DEBUG] Enviando al modelo con {len(historial_conversacion[usuario])} mensajes")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=historial_conversacion[usuario],
            tools=herramientas
        )

        print(f"[DEBUG] Respuesta recibida. Tool calls: {response.choices[0].message.tool_calls}")
        print(response.choices[0].message)
        print(response.choices[0].message.content)
        print(response.choices[0].message.tool_calls)

        if response.choices[0].message.tool_calls:
            print(f"[DEBUG] Se encontraron {len(response.choices[0].message.tool_calls)} tool_calls")
            historial_conversacion[usuario].append({
                "role": "assistant",
                "content": response.choices[0].message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response.choices[0].message.tool_calls
                ]
            })

            for tool_call in response.choices[0].message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"Ejecutando herramienta: {tool_name} con args: {tool_args}")

                if tool_name == "generar_resumen_IA":
                    resultado = await generar_resumen_IA(chat_id, tool_args.get("cantidad mensajes"), tool_args.get("paginacion"))
                elif tool_name == "consultar_internet_IA":
                    resultado = consultar_internet_IA(tool_args.get("buscar"))
                elif tool_name == "consultar_resultado_deportivo_IA":
                    resultado = consultar_resultado_deportivo_IA(tool_args.get("buscar"))
                elif tool_name == "consultar_partido_deportivo_en_vivo_IA":
                    resultado = consultar_partido_deportivo_en_vivo_IA(tool_args.get("buscar"))
                elif tool_name == "generar_reaccion_IA":
                    resultado = await generar_reaccion_IA(tool_args.get("emoji"))
                    return {"response": "emoji generado", "emoji": resultado}
                else:
                    resultado = "Función no reconocida"

                historial_conversacion[usuario].append({
                    "role": "tool",
                    # "tool_call_id": tool_call.id,
                    "content": f"Resultado de {tool_name}: {json.dumps(resultado, default=str)}"
                })

            final_response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=historial_conversacion[usuario]
            )

            contenido = final_response.choices[0].message.content or ""
            historial_conversacion[usuario].append({"role": "assistant", "content": contenido})
            return {"response": contenido}
        
        contenido = response.choices[0].message.content or ""
        historial_conversacion[usuario].append({"role": "assistant", "content": contenido})
        return {"response": contenido}
    except Exception as e:
        return {"error": str(e)}