from dotenv import load_dotenv
import openai
import json
from config import settings
# from supertonic import TTS
import os
import subprocess
import base64
from tavily import TavilyClient, TavilyKeylessLimitError
from database_chatbot import consultar_mensajes, consultar_memorias, guardar_memoria
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
contador_llamadas = {}
RECARGAR_CADA = 10  # Recargar memorias y fecha cada N llamadas por usuario

#fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

async def guardar_memoria_IA(remitente: str, id_remitente: str, memoria: str):
    resultado = guardar_memoria(remitente, id_remitente, memoria)
    print(f"Memoria guardada para {remitente} ({id_remitente}): {memoria}")
    return resultado

async def generar_resumen_IA(id_chat: str, numero_mensajes: int = 10):
    if id_chat != "":
        numero_mensajes = int(numero_mensajes or 10)
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

async def enviar_encuesta_IA(encuesta: str, opciones: list, multiple: bool = False):
    if not encuesta or not opciones:
        return {"error": "La encuesta y las opciones no pueden estar vacías."}
    print("Encuesta generada:", encuesta, opciones, multiple)
    return {"encuesta": encuesta, "opciones": opciones, "multiple": multiple}

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
            voz = settings.VOZ_FEMENINA
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
            "description": "Obtiene resultados de partidos ya finalizados o disputados anteriormente. Utilizar cuando el usuario pregunte quién ganó, cuánto quedó un partido, resultados históricos, estadísticas de encuentros terminados, tablas de posiciones o clasificación de torneos. No utilizar para partidos que se estén jugando en este momento. NO la utilices para crear encuestas, pronósticos, apuestas o juegos.",
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
                La reacción SIEMPRE va acompañada de una respuesta en texto.
                Solo puedes llamar generar_reaccion_IA UNA VEZ por mensaje del usuario. Nunca la llames dos veces en el mismo turno, incluso si cambias de opinión sobre el emoji.
                No vuelvas a llamar generar_reaccion_IA en este turno.
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
            "description": "Utiliza esta herramienta para guardar información importante que deba ser recordada en el futuro o para mantener futuras interacciones más personalizadas. Por ejemplo, si el usuario dice su nombre, su cumpleaños, su dirección, su número de teléfono, gustos, preferencias o cualquier otro dato personal que pueda ser útil recordar más adelante.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_encuesta_IA",
            "description": "Debes generar las opciones de respuesta (No generes mas de 12 opciones) y el texto de la encuesta basado en la solicitud del usuario. Utilizar cuando el usuario solicite enviar una encuesta, sondeo, votación o cualquier forma de recopilación de opiniones. NO consultes herramientas deportivas antes de generar la encuesta, salvo que el usuario solicite explícitamente información real del partido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "encuesta": {
                        "type": "string",
                        "description": "El texto de la encuesta."
                    },
                    "opciones": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "minItems":2,
                        "maxItems":12,
                        "description": "Las opciones de respuesta de la encuesta."
                    },
                    "multiple": {
                        "type": "boolean",
                        "description": "Indica si se permiten múltiples respuestas. Por defecto es falso."
                    }
                },
                "required": ["encuesta", "opciones"]
            }
        }
    }
]

