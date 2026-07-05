from dotenv import load_dotenv
import openai
import json
from config import settings
# from supertonic import TTS
import os
import subprocess
import base64
from tavily import TavilyClient, TavilyKeylessLimitError
from database_chatbot import consultar_mensajes, consultar_memorias
from generador_imagenes import generar_imagen
import whisper
import tempfile
from datetime import datetime
import requests
from omnivoice import OmniVoice
import soundfile as sf
import torch
import gc
import uuid
import re

load_dotenv(override=True)

client = openai.OpenAI(base_url=settings.OPENAI_API_BASE_URL, api_key=settings.OPENAI_API_KEY)
MODEL_NAME = settings.MODEL_NAME

SYSTEM_MESSAGE = settings.SYSTEM_MESSAGE

historial_conversacion = {}

fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def guardar_memoria_IA(remitente: str, id_remitente: str, memoria: str):
    from database_chatbot import guardar_memoria
    resultado = guardar_memoria(remitente, id_remitente, memoria)
    print(f"Memoria guardada para {remitente} ({id_remitente}): {memoria}")
    return resultado

async def generar_resumen_IA(id_chat: str, numero_mensajes: int):
    if id_chat != "":
        resumen = consultar_mensajes(id_chat, numero_mensajes)
        print("Resumen del chat obtenido: ", resumen)
        return resumen
    
async def generar_reaccion_IA(emoji: str):
    single_emoji = emoji.strip().split()[0] if emoji.strip() else "👍"
    print("Emoji generado:", single_emoji)
    return single_emoji

async def pedir_imagen_IA(peticion: str):
    imagen_pedida = generar_imagen(peticion)
    print("Imagen pedida:", imagen_pedida)
    return imagen_pedida

def limpiar_tool_calls_texto(contenido: str, reaccion_emoji=None):
    """Elimina patrones de tool calls filtrados como texto y extrae emojis de generar_reaccion_IA."""
    if not contenido:
        return contenido, reaccion_emoji

    emoji = reaccion_emoji

    # Extraer emoji de generar_reaccion_IA en cualquier formato conocido
    patrones_emoji = [
        r'<\|tool_call>call:generar_reaccion_IA\{emoji:"([^"]+)"\}<tool_call\|>',
        r'\[Tool call: generar_reaccion_IA\(emoji=["\']?([^\'"\)\]]+)["\']?\)\]',
        r'<tool_call>\s*generar_reaccion_IA[^<]*emoji["\s:=]+([^\s"\'<,}\]]+)',
    ]
    for patron in patrones_emoji:
        match = re.search(patron, contenido, flags=re.DOTALL | re.IGNORECASE)
        if match and not emoji:
            raw = match.group(1).strip()
            emoji = raw.split()[0] if raw else "👍"
            break

    # Eliminar todos los patrones conocidos de tool calls
    for patron in [
        r'<\|tool_call>.*?<tool_call\|>',
        r'\[Tool call:.*?\]',
        r'<tool_call>.*?</tool_call>',
        r'<function_calls>.*?</function_calls>',
        r'\{[^{}]*["\']?action["\']?\s*:\s*["\'][^"\']+["\'][^{}]*\}',
    ]:
        contenido = re.sub(patron, '', contenido, flags=re.DOTALL | re.IGNORECASE)

    return contenido.strip(), emoji

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

async def generar_respuesta_audio_IA(texto, delivery_id, tipo_voz="masculina"):
    try:
        if tipo_voz == "femenina":
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
                    }
                },
                "required": ["numero_mensajes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_internet_IA",
            "description": "Busca información actualizada en internet. Debe utilizarse para noticias, eventos recientes, lanzamientos de productos, cambios de versiones, resultados deportivos, clima y cualquier información que pueda haber cambiado después del entrenamiento del modelo. Si el usuario pregunta por una canción o letra de canción, si en la respuesta encuentras un enlace de YouTube, Spotify o Deezer, devuelvelo en la respuesta. No utilizar para resultados de partidos en vivo.",
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
                Siempre usa esta herramienta para reaccionar a cada mensaje con UN único emoji apropiado.
                La reacción SIEMPRE va acompañada de una respuesta en texto o audio.
                Solo retorna UN único emoji, nunca combines múltiples emojis.

                Ejemplos:
                - "jajaja" → 😂
                - "buen trabajo" → 👏
                - "felicidades" → 🎉
                - "golazo" → ⚽
                - "que tristeza" → 😢
                - pregunta técnica → 🤔
                - respuesta general → 👍
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
    },
    {
        "type": "function",
        "function": {
            "name": "generar_respuesta_audio_IA",
            "description": "Genera una respuesta en audio (nota de voz). Utilizar cuando el usuario solicite una respuesta en audio, nota de voz, mensaje hablado, que le hablen, en voz o cualquier forma de respuesta hablada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "texto": {
                        "type": "string",
                        "description": "El texto que se desea convertir en audio."
                    },
                    "tipo_voz": {
                        "type": "string",
                        "enum": ["femenina", "masculina"],
                        "description": "El tipo de voz a utilizar. Por defecto masculina."
                    }
                },
                "required": ["texto"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "guardar_memoria_IA",
            "description": "Utiliza esta herramienta para guardar información importante que deba ser recordada en el futuro. Por ejemplo, si el usuario te dice su nombre, su cumpleaños, su dirección, su número de teléfono o cualquier otro dato personal que pueda ser útil recordar más adelante.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memoria": {
                        "type": "string",
                        "description": "La información que se desea guardar en la memoria."
                    }
                },
                "required": ["memoria"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pedir_imagen_IA",
            "description": "Genera una imagen basada en la descripción proporcionada por el usuario. Utilizar cuando el usuario solicite una imagen, foto, ilustración, dibujo, arte o cualquier representación visual.",
            "parameters": {
                "type": "object",
                "properties": {
                    "peticion": {
                        "type": "string",
                        "description": "La petición o descripción de la imagen que se desea generar."
                    }
                },
                "required": ["peticion"]
            }
        }
    }
]

