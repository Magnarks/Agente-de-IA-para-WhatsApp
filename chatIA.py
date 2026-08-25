from dotenv import load_dotenv
import openai
import json
from config import settings
# from supertonic import TTS
import os
import subprocess
import base64
from tavily import TavilyClient, TavilyKeylessLimitError
from database_chatbot import consultar_mensajes, consultar_memorias, guardar_memoria, consultar_usuarios_grupo
from generador_imagenes import generar_imagen
from generador_memes import generar_meme_bytes
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

def listar_plantillas_memes_IA():
    PLANTILLAS_MEMES = {
        "reaching_restrained": {
            "nombre": "Guy reaching for balloon, held back",
            "identificador": "Balloon",
            "finalidad": (
                "Representa querer algo (arriba, panel feliz alcanzando el objeto) "
                "pero estar detenido/restringido por algo o alguien (abajo, "
                "figura rosa abrazando con fuerza mientras el personaje sigue "
                "estirando el brazo nervioso). Úsala para 'quiero hacer X pero "
                "Y me lo impide' — ansiedad, compromisos, relaciones posesivas, "
                "falta de tiempo/dinero, etc."
            ),
            "textos": [
                "Panel superior: el objeto/deseo (lo que se quiere alcanzar)",
                "Panel inferior, figura rosa: lo que te retiene/impide lograrlo",
                "Panel inferior, personaje: opcional, refuerza quién es 'tú' en la situación",
            ],
            "textos_requeridos": 3,
            "textos_opcionales": None,
        },
    
        "iq_bell_curve": {
            "nombre": "IQ Bell Curve / Midwit",
            "identificador": "BellCurve",
            "finalidad": (
                "Compara tres posturas ante la MISMA situación: el de IQ bajo "
                "(cara simple) y el de IQ alto (encapuchado, calmado) llegan a "
                "la MISMA conclusión simple por razones distintas (instinto vs "
                "sabiduría), mientras el de en medio ('midwit', con lentes, "
                "llorando/estresado) tiene la postura contraria, sobre-analizada "
                "y pretenciosa. Ideal para burlarse de opiniones "
                "'sobre-intelectualizadas' que ignoran lo obvio."
            ),
            "textos": [
                "Cara izquierda (IQ bajo): postura simple/directa",
                "Cara centro (Midwit): postura contraria, complicada/pretenciosa",
                "Cara derecha (IQ alto): misma postura simple que la izquierda, con justificación 'sabia'",
            ],
            "textos_requeridos": 3,
            "textos_opcionales": None,
        },
    
        "what_if_but_god_said": {
            "nombre": "What if You / But God said (dedo roto)",
            "identificador": "ButGodSaid",
            "finalidad": (
                "Plantea una expectativa ambiciosa o ilusión ('¿Qué tal si tú...') "
                "que es bruscamente frustrada por la realidad/destino ('Pero Dios "
                "dijo: no' — el dedo doblado/roto simboliza el plan arruinado). "
                "Tono de humor negro/absurdo para cuando algo sale mal de forma "
                "contundente e inesperada."
            ),
            "textos": [
                "Panel superior: la expectativa o plan ambicioso ('What if you...')",
                "Panel inferior: cómo la realidad lo arruinó ('But god said...')",
            ],
            "textos_requeridos": 2,
            "textos_opcionales": None,
        },
    
        "passing_notes_angry": {
            "nombre": "Pasando la nota en clase / reacción enojada",
            "identificador": "ClassNote",
            "finalidad": (
                "Panel 1: alguien comparte información/ayuda discretamente con "
                "otro (pasar una nota). Panel 2: un tercero descubre esto y "
                "reacciona con enojo/indignación mostrando el papel. Úsala para "
                "situaciones de 'alguien compartió algo a escondidas y otro lo "
                "descubrió molesto' — chismes, copiar tarea, un comentario agresivo, filtrar información."
            ),
            "textos": [
                "Panel 1: qué se está compartiendo/la nota (opcional, puede ir en el papel)",
                "Panel 2: la reacción de indignación del que descubre",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": None,
        },
    
        "tuxedo_winnie_pooh": {
            "nombre": "Tuxedo Winnie the Pooh (normal vs elegante)",
            "identificador": "Classy",
            "finalidad": (
                "Compara una versión simple/informal de un enunciado (Pooh "
                "normal, arriba) con la MISMA idea dicha de forma elegante/"
                "sofisticada (Pooh de esmoquin, abajo). Se usa para mostrar que "
                "algo 'suena mejor' o más pretencioso al reformularlo con "
                "palabras rebuscadas, aunque sea la misma idea."
            ),
            "textos": [
                "Panel superior (Pooh normal): la versión simple/casual del enunciado",
                "Panel inferior (Pooh de esmoquin): la misma idea dicha de forma elegante/rebuscada",
            ],
            "textos_requeridos": 2,
            "textos_opcionales": None,
        },
    
        "heidi_wheelchair_cliff": {
            "nombre": "Heidi empujando silla de ruedas al acantilado",
            "identificador": "Cliff",
            "finalidad": (
                "Humor negro: panel 1 muestra una conversación amistosa "
                "aparente (globos de diálogo vacíos para personalizar), panel 2 "
                "revela que en realidad terminó empujando a la otra persona por "
                "un acantilado. Úsala para 'lo que parecía una situación normal "
                "termina en traición/consecuencia extrema e inesperada', con "
                "tono absurdo/oscuro."
            ),
            "textos": [
                "Globo 1 (panel superior): lo que dice el personaje que empuja",
                "Globo 2 (panel superior): lo que dice el personaje en la silla",
            ],
            "textos_requeridos": 2,
            "textos_opcionales": None,
        },
    
        "coca_cola_mentos": {
            "nombre": "Coca-Cola y Mentos (combinación explosiva)",
            "identificador": "Cola",
            "finalidad": (
                "Representa la idea de mezclar dos cosas que, juntas, generan "
                "una reacción caótica/explosiva (la Coca-Cola y los caramelos "
                "Mentos causan una erupción física real). Úsala como metáfora "
                "de 'combinar X con Y = desastre/caos garantizado'."
            ),
            "textos": [
                "Etiqueta sobre la botella: el primer elemento de la mezcla",
                "Etiqueta sobre los dulces: el segundo elemento de la mezcla",
            ],
            "textos_requeridos": 2,
            "textos_opcionales": None,
        },
    
        "finally_scientist": {
            "nombre": "Científico con tubo de ensayo — 'FINALLY'",
            "finalidad": (
                "Foto de stock de un científico examinando un líquido verde con "
                "la palabra 'FINALLY' arriba. Se usa (a menudo con ironía) para "
                "celebrar haber logrado/descubierto/terminado algo, sin importar "
                "qué tan trivial sea en realidad."
            ),
            "textos": [
                "Texto superior (reemplaza 'FINALLY' si quieres): la exclamación de logro",
                "Opcional, en el tubo o pie de imagen: qué se logró",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": 1,
        },
    
        "epic_handshake": {
            "nombre": "Epic Handshake (apretón de manos musculoso)",
            "identificador": "PredatorHandshake",
            "finalidad": (
                "El icónico apretón de manos de Depredador. Representa que dos "
                "cosas/personas/grupos aparentemente distintos están de acuerdo "
                "o comparten algo en común ('X y Y son lo mismo'). Muy usado "
                "para unir dos ideas inesperadas bajo una coincidencia."
            ),
            "textos": [
                "Brazo izquierdo: primera cosa/persona/idea",
                "Brazo derecho: segunda cosa/persona/idea",
                "Centro: lo que ambas tienen en común",
            ],
            "textos_requeridos": 3,
            "textos_opcionales": None,
        },
    
        "winnie_pooh_grumpy_setup": {
            "nombre": "Winnie the Pooh 4 paneles (honey / but you know what I don't love)",
            "identificador": "Hate",
            "finalidad": (
                "Formato de 'setup + remate': Pooh expresa que ama algo (panel "
                "1), luego pregunta retóricamente qué no le gusta (panel 2), y "
                "los dos paneles finales (con cara cada vez más molesta) quedan "
                "en blanco para el remate/queja específica. Ideal para chistes "
                "de 'me encanta X, pero lo que NO soporto es Y'."
            ),
            "textos": [
                "Panel 4: el remate/queja específica, con molestia",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": None,
        },
    
        "types_of_headache_scale": {
            "nombre": "Tipos de dolor de cabeza (escala de severidad)",
            "identificador": "Headache",
            "finalidad": (
                "Diagrama comparativo de 4 niveles/tipos con severidad "
                "creciente (marcado en rojo sobre una cabeza, hasta cubrirla "
                "completa). Sirve como plantilla genérica de 'escala/tipos de "
                "X', reemplazando las etiquetas por cualquier categoría "
                "comparable en intensidad creciente."
                "Usala para 'niveles de molestia, dificultad, intensidad, gravedad, etc.'"
            ),
            "textos": [
                "Etiqueta 4 (cabeza completa roja): nivel extremo",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": None,
        },
    
        "cute_then_retarded_dog": {
            "nombre": "Aw look how cute / Oh no it's retarded",
            "identificador": "ItsRetarded",
            "finalidad": (
                "4 paneles: entusiasmo inicial al ver algo (persona señalando "
                "con emoción), luego se revela un defecto/problema (cara rara "
                "del perro), y los dos paneles finales muestran decepción. "
                "Úsalo para 'algo parecía genial al inicio pero resultó "
                "decepcionante/defectuoso'."
            ),
            "textos": [
                "Panel 4: texto de decepción o revelación del defecto/problema",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": None,
        },
    
        "goofy_threatening": {
            "nombre": "Goofy amenazante / persona en el piso",
            "identificador": "ItsTime",
            "finalidad": (
                "Estilo cómic en blanco y negro: una figura grande y agresiva "
                "(tipo Goofy) se para amenazante sobre alguien tirado en el "
                "piso, con globos de diálogo vacíos. Tono de humor negro para "
                "representar una amenaza/intimidación exagerada o absurda entre "
                "dos partes."
            ),
            "textos": [
                "Globo superior (figura amenazante): la amenaza/reclamo",
                "Globo inferior (persona en el piso): la respuesta/súplica",
            ],
            "textos_requeridos": 2,
            "textos_opcionales": None,
        },
    
        "knight_unaware_arrow": {
            "nombre": "Caballero medieval — flecha por llegar",
            "identificador": "Knight",
            "finalidad": (
                "Panel superior: caballero calmado y confiado con su espada al "
                "hombro. Panel inferior: el mismo caballero, con una "
                "flecha impactando en la unica apertura de su armadura. Representa 'estar tranquilo/"
                "confiado justo antes de que algo malo te tome por sorpresa' — "
                "ideal para ironía dramática o 'peligro inminente no percibido'."
            ),
            "textos": [
                "Panel superior: la situación de calma/confianza actual",
                "Panel inferior: el peligro que se aproxima sin que el personaje lo note",
            ],
            "textos_requeridos": 2,
            "textos_opcionales": None,
        },
    
        "reaction_looking_up_dread": {
            "nombre": "Reacción — mirando hacia arriba con temor",
            "identificador": "LookUp",
            "finalidad": (
                "Foto de reacción genérica: alguien mirando hacia arriba con "
                "expresión de temor/asombro/preocupación, tono azulado y "
                "ambiente tenso. Útil como reacción a una noticia mala, algo "
                "que se avecina, o sorpresa desagradable."
            ),
            "textos": [
                "Texto superior o pie de imagen: qué provoca la reacción de temor",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": None,
        },
    
        "decibel_scale_comparison": {
            "nombre": "Escala de decibeles (comparación de magnitud)",
            "identificador": "Loud",
            "finalidad": (
                "Línea de tiempo/escala horizontal que ordena elementos por "
                "intensidad (aquí, ruido en decibeles: moto, concierto, motor "
                "de avión, disparo de escopeta). Sirve como plantilla genérica "
                "para comparar la 'magnitud' o 'intensidad' de varias cosas en "
                "una misma escala, reemplazando los elementos por lo que "
                "corresponda al chiste."
            ),
            "textos": [
                "Elemento 1 (más bajo en la escala)",
                "Elemento 2",
                "Elemento 3",
                "Elemento 4 (más alto en la escala)",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": 1,
        },
    
        "evil_kermit": {
            "nombre": "Evil Kermit (Me: / También yo:)",
            "identificador": "MeAlsoMe",
            "finalidad": (
                "Kermit normal habla con una versión encapuchada/oscura de sí "
                "mismo. Representa el conflicto interno entre lo que 'deberías' "
                "hacer (Kermit normal) y el impulso tentador/malo (Kermit "
                "encapuchado) que termina ganando. Perfecto para autosabotaje o "
                "malas decisiones tentadoras."
            ),
            "textos": [
                "Etiqueta 'Me:' — el pensamiento racional/correcto",
                "Etiqueta 'También yo:' — el impulso tentador que susurra el Kermit oscuro",
            ],
            "textos_requeridos": 2,
            "textos_opcionales": None,
        },
    
        "exploited_cow_farmer": {
            "nombre": "Vaca exhausta / granjero alegre 'Good morning sunshine'",
            "identificador": "Milk",
            "finalidad": (
                "La vaca luce agotada y sobre-exprimida (varios chorros de "
                "leche), mientras el granjero llega feliz cargando muchos "
                "baldes vacíos más, ajeno o indiferente al cansancio de la "
                "vaca. Representa a alguien exigiendo más trabajo/esfuerzo a "
                "quien ya está exhausto, con tono irónico sobre explotación "
                "laboral. O también puede usarse para 'cuando alguien te pide más de lo que ya has hecho'."
                "O también cuando alguien abusa mucho de algo o repite un patrón de forma excesiva, sin importar el cansancio o la saturación del otro."
            ),
            "textos": [
                "Etiqueta sobre la vaca indicando qué tan exhausta está",
                "Opcional: Globo de diálogo del granjero (ya viene con 'Good morning sunshine')",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": 1,
        },
    
        "big_button_hesitation": {
            "nombre": "Mano dudando presionar el botón grande",
            "identificador": "NutButton",
            "finalidad": (
                "Una mano se acerca rápidamente a un botón grande, sin "
                "presionarlo aún. Se usa de forma irónica para reaccionar ante malas decisiones, "
                "actos absurdos o situaciones donde alguien cede de manera impulsiva ante algo."
            ),
            "textos": [
                "Etiqueta sobre el botón: la decisión/acción arriesgada a tomar"
            ],
            "textos_requeridos": 1,
            "textos_opcionales": None,
        },
    
        "choose_one_pills_grab_all": {
            "nombre": "'Choose One' — agarrando todas las pastillas",
            "identificador": "Pills",
            "finalidad": (
                "Se presentan varias opciones exclusivas para 'elegir una' "
                "(ej. sabiduría (roja), vida (verde), riqueza infinitas (amarilla)), pero la imagen final "
                "muestra unas manos agarrando la pastilla número 4 (azul), ignorando la regla. "
                "Representa negarse a elegir solo una opción por codicia, "
                "indecisión, o 'quiero exactamente eso'."
            ),
            "textos": [
                "Etiqueta de opción 4 (la que se agarra): la opción que se toma, ignorando las demás"
            ],
            "textos_requeridos": 1,
            "textos_opcionales": None,
        },

        "trade_offer": {
            "nombre": "Trade Offer",
            "identificador": "TradeOffer",
            "finalidad": (
                "Un usuario ofrece un intercambio, mostrando lo que está dispuesto a dar y lo que espera recibir. "
                "Se usa para representar situaciones de negociación, trueques o intercambios de cualquier tipo."
                "Representa de manera humorística o irónica los términos de un acuerdo, mostrando lo que cada parte aporta y espera a cambio."
                "Se puede usar para ilustrar situaciones de 'yo te doy X, tú me das Y', o para exagerar lo que alguien está dispuesto a ofrecer frente a lo que espera recibir."
            ),
            "textos": [
                "Etiqueta de lo que se ofrece: lo que el usuario está dispuesto a dar",
                "Etiqueta de lo que se espera recibir: lo que el usuario espera obtener a cambio",
                "Etiqueta de titulo: opcional, puede ser un encabezado o contexto para el intercambio",
            ],
            "textos_requeridos": 2,
            "textos_opcionales": 1,
        },

        "trump": {
            "nombre": "Trump",
            "identificador": "Trump",
            "finalidad": (
                "Una imagen de Donald Trump mostrando un papel con un mensaje. Se usa para representar declaraciones, anuncios o mensajes de manera humorística o irónica, a menudo exagerando la importancia o el dramatismo del contenido."
            ),
            "textos": [
                "Etiqueta en el papel: el mensaje o declaración que se quiere destacar",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": None,
        },

        "vape": {
            "nombre": "Vape",
            "identificador": "Vape",
            "finalidad": (
                "Una imagen con 2 paneles, en la de arriba una persona con un cigarrillo electrónico (vape) de forma tranquila y al lado un cuadro blanco donde se ilustra un texto"
                "y en la de abajo el mismo personaje expulsando el humo del vape con un gesto de sorpresa y al lado un cuadro blanco donde se ilustra otro texto"
                "Se usa para representar situaciones donde algo que parecía inofensivo o simple (arriba) se convierte en algo sorprendente, impactante o exagerado (abajo), a menudo con un giro humorístico o irónico."
            ),
            "textos": [
                "Etiqueta en el vape: el mensaje o declaración que se quiere destacar",
                "Etiqueta en el cuadro inferior: el mensaje o declaración que se quiere destacar",
            ],
            "textos_requeridos": 2,
            "textos_opcionales": None,
        },

        "yeshoney": {
            "nombre": "'YesHoney' / Si cariño",
            "identificador": "YesHoney",
            "finalidad": (
                "Una imagen de un personaje (un hombre con la cara desgastada, con cansancio y tristeza) diciendo 'YesHoney' con una expresión de resignación o aceptación, mientras que en el fondo se muestra a otra persona (Una mujer linda con suéter rojo y grandes senos) "
                "tocándose las manos. Se usa para representar situaciones donde alguien acepta o consiente algo a regañadientes, a menudo con un toque de humor o ironía."
                "Se puede usar cuando alguien está sumamente enamorado o enamorada o le gusta mucho una persona y hace lo que sea por la otra persona, incluso si no le gusta o no está de acuerdo con ello."
            ),
            "textos": [
                "Etiqueta en la mujer: el mensaje o declaración que se quiere destacar",
            ],
            "textos_requeridos": 1,
            "textos_opcionales": None,
        },
    }

    return PLANTILLAS_MEMES


async def generar_meme_IA(plantilla: str, argumentos: list):
    meme_bytes = generar_meme_bytes(plantilla, argumentos)
    if hasattr(meme_bytes, 'getvalue'):
        meme_bytes = meme_bytes.getvalue()
    print("Meme generado:", meme_bytes)
    return meme_bytes

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
        response = TavilyClient(api_key=settings.TAVILY_API_KEY).search(query=buscar, max_results=3, include_answer=True, include_raw_content=True , search_depth="advanced", include_images=True)
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

def buscar_video_yt_IA(buscar: str):

    if not buscar or not buscar.strip():
        return "No se proporcionó una consulta"
    
    try:
        response = TavilyClient(api_key=settings.TAVILY_API_KEY).search(query=f"https://www.youtube.com/results?search_query={buscar}", max_results=3, include_answer=True, search_depth="advanced")
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
    

# mimetypes aceptados como documentos procesables
_MIMETYPES_DOCUMENTO = {
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "application/xml",
    "text/xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
}

def extraer_texto_documento(doc_bytes: bytes, mimetype: str, filename: str = "") -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else ""

    if mimetype in ("text/plain", "text/csv", "application/json", "application/xml", "text/xml") or ext in ("txt", "csv", "json", "xml"):
        for enc in ("utf-8", "latin-1"):
            try:
                return doc_bytes.decode(enc)
            except UnicodeDecodeError:
                continue
        return doc_bytes.decode("utf-8", errors="replace")

    if mimetype == "application/pdf" or ext == "pdf":
        try:
            import pdfplumber, io
            with pdfplumber.open(io.BytesIO(doc_bytes)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            pass
        try:
            import pypdf, io
            reader = pypdf.PdfReader(io.BytesIO(doc_bytes))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            return "[PDF no soportado: instala pdfplumber o pypdf]"

    if mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or ext == "docx":
        try:
            import docx, io
            doc = docx.Document(io.BytesIO(doc_bytes))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            return "[DOCX no soportado: instala python-docx]"

    if mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or ext == "xlsx":
        try:
            import openpyxl, io
            wb = openpyxl.load_workbook(io.BytesIO(doc_bytes), data_only=True)
            lines = []
            for sheet in wb.worksheets:
                lines.append(f"[Hoja: {sheet.title}]")
                for row in sheet.iter_rows(values_only=True):
                    lines.append("\t".join("" if v is None else str(v) for v in row))
            return "\n".join(lines)
        except ImportError:
            return "[XLSX no soportado: instala openpyxl]"

    return f"[Tipo de documento no soportado: {mimetype}]"


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
            "name": "buscar_video_yt_IA",
            "description": "Busca videos en YouTube. Debe utilizarse para encontrar videos recientes, populares o específicos en la plataforma de YouTube. Usala cuando el usuario pregunte por un video, canción, tutorial, clip o cualquier contenido que pueda estar en YouTube. No olvides compartir el enlace del video en la respuesta. puedes complementar una respuesta con un ejemplo visual que pueda estar en youtube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "buscar": {
                        "type": "string",
                        "description": "Lo que toca buscar en YouTube."
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
            "description": """Genera una imagen basada en la descripción proporcionada por el usuario. Utilizar cuando el usuario solicite una imagen, foto, ilustración, dibujo, arte o cualquier representación visual. Traduce la descripción o prompt a inglés, esto con el fin de mejorar la precisión.
                            IMPORTANTE: junto con esta llamada, escribe SIEMPRE un mensaje de texto corto (en el mismo turno, como contenido de tu respuesta) que acompañe la imagen; ese texto se enviará como caption/pie de foto junto a la imagen generada. No dejes el mensaje vacío.
                            """,
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
            "name": "listar_plantillas_memes_IA",
            "description": "Lista las plantillas de memes disponibles, sus nombres y sus identificadores. Utilizar antes de generar un meme para conocer las plantillas disponibles.",
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generar_meme_IA",
            "description": """Genera un meme basado en la plantilla y el texto o textos proporcionados por el usuario. Utilizar cuando el usuario solicite un meme, imagen divertida, broma visual o cualquier representación humorística. Igualmente tu puedes usar esta función si lo consideras conveniente para responder, en ese caso usa una plantilla de meme que consideres oportuna con texto que igual consideres indicado.
                            Consulta la función listar_plantillas_memes_IA para conocer las plantillas de memes disponibles, sus nombres y sus identificadores (el identificador es el que se debe de usar para la función generar_meme_IA).
                            Recuerda que siempre debes usar la función listar_plantillas_memes_IA antes de llamar a esta para conocer que plantillas puedes usar. NO inventes plantillas.
                            IMPORTANTE: junto con esta llamada, escribe SIEMPRE un mensaje de texto corto (en el mismo turno, como contenido de tu respuesta) que acompañe el meme; ese texto se enviará como caption/pie de foto junto al meme generado. No dejes el mensaje vacío.
                            """,
            "parameters": {
                "type": "object",
                "properties": {
                    "plantilla": {
                        "type": "string",
                        "description": "El identificador de la plantilla del meme que se desea generar."
                    },
                    "argumentos": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Los textos que se desean incluir en el meme. El número de textos debe coincidir con la cantidad requerida por la plantilla seleccionada. puedes agregar textos opcionales si la plantilla lo permite."
                    }
                },
                "required": ["plantilla", "argumentos"]
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

# Tipos de mensaje de WhatsApp cuyo 'body' no es texto legible (stickers,
# medios, etc.) y puede venir como blob binario/base64 gigante.
_TIPOS_MENSAJE_NO_TEXTO = {"sticker", "image", "video", "audio", "ptt", "document", "vcard", "location"}

def sanitizar_texto_previo(body: str, tipo: str = None, max_len: int = 400) -> str:
    """Evita inyectar blobs binarios/base64 (stickers, medios) en el contexto del modelo."""
    if not body:
        return ""
    if tipo and tipo.lower() in _TIPOS_MENSAJE_NO_TEXTO:
        return f"[{tipo}]"
    if len(body) > max_len:
        return body[:max_len] + "... [contenido truncado]"
    return body

def construir_mensaje_miembros(chat_id):
    """
    Devuelve un mensaje 'system' con el mapeo Nombre -> lid del grupo,
    o None si no aplica (chat_id vacío, es un chat privado, o no hay
    miembros registrados en la BD para ese chat).
    """
    if not chat_id:
        return None
 
    miembros = consultar_usuarios_grupo(chat_id)
    if not miembros:
        return None
 
    lineas = []
    for m in miembros:
        nombre = m.get("name") or m.get("pushName") or "desconocido"
        lid = m.get("lid")
        if lid:
            lineas.append(f"- {nombre}: {lid}")
 
    if not lineas:
        return None
 
    contenido = (
        "Miembros del grupo (Nombre). Usa este valor "
        "cada vez que quieras mencionar a alguien en tu respuesta, en "
        "cualquier momento de la conversación (no solo al saludar). "
        "Nunca uses el número de teléfono, nunca inventes el nombre.\n"
        + "\n".join(lineas)
    )
    return {"role": "system", "content": contenido}


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

    if tool_name == "buscar_video_yt_IA":
        return buscar_video_yt_IA(tool_args.get("buscar")), None
 
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
            if contexto.get("texto_respuesta"):
                response_data["caption"] = contexto["texto_respuesta"]
            if contexto.get("reaccion_emoji"):
                response_data["emoji"] = contexto["reaccion_emoji"]
            return resultado_imagen, response_data
        return resultado_imagen, None

    if tool_name == "listar_plantillas_memes_IA":
        resultado_plantillas = listar_plantillas_memes_IA()
        return resultado_plantillas, None

    if tool_name == "generar_meme_IA":
        resultado_meme = await generar_meme_IA(tool_args.get("plantilla"), tool_args.get("argumentos"))
        if isinstance(resultado_meme, bytes):
            response_data = {
                "response": "meme generado",
                "meme_file": base64.b64encode(resultado_meme).decode("utf-8"),
            }
            print("Meme generado:", response_data["meme_file"][:30], "...")  # Mostrar solo los primeros 30 caracteres
            if contexto.get("texto_respuesta"):
                response_data["caption"] = contexto["texto_respuesta"]
            if contexto.get("reaccion_emoji"):
                response_data["emoji"] = contexto["reaccion_emoji"]
            return resultado_meme, response_data
        return resultado_meme, None
 
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

async def generar_caption_imagen_IA(usuario):
    """Pide al modelo un texto corto para acompañar la imagen/meme recién generado.
    Necesario porque el modelo no puede devolver content + tool_calls a la vez,
    por lo que el caption se pide en una llamada aparte, sin tools disponibles.
    """
    try:
        mensajes_temp = historial_conversacion[usuario] + [{
            "role": "user",
            "content": "Escribe un mensaje breve y natural (sin comillas) para acompañar la imagen que acabas de generar, como si fuera el pie de foto. Responde solo con ese texto."
        }]
        respuesta = client.chat.completions.create(
            model=MODEL_NAME,
            messages=mensajes_temp,
            tools=herramientas,
            tool_choice="none"
        )
        caption = respuesta.choices[0].message.content or ""
        caption, _ = limpiar_tool_calls_texto(caption)
        return caption
    except Exception as e:
        print(f"[WARN] No se pudo generar caption: {e}")
        return ""

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
            contenido_mensajes = "\n".join([f"- [{m.get('timestamp', '')}] {m.get('author', m.get('from', 'desconocido'))}: {sanitizar_texto_previo(m.get('body', ''), m.get('type'))}" for m in mensajes_previos])
            historial_conversacion[usuario].append({
                "role": "system",
                "content": f"Mensajes previos del chat:\n{contenido_mensajes}"
            })
        contador_llamadas[usuario] = 0
 
    # Actualizar fecha y recargar memorias cada RECARGAR_CADA llamadas
    contador_llamadas[usuario] = contador_llamadas.get(usuario, 0) + 1

    # --- FECHA: se actualiza SIEMPRE, en cada llamada, sin importar
    # RECARGAR_CADA. Es barato (no toca BD) y evita que conversaciones
    # de pocas llamadas (como "administrador", que solo recibe 2 en
    # toda su vida: startup y shutdown) queden con la hora congelada
    # desde el arranque del proceso.
    for i, msg in enumerate(historial_conversacion[usuario]):
        if msg.get("role") == "system" and "Fecha actual:" in msg.get("content", ""):
            historial_conversacion[usuario][i]["content"] = f"Fecha actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            break

    # --- MEMORIAS: esta sí se queda detrás de RECARGAR_CADA, porque
    # implica una consulta a la base de datos y no tiene sentido
    # pegarle a Mongo en cada mensaje.
    if contador_llamadas[usuario] % RECARGAR_CADA == 0:
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

        texto_miembros_actualizado = construir_mensaje_miembros(chat_id)
        if texto_miembros_actualizado:
            nuevo_msg_miembros = {"role": "system", "content": texto_miembros_actualizado}
            idx_miembros = next((i for i, msg in enumerate(historial_conversacion[usuario])
                                 if msg.get("role") == "system" and "Miembros del grupo" in msg.get("content", "")), None)
            if idx_miembros is not None:
                historial_conversacion[usuario][idx_miembros] = nuevo_msg_miembros
            else:
                historial_conversacion[usuario].insert(2, nuevo_msg_miembros)

        print(f"[INFO] Memorias y fecha actualizadas para {usuario} (llamada #{contador_llamadas[usuario]})")
 
    if b64 is None:
        # salvaguarda: nunca dejar crecer el contexto indefinidamente con un solo mensaje
        if len(mensaje) > 4000:
            mensaje = mensaje[:4000] + "... [contenido truncado]"
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
        elif tipo_b64 in _MIMETYPES_DOCUMENTO:
            doc_bytes_data = base64.b64decode(b64.get('data', ''))
            filename = b64.get('filename') or b64.get('name') or ''
            texto_doc = extraer_texto_documento(doc_bytes_data, tipo_b64, filename)
            MAX_CHARS_DOC = 12000
            if len(texto_doc) > MAX_CHARS_DOC:
                texto_doc = texto_doc[:MAX_CHARS_DOC] + "\n[... documento truncado ...]"
            prefijo = f"{mensaje}\n\n" if mensaje and mensaje.strip() else ""
            nombre_doc = filename or tipo_b64
            historial_conversacion[usuario].append({
                "role": "user",
                "content": f"{prefijo}[Documento: {nombre_doc}]\n{texto_doc}"
            })
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
            "texto_respuesta": None,
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
            print(f"[DEBUG] content: {msg.content!r}")
            print(f"[DEBUG] reasoning_content: {getattr(msg, 'reasoning_content', 'NO_ATTR')}")
            print(f"[DEBUG] model_extra: {msg.model_extra}")
 
            if not msg.tool_calls:
                contenido = msg.content or ""
                agoto_iteraciones = False
                break
 
            # texto que el modelo escribió junto al tool call (posible caption)
            contexto["texto_respuesta"] = msg.content or ""
 
            historial_conversacion[usuario].append({
                "role": "assistant",
                "content": msg.content or "",
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
                elif tool_name == "pedir_imagen_IA":
                    if isinstance(resultado, dict) and "artifacts" in resultado:
                        # guardar solo confirmación que se genero imagen, NO imagen ni base64 en el historial
                        contenido_tool_msg = "Imagen generada y enviada al usuario."
                    else:
                        contenido_tool_msg = f"Resultado de pedir_imagen_IA: {json.dumps(resultado, default=str)}"
                elif tool_name == "generar_meme_IA":
                    if isinstance(resultado, bytes):
                        contenido_tool_msg = "Meme generado y enviado al usuario."
                    else:
                        contenido_tool_msg = f"Resultado de generar_meme_IA: {json.dumps(resultado, default=str)}"
                else:
                    contenido_tool_msg = f"Resultado de {tool_name}: {json.dumps(resultado, default=str)}"
 
                historial_conversacion[usuario].append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": contenido_tool_msg
                })
 
            if respuesta_temprana is not None:
                if isinstance(respuesta_temprana, dict) and ("image_file" in respuesta_temprana or "meme_file" in respuesta_temprana) and not respuesta_temprana.get("caption"):
                    caption = await generar_caption_imagen_IA(usuario)
                    if caption:
                        respuesta_temprana["caption"] = caption
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