MAX_ITERACIONES_TOOLS = 3  # límite de seguridad para evitar loops infinitos
 
 
async def ejecutar_tool(tool_name, tool_args, contexto):
    """
    Ejecuta una tool y devuelve (resultado, respuesta_temprana).
 
    - resultado: lo que se guarda como contenido del mensaje role='tool'
    - respuesta_temprana: dict a retornar INMEDIATAMENTE desde chat() (para
      los casos de audio/imagen/encuesta que cortan el flujo), o None si
      hay que seguir el ciclo normal (pedirle texto al modelo).
 
    contexto es un dict mutable con: usuario, id_usuario, chat_id,
    delivery_id, reaccion_emoji. Se muta in-place para que el emoji de
    reacción persista entre llamadas y quede disponible en el response final.
    """
    usuario = contexto["usuario"]
    id_usuario = contexto["id_usuario"]
    chat_id = contexto["chat_id"]
    delivery_id = contexto["delivery_id"]
 
    if tool_name == "generar_reaccion_IA":
        if contexto.get("reaccion_emoji"):
            return {"emoji": contexto["reaccion_emoji"], "ya_registrada": True}, None
        contexto["reaccion_emoji"] = await generar_reaccion_IA(tool_args.get("emoji"))
        return {"emoji": contexto["reaccion_emoji"]}, None
 
    if tool_name == "generar_resumen_IA":
        resultado = await generar_resumen_IA(chat_id, tool_args.get("numero_mensajes", 10))
        return resultado, None
 
    if tool_name == "generar_respuesta_audio_IA":
        texto_audio = tool_args.get("texto")
        tipo_voz = tool_args.get("tipo_voz", "masculina")
        _delivery_id = delivery_id or str(uuid.uuid4())
        resultado_audio = await generar_respuesta_audio_IA(texto_audio, _delivery_id, tipo_voz)
        if "audio_file" in resultado_audio:
            response_data = {"response": "audio generado", "audio_file": resultado_audio["audio_file"]}
            if contexto.get("reaccion_emoji"):
                response_data["emoji"] = contexto["reaccion_emoji"]
            return resultado_audio, response_data
        return resultado_audio, None
 
    if tool_name == "guardar_memoria_IA":
        resultado = await guardar_memoria_IA(usuario, id_usuario, tool_args.get("memoria"))
        return resultado, None
 
    if tool_name == "consultar_internet_IA":
        return consultar_internet_IA(tool_args.get("buscar")), None
 
    if tool_name == "consultar_resultado_deportivo_IA":
        resultado = consultar_resultado_deportivo_IA(tool_args.get("buscar"))
        if isinstance(resultado, dict) and not resultado.get("data"):
            resultado = ("No se encontraron resultados de partidos para este período. "
                         "Responde al usuario basándote en tu conocimiento general.")
        return resultado, None
 
    if tool_name == "consultar_partido_deportivo_en_vivo_IA":
        resultado = consultar_partido_deportivo_en_vivo_IA(tool_args.get("buscar"))
        if isinstance(resultado, dict) and not resultado.get("response"):
            resultado = ("No hay partidos en vivo disponibles en este momento según la API. "
                         "Proporciona al usuario tu pronóstico o análisis basado en tu "
                         "conocimiento general de los equipos.")
        return resultado, None
 
    if tool_name == "pedir_imagen_IA":
        resultado_imagen = await pedir_imagen_IA(tool_args.get("peticion"))
        if isinstance(resultado_imagen, dict) and "artifacts" in resultado_imagen:
            response_data = {
                "response": "imagen generada",
                "image_file": resultado_imagen["artifacts"][0]["base64"],
            }
            if contexto.get("reaccion_emoji"):
                response_data["emoji"] = contexto["reaccion_emoji"]
            return resultado_imagen, response_data
        return resultado_imagen, None
 
    if tool_name == "enviar_encuesta_IA":
        opciones = tool_args.get("opciones")
        resultado_encuesta = await enviar_encuesta_IA(
            tool_args.get("encuesta"),
            opciones,
            tool_args.get("multiple", False),
        )
        if isinstance(opciones, str):
            try:
                opciones = json.loads(opciones)
            except Exception:
                opciones = [opciones]
        if "encuesta" in resultado_encuesta:
            response_data = {
                "response": "encuesta generada",
                "encuesta": resultado_encuesta["encuesta"],
                "opciones": opciones,
                "multiple": resultado_encuesta["multiple"],
            }
            if contexto.get("reaccion_emoji"):
                response_data["emoji"] = contexto["reaccion_emoji"]
            return resultado_encuesta, response_data
        return resultado_encuesta, None
 
    return "Función no reconocida", None