async def chat(mensaje, remitente, id_remitente_grupo, chat_id, b64=None, delivery_id=None):
    usuario = remitente
    id_usuario = id_remitente_grupo

    if usuario not in historial_conversacion:
        historial_conversacion[usuario] = []
        historial_conversacion[usuario].append({"role": "system", "content": SYSTEM_MESSAGE})
        historial_conversacion[usuario].append({"role": "system", "content": f"Fecha actual: {fecha_actual}"})
        # Cargar memorias previas del usuario
        memorias_previas = consultar_memorias(usuario, id_usuario)
        if memorias_previas:
            contenido_memorias = "\n".join([f"- [{m['fecha']}] {m['memoria']}" for m in memorias_previas])
            historial_conversacion[usuario].append({
                "role": "system",
                "content": f"Memorias del usuario almacenadas:\n{contenido_memorias}"
            })

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

            reaccion_emoji = None
            for tool_call in response.choices[0].message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"Ejecutando herramienta: {tool_name} con args: {tool_args}")

                if tool_name == "generar_resumen_IA":
                    resultado = await generar_resumen_IA(chat_id, tool_args.get("cantidad mensajes"))
                elif tool_name == "generar_respuesta_audio_IA":
                    texto_audio = tool_args.get("texto")
                    tipo_voz = tool_args.get("tipo_voz", "masculina")
                    _delivery_id = delivery_id or str(uuid.uuid4())
                    resultado_audio = await generar_respuesta_audio_IA(texto_audio, _delivery_id, tipo_voz)
                    if "audio_file" in resultado_audio:
                        response_data = {"response": "audio generado", "audio_file": resultado_audio["audio_file"]}
                        if reaccion_emoji:
                            response_data["emoji"] = reaccion_emoji
                        return response_data
                    resultado = resultado_audio
                elif tool_name == "guardar_memoria_IA":
                    resultado = await guardar_memoria_IA(usuario, id_usuario, tool_args.get("memoria"))
                elif tool_name == "consultar_internet_IA":
                    resultado = consultar_internet_IA(tool_args.get("buscar"))
                elif tool_name == "consultar_resultado_deportivo_IA":
                    resultado = consultar_resultado_deportivo_IA(tool_args.get("buscar"))
                    if isinstance(resultado, dict) and not resultado.get("data"):
                        resultado = "No se encontraron resultados de partidos para este período. Responde al usuario basándote en tu conocimiento general."
                elif tool_name == "consultar_partido_deportivo_en_vivo_IA":
                    resultado = consultar_partido_deportivo_en_vivo_IA(tool_args.get("buscar"))
                    if isinstance(resultado, dict) and not resultado.get("response"):
                        resultado = "No hay partidos en vivo disponibles en este momento según la API. Proporciona al usuario tu pronóstico o análisis basado en tu conocimiento general de los equipos."
                elif tool_name == "generar_reaccion_IA":
                    reaccion_emoji = await generar_reaccion_IA(tool_args.get("emoji"))
                    resultado = {"emoji": reaccion_emoji}
                elif tool_name == "pedir_imagen_IA":
                    resultado_imagen = await pedir_imagen_IA(tool_args.get("peticion"))
                    if "artifacts" in resultado_imagen:
                            response_data = {"response": "imagen generada", "image_file": resultado_imagen["artifacts"][0]["base64"]}
                            if reaccion_emoji:
                                response_data["emoji"] = reaccion_emoji
                            return response_data
                    resultado = resultado_imagen
                else:
                    resultado = "Función no reconocida"

                historial_conversacion[usuario].append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Resultado de {tool_name}: {json.dumps(resultado, default=str)}"
                })

            final_response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=historial_conversacion[usuario],
                tools=herramientas
            )

            # Si final_response también tiene tool_calls (ej: generar_reaccion_IA)
            if final_response.choices[0].message.tool_calls:
                historial_conversacion[usuario].append({
                    "role": "assistant",
                    "content": final_response.choices[0].message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        }
                        for tc in final_response.choices[0].message.tool_calls
                    ]
                })
                for tc in final_response.choices[0].message.tool_calls:
                    tc_args = json.loads(tc.function.arguments)
                    if tc.function.name == "generar_reaccion_IA" and not reaccion_emoji:
                        reaccion_emoji = await generar_reaccion_IA(tc_args.get("emoji"))
                        tc_resultado = {"emoji": reaccion_emoji}
                    elif tc.function.name == "pedir_imagen_IA":
                        tc_resultado = await pedir_imagen_IA(tc_args.get("peticion"))
                        if "artifacts" in tc_resultado:
                            response_data = {"response": "imagen generada", "image_file": tc_resultado["artifacts"][0]["base64"]}
                            if reaccion_emoji:
                                response_data["emoji"] = reaccion_emoji
                            return response_data
                    elif tc.function.name == "consultar_internet_IA":
                        tc_resultado = consultar_internet_IA(tc_args.get("buscar"))
                    elif tc.function.name == "guardar_memoria_IA":
                        tc_resultado = await guardar_memoria_IA(usuario, id_usuario, tc_args.get("memoria"))
                    elif tc.function.name == "generar_respuesta_audio_IA":
                        _did = delivery_id or str(uuid.uuid4())
                        tc_resultado = await generar_respuesta_audio_IA(tc_args.get("texto"), _did, tc_args.get("tipo_voz", "masculina"))
                        if "audio_file" in tc_resultado:
                            response_data = {"response": "audio generado", "audio_file": tc_resultado["audio_file"]}
                            if reaccion_emoji:
                                response_data["emoji"] = reaccion_emoji
                            return response_data
                    else:
                        tc_resultado = "ok"
                    historial_conversacion[usuario].append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tc_resultado, default=str)
                    })
                # Llamada final sin tools para obtener el texto
                text_response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=historial_conversacion[usuario],
                    tool_choice="none"
                )
                contenido = text_response.choices[0].message.content or ""
                contenido, reaccion_emoji = limpiar_tool_calls_texto(contenido, reaccion_emoji)
            else:
                contenido = final_response.choices[0].message.content or ""
            contenido, reaccion_emoji = limpiar_tool_calls_texto(contenido, reaccion_emoji)

            # Detectar pedir_imagen_IA si el modelo la llamó como texto en lugar de function call
            if 'pedir_imagen_IA' in contenido:
                match_peticion = re.search(r'["\']peticion["\']?\s*:\s*["\']([^"\']+)["\']', contenido, re.IGNORECASE)
                if match_peticion:
                    prompt_imagen = match_peticion.group(1)
                    print(f"[INFO] pedir_imagen_IA detectada como texto, ejecutando con: {prompt_imagen}")
                    resultado_img_txt = await pedir_imagen_IA(prompt_imagen)
                    if isinstance(resultado_img_txt, dict) and "artifacts" in resultado_img_txt:
                        rdata = {"response": "imagen generada", "image_file": resultado_img_txt["artifacts"][0]["base64"]}
                        if reaccion_emoji:
                            rdata["emoji"] = reaccion_emoji
                        historial_conversacion[usuario].append({"role": "assistant", "content": "Imagen generada"})
                        return rdata
                    contenido = re.sub(r'\{[^{}]*pedir_imagen_IA[^{}]*\}', '', contenido, flags=re.DOTALL | re.IGNORECASE).strip()

            # Fallback si el modelo retornó contenido vacío tras procesar tools
            if not contenido:
                print("[WARN] Contenido vacío tras procesar tools, llamada de fallback sin historial de tools")
                mensajes_sin_tools = [
                    m for m in historial_conversacion[usuario]
                    if m.get("role") not in ("tool",) and "tool_calls" not in m
                ]
                try:
                    fallback_resp = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=mensajes_sin_tools
                    )
                    contenido = fallback_resp.choices[0].message.content or ""
                    contenido, reaccion_emoji = limpiar_tool_calls_texto(contenido, reaccion_emoji)
                except Exception as fe:
                    print(f"[WARN] Error en fallback: {fe}")

            historial_conversacion[usuario].append({"role": "assistant", "content": contenido})
            response_data = {"response": contenido}
            if reaccion_emoji:
                response_data["emoji"] = reaccion_emoji
            return response_data
        
        contenido = response.choices[0].message.content or ""
        contenido, _ = limpiar_tool_calls_texto(contenido)
        historial_conversacion[usuario].append({"role": "assistant", "content": contenido})
        return {"response": contenido}
    except Exception as e:
        return {"error": str(e)}