async def chat(mensaje, remitente, id_remitente_grupo, chat_id, b64=None, delivery_id=None):
    usuario = remitente
    id_usuario = id_remitente_grupo
 
    if usuario not in historial_conversacion:
        historial_conversacion[usuario] = []
        historial_conversacion[usuario].append({"role": "system", "content": SYSTEM_MESSAGE})
        historial_conversacion[usuario].append({"role": "system", "content": f"Fecha actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"})
        # Cargar memorias previas del usuario
        memorias_previas = consultar_memorias(usuario, id_usuario)
        if memorias_previas:
            contenido_memorias = "\n".join([f"- [{m['fecha']}] {m['memoria']}" for m in memorias_previas])
            historial_conversacion[usuario].append({
                "role": "system",
                "content": f"Memorias del usuario almacenadas:\n{contenido_memorias}"
            })
        # Cargar contexto mensajes previos del chat
        mensajes_previos = consultar_mensajes(chat_id, 10)  # Obtener los últimos 10 mensajes del chat
        if mensajes_previos:
            contenido_mensajes = "\n".join([f"- [{m.get('timestamp', '')}] {m.get('author', m.get('from', 'desconocido'))}: {m.get('body', '')}" for m in mensajes_previos])
            historial_conversacion[usuario].append({
                "role": "system",
                "content": f"Mensajes previos del chat:\n{contenido_mensajes}"
            })
        contador_llamadas[usuario] = 0
 
    # Actualizar fecha y recargar memorias cada RECARGAR_CADA llamadas
    contador_llamadas[usuario] = contador_llamadas.get(usuario, 0) + 1
    if contador_llamadas[usuario] % RECARGAR_CADA == 0:
        for i, msg in enumerate(historial_conversacion[usuario]):
            if msg.get("role") == "system" and "Fecha actual:" in msg.get("content", ""):
                historial_conversacion[usuario][i]["content"] = f"Fecha actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                break
        memorias_actualizadas = consultar_memorias(usuario, id_usuario)
        if memorias_actualizadas:
            contenido_memorias = "\n".join([f"- [{m['fecha']}] {m['memoria']}" for m in memorias_actualizadas])
            nuevo_msg = {"role": "system", "content": f"Memorias del usuario actualizadas:\n{contenido_memorias}"}
            idx_memorias = next((i for i, msg in enumerate(historial_conversacion[usuario])
                                 if msg.get("role") == "system" and "Memorias del usuario" in msg.get("content", "")), None)
            if idx_memorias is not None:
                historial_conversacion[usuario][idx_memorias] = nuevo_msg
            else:
                historial_conversacion[usuario].insert(2, nuevo_msg)
        print(f"[INFO] Memorias y fecha actualizadas para {usuario} (llamada #{contador_llamadas[usuario]})")
 
    if b64 is None:
        historial_conversacion[usuario].append({"role": "user", "content": mensaje})
    else:
        tipo_b64 = b64.get('mimetype', None)
        if tipo_b64 == "image/jpeg":
            jpeg_base64 = b64.get("data")
            historial_conversacion[usuario].append({"role": "user", "content": [{"type": "text", "text": mensaje}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{jpeg_base64}"}}]})
        elif tipo_b64 == "audio/ogg":
            ogg_bytes = base64.b64decode(b64.get('data', None))
            if ogg_bytes is not None:
                process = subprocess.run(
                    ["ffmpeg", "-i", "pipe:0", "-f", "wav", "-ac", "1", "-ar", "16000", "pipe:1"],
                    input=ogg_bytes,
                    capture_output=True
                )
                wav_bytes = process.stdout
                wav_base64 = base64.b64encode(wav_bytes).decode()
                buscando_gemma = await transcribir_con_whisper_local(wav_bytes)
                if "gema" or "gemma" in buscando_gemma.lower():
                    historial_conversacion[usuario].append({"role": "user", "content": [{"type": "text", "text": "Transcribe el audio. Si NO escuchas las palabras: gemma o gema responde exactamente: IGNORAR_AUDIO Sin explicaciones adicionales. Si sí escuchas alguna de esas palabras, responde normalmente."}, {"type": "input_audio", "input_audio": {"data": wav_base64, "format": "wav"}}]})
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
 
        contexto = {
            "usuario": usuario,
            "id_usuario": id_usuario,
            "chat_id": chat_id,
            "delivery_id": delivery_id,
            "reaccion_emoji": None,
        }
 
        contenido = ""
        agoto_iteraciones = True
 
        for _ in range(MAX_ITERACIONES_TOOLS):
            print(f"[DEBUG] Enviando al modelo con {len(historial_conversacion[usuario])} mensajes")
            respuesta = client.chat.completions.create(
                model=MODEL_NAME,
                messages=historial_conversacion[usuario],
                tools=herramientas
            )
            msg = respuesta.choices[0].message
            print(f"[DEBUG] Tool calls: {msg.tool_calls}")
 
            if not msg.tool_calls:
                contenido = msg.content or ""
                agoto_iteraciones = False
                break
 
            historial_conversacion[usuario].append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in msg.tool_calls
                ]
            })
 
            respuesta_temprana = None
            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                print(f"Ejecutando herramienta: {tool_name} con args: {tool_args}")
 
                resultado, posible_respuesta_temprana = await ejecutar_tool(tool_name, tool_args, contexto)
                if posible_respuesta_temprana is not None:
                    respuesta_temprana = posible_respuesta_temprana
 
                if tool_name == "generar_reaccion_IA":
                    if isinstance(resultado, dict) and resultado.get("ya_registrada"):
                        contenido_tool_msg = (
                            f"Ya reaccionaste con '{contexto['reaccion_emoji']}' a este mensaje. "
                            "No vuelvas a llamar generar_reaccion_IA en este turno. "
                            "Responde al usuario con texto."
                        )
                    else:
                        contenido_tool_msg = f"Reacción '{contexto['reaccion_emoji']}' registrada. Ahora responde al usuario con texto."
                else:
                    contenido_tool_msg = f"Resultado de {tool_name}: {json.dumps(resultado, default=str)}"
 
                historial_conversacion[usuario].append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": contenido_tool_msg
                })
 
            if respuesta_temprana is not None:
                return respuesta_temprana
            # si no hubo corte anticipado, se vuelve a llamar al modelo
            # (con los resultados de las tools ya en el historial)
 
        if agoto_iteraciones:
            print(f"[WARN] Se alcanzaron las {MAX_ITERACIONES_TOOLS} iteraciones de tool calls sin respuesta de texto")
 
        reaccion_emoji = contexto["reaccion_emoji"]
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
 
        # Fallback si el modelo no devolvió texto: se le fuerza a responder
        # SOBRE EL MISMO HISTORIAL (que ya incluye los resultados de las tools),
        # solo que ahora sin poder volver a llamar herramientas.
        if not contenido:
            print("[WARN] Contenido vacío, forzando respuesta de texto con tool_choice='none'")
            try:
                fallback_resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=historial_conversacion[usuario],
                    tools=herramientas,
                    tool_choice="none"
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
 
    except Exception as e:
        return {"error": str(e)}