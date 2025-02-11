import streamlit as st
import pandas as pd
import datetime
import os
import uuid
import gspread
import time
import json
import pandas as pd
import base64 
# Inicializa Google Sheets con credenciales almacenadas en st.secrets
from google.oauth2.service_account import Credentials
from datetime import datetime
from pathlib import Path
from io import BytesIO
from openpyxl import load_workbook

# Función ajustada para cargar un rango específico de datos
def get_cached_data(sheet, session_key, rango=None):
    """
    Carga los datos de una hoja y los guarda en st.session_state.
    Tiene opción para limitar el rango de datos cargados.
    Si ya ha sido cacheada previamente, simplemente devuelve el caché.
    """
    if session_key not in st.session_state:
        try:
            if rango:  # Si se especifica un rango
                st.session_state[session_key] = sheet.get_values(rango)
            else:
                st.session_state[session_key] = sheet.get_all_records()
        except Exception as e:
            st.error(f"⚠️ Error al cargar los datos: {e}")
            st.stop()
    return st.session_state[session_key]

@st.cache_data
def cargar_hoja_completa(sheet):
    """
    Lee todos los registros de una hoja de cálculo y los almacena en caché para evitar
    múltiples solicitudes.
    """
    return sheet.get_all_records()


def guardar_en_hoja_sin_duplicados(hoja, datos, columnas=None, columna_unica="Número de Equipo"):
    """
       Guarda datos en la hoja de cálculo de Google evitando duplicados basados en una columna específica.
       """
    # Verifica si la hoja tiene datos existentes
    registros_existentes = hoja.get_all_records()
    valores_existentes = {registro[columna_unica] for registro in registros_existentes if columna_unica in registro}

    # Filtra los datos nuevos que ya existen en la hoja
    datos_filtrados = [fila for fila in datos if fila[columnas.index(columna_unica)] not in valores_existentes]

    if not datos_filtrados:
        st.warning("ℹ️ No hay nuevos datos para guardar. Todo ya está registrado.")
        return

    # Guardar solo los datos no duplicados
    hoja.append_rows(datos_filtrados)
    st.success(f"✅ Se han agregado {len(datos_filtrados)} nuevos registros a la hoja.")


def guardar_con_retraso(hoja, datos):
    """
    Función de escritura que aplica control de velocidad para evitar
    superar los límites de cuota.
    """
    hoja.append_rows(datos)
    time.sleep(2)  # Retraso de 2 segundos entre operaciones

# Define el alcance (scope) de autorización para Google Sheets
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Configurar credenciales usando las scopes necesarias
credentials_info = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)

# Usar las credenciales para autorizar gspread
gc = gspread.authorize(credentials)

# Acceso a la hoja
sheet_id = "1V7ST8vmpc5NVe3V1bfvE5WSRCiRRZv2LyxqW1Q5Bh3Y"
spreadsheet = gc.open_by_key(sheet_id)

# Carga las hojas disponibles
try:
    hoja_equipos = spreadsheet.worksheet("Inspeccion_Equipos")
except gspread.exceptions.WorksheetNotFound as e:
    st.error("⚠️ La hoja 'Inspeccion_Equipos' no se encontró en Google Sheets.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Error durante el acceso a la hoja: {e}")
    st.stop()

try:
    hoja_faltantes = spreadsheet.worksheet("Datos_Bodegas")
except gspread.exceptions.WorksheetNotFound as e:
    st.error("⚠️ La hoja 'Datos_Bodegas' no se encontró en Google Sheets.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Error durante el acceso a la hoja: {e}")
    st.stop()

# Ahora carga los datos de las hojas (utilizando las funciones de caché)
equipos_data = get_cached_data(hoja_equipos, "cached_equipos")
faltantes_data = get_cached_data(hoja_faltantes, "cached_faltantes")



# Función para generar IDs únicos
vuelo_id = str(uuid.uuid4())[:8]

# ---------- CONFIGURACIÓN DE SESIÓN ----------
if "pantalla" not in st.session_state:
    st.session_state.pantalla = 0
if "datos_generales" not in st.session_state:
    st.session_state.datos_generales = {}
if "equipos_inspeccionados" not in st.session_state:
    st.session_state.equipos_inspeccionados = []
if "datos_faltantes" not in st.session_state:
    st.session_state.datos_faltantes = []
if "datos_guardados" not in st.session_state:
    st.session_state.datos_guardados = False  # Inicializamos como False porque aún no se ha guardado nada

st.markdown(
    "<div style='padding: 1px; border: 1px solid #fa0303; border-radius: 1px; background-color: #fa0303;'>",
    unsafe_allow_html=True)

# Ruta de la imagen del encabezado
imagen_path = Path(__file__).parent / "imag" / "EMSA.png"

if imagen_path.exists():
    # Convertir la imagen a base64
    with open(imagen_path, "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode("utf-8")

    # Crear el cuadro con la imagen incrustada en base64 dentro del HTML
    st.markdown(
        f"""
        <div style="
            padding: 10px;
            border: 2px solid lightgray;
            background-color: white;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.1);
        ">
            <img src="data:image/png;base64,{base64_image}" style="width: 100%; border-radius: 5px;" />
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.warning("⚠️ Imagen de encabezado no encontrada.")

st.markdown(
    "<div style='padding: 1px; border: 1px solid #fa0303; border-radius: 1px; background-color: #fa0303; margin-top: 12px;'>",
    unsafe_allow_html=True)


# ---------- PANTALLA 1: DATOS GENERALES ----------
if st.session_state.pantalla == 1:
    st.markdown(
        """
        <style>
            .titulo-personalizado {
                background-color: #ff0000; /* Fondo rojo */
                color: white !important; /* Texto blanco asegurado */
                padding: 15px; /* Espaciado interno */
                text-align: center; /* Centrar el texto */
                border-radius: 5px; /* Bordes redondeados */
                font-size: 2.25rem; /* Tamaño equivalente a st.title */
                font-weight: bold; /* Texto en negrita */
                text-transform: uppercase; /* Convertir el texto a mayúsculas*/
                margin-bottom: 25px; /* Separación con contenido siguiente */
            }
        </style>
        <div class="titulo-personalizado">
            Checklist de Revisión GSE
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div style='text-align: center; font-size: 18px; background-color: #ffe7e7; padding: 20px; border-radius: 10px; 
                    border: 2px solid #FF0000;'>
            <p><b>Formulario para registrar la inspección de equipos motorizados y no motorizados en la atención a la aeronave. 
            Completar todos los campos obligatorios.</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Datos Generales")

    # Recuperar los valores previamente guardados en session_state
    fecha = st.date_input("Fecha", datetime.today() if 'Fecha' not in st.session_state.datos_generales else
    st.session_state.datos_generales["Fecha"])
    estacion = st.selectbox("Seleccione la Estación", ["CUE", "GYE", "LTX", "MEC", "OCC", "UIO"],
                            index=["CUE", "GYE", "LTX", "MEC", "OCC", "UIO"].index(
                                st.session_state.datos_generales.get("Estación", "CUE")))
    numero_vuelo = st.text_input("Número de Vuelo", value=st.session_state.datos_generales.get("Número de Vuelo", ""))
    aerolinea = st.selectbox("Seleccione la Aerolínea", ["American Airlines", "LATAM", "Emirates", "Delta", "KLM"],
                             index=["American Airlines", "LATAM", "Emirates", "Delta", "KLM"].index(
                                 st.session_state.datos_generales.get("Aerolínea", "American Airlines")))
    matricula = st.text_input("Matrícula de Aeronave", value=st.session_state.datos_generales.get("Matrícula", ""))
    pit_parqueo = st.text_input("PIT de Parqueo", value=st.session_state.datos_generales.get("PIT de Parqueo", ""))
    jefe_grupo = st.text_input("Nombre y Apellido de Jefe de Grupo",
                               value=st.session_state.datos_generales.get("Jefe de Grupo", ""))
    supervisor = st.text_input("Nombre y Apellido de Supervisor",
                               value=st.session_state.datos_generales.get("Supervisor", ""))

    # CSS para personalizar y alinear los botones
    st.markdown(
        """
        <style>
        /* Botón personalizado */
        div.stButton > button {
            background-color: #007bff; /* Color azul */
            color: white; 
            font-size: 16px; 
            padding: 8px 16px; 
            margin: 10px 5px;
            border: none; 
            border-radius: 8px; 
            cursor: pointer;
            transition: all 0.3s ease-in-out;
        }

        div.stButton > button:hover {
            background-color: #0056b3; /* Hover */
            transform: scale(1.05);
        }

        div.stButton > button:active {
            background-color: #003f7f; /* Active */
            transform: scale(0.97);
        }

        /* Botón "Inicio" con nuevo color (verde) */
        div[data-testid="stHorizontalBlock"] > div:first-child div.stButton > button {
            background-color: #28a745; /* Verde */
            color: white;
        }

        div[data-testid="stHorizontalBlock"] > div:first-child div.stButton > button:hover {
            background-color: #218838; /* Hover más oscuro para el verde */
            transform: scale(1.05);
        }

        div[data-testid="stHorizontalBlock"] > div:first-child div.stButton > button:active {
            background-color: #1e7e34; /* Active más oscuro */
            transform: scale(0.97);
        }

        /* Alinear botones de forma personalizada */
        div[data-testid="stHorizontalBlock"] > div:first-child div.stButton {
            text-align: left; /* Botón de la primera columna alineado a la izquierda */
        }

        div[data-testid="stHorizontalBlock"] > div:last-child div.stButton {
            text-align: right; /* Botón de la segunda columna alineado a la derecha */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Dividimos el espacio en dos columnas
    col1, col2 = st.columns([1, 1], gap="large")  # Dos columnas equilibradas

    # Botón "Inicio"
    with col1:
        if st.button("🏠 Inicio"):
            st.session_state.pantalla = 0  # Regresar a la pantalla inicial
            st.rerun()

    # Botón "Continuar"
    with col2:
        if st.button("➡️ Continuar"):
            errores = []

            # Validaciones
            if not estacion:
                errores.append("⚠️ Debes seleccionar la estación.")
            if not numero_vuelo:
                errores.append("⚠️ El número de vuelo es obligatorio.")
            if not aerolinea:
                errores.append("⚠️ Debes seleccionar una aerolínea.")
            if not matricula:
                errores.append("⚠️ La matrícula de la aeronave es obligatoria.")
            if not pit_parqueo:
                errores.append("⚠️ El PIT de parqueo es obligatorio.")
            if not jefe_grupo:
                errores.append("⚠️ El nombre y apellido del jefe de grupo son obligatorios.")
            if not supervisor:
                errores.append("⚠️ El nombre y apellido del supervisor son obligatorios.")

            # Si hay errores, mostrarlos
            if errores:
                for error in errores:
                    st.error(error)
            else:
                # Guardar datos en session_state
                st.session_state.datos_generales = {
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Estación": estacion,
                    "Número de Vuelo": numero_vuelo,
                    "Aerolínea": aerolinea,
                    "Matrícula": matricula,
                    "PIT de Parqueo": pit_parqueo,
                    "Jefe de Grupo": jefe_grupo,
                    "Supervisor": supervisor
                }
                # Generar vuelo_id si aún no existe
                if "vuelo_id" not in st.session_state:
                    st.session_state["vuelo_id"] = str(uuid.uuid4())[:8]

                # Avanzar a la siguiente pantalla
                st.session_state.pantalla = 2
                st.rerun()


# ---------- PANTALLA 2: SELECCIÓN DE EQUIPO ----------
elif st.session_state.pantalla == 2:
    st.markdown(
        """
        <style>
            .titulo-personalizado {
                background-color: #ff0000; /* Fondo rojo */
                color: white !important; /* Texto blanco asegurado */
                padding: 15px; /* Espaciado interno */
                text-align: center; /* Centrar el texto */
                border-radius: 5px; /* Bordes redondeados */
                font-size: 2.25rem; /* Tamaño equivalente a st.title */
                font-weight: bold; /* Texto en negrita */
                text-transform: uppercase; /* Convertir el texto a mayúsculas*/
                margin-bottom: 25px; /* Separación con contenido siguiente */
            }
        </style>
        <div class="titulo-personalizado">
            Selección de Equipo
        </div>
        """,
        unsafe_allow_html=True
    )

    # Inicialización de sesión si es la primera ejecución
    if "tipo_equipo" not in st.session_state:
        st.session_state.tipo_equipo = "Motorizado"
    if "equipo_seleccionado" not in st.session_state:
        st.session_state.equipo_seleccionado = ""
    if "cantidad" not in st.session_state:
        st.session_state.cantidad = 1

    equipos = {
        "Motorizado": ["Aire Acondicionado", "Agua Potable", "Arranque", "CBL", "Drenaje",
                       "Escalera", "GPU", "Loader", "Remolque", "Tractor"],
        "No Motorizado": ["Escalera", "Carreta", "Barra de Tiro", "Conos", ]
    }

    # Seleccione el tipo de equipo
    tipo_equipo = st.radio(
        "Seleccione el Tipo de Equipo",
        ["Motorizado", "No Motorizado"],
        index=["Motorizado", "No Motorizado"].index(st.session_state.tipo_equipo),
        key="radio_tipo_equipo"
    )

    # Reiniciar valores iniciales si el tipo de equipo se cambia
    if st.session_state.tipo_equipo != tipo_equipo:
        st.session_state.tipo_equipo = tipo_equipo
        st.session_state.equipo_seleccionado = ""  # Reset frente a cambio de categoría

    # Seleccione el equipo dependiendo del tipo
    opciones_equipos = equipos[st.session_state.tipo_equipo]
    try:
        equipo_seleccionado_index = opciones_equipos.index(st.session_state.equipo_seleccionado)
    except ValueError:
        equipo_seleccionado_index = 0  # Predeterminado al primer valor si no se encuentra

    equipo_seleccionado = st.selectbox(
        "Seleccione el equipo",
        [""] + opciones_equipos,
        index=equipo_seleccionado_index + 1,  # Ajustamos el índice porque agregamos una opción vacía
        key="selectbox_equipo"
    )

    # Actualizar en session_state
    st.session_state.equipo_seleccionado = equipo_seleccionado

    # Selección de la cantidad
    cantidad = st.number_input(
        "Cantidad de equipos",
        min_value=1,
        max_value=15,
        step=1,
        value=st.session_state.cantidad,
        key="cantidad_equipos"
    )
    st.session_state.cantidad = cantidad

    # Dividimos el espacio en dos columnas
    col1, col2 = st.columns([1, 1], gap="large")  # Dos columnas equilibradas

    # CSS para alinear los botones a la izquierda y derecha
    st.markdown("""
        <style>
        /* Alinear botones de forma personalizada */
        div[data-testid="stHorizontalBlock"] > div:first-child div.stButton {
            text-align: left; /* Botón de la primera columna alineado a la izquierda */
        }

        div[data-testid="stHorizontalBlock"] > div:last-child div.stButton {
            text-align: right; /* Botón de la segunda columna alineado a la derecha */
        }

        div.stButton > button {
            background-color: #007bff; /* Color azul de fondo */
            color: white; /* Texto blanco */
            padding: 12px 20px; /* Espacio interno del botón */
            border: none; /* Sin bordes */
            border-radius: 8px; /* Bordes redondeados */
            font-size: 17px; /* Tamaño del texto */
            font-weight: bold; /* Texto en negrita */
            cursor: pointer; /* Cursor en hover */
            box-shadow: 0px 3px 6px rgba(0, 0, 0, 0.15); /* Sombra sutil */
            transition: all 0.3s ease-in-out; /* Transición suave */
            width: auto; /* Evitar centrado automático */
        }

        div.stButton > button:hover {
            background-color: #0056b3; /* Fondo más oscuro en hover */
            transform: scale(1.05); /* Ligeramente más grande */
        }

        div.stButton > button:active {
            background-color: #003f7f; /* Fondo más oscuro al hacer clic */
            transform: scale(0.97); /* Contracción leve al hacer clic */
        }
        </style>
    """, unsafe_allow_html=True)

    # Botón "Volver" (alineado a la izquierda)
    with col1:
        if st.button("⬅️ Volver"):
            st.session_state.pantalla = 1  # Acción al presionar "Volver"
            st.rerun()

    # Botón "Continuar" (alineado a la derecha)
    with col2:
        if st.button("➡️ Continuar", key="boton_siguiente_p1"):

            if not equipo_seleccionado:  # Mostrar error si no hay equipo seleccionado
                st.error("⚠️ Debes seleccionar un equipo.")
            else:
                st.session_state.pantalla = 3  # Avanzar a la siguiente pantalla
                st.rerun()

# PANTALLA 3: EVALUACIÓN DE EQUIPOS
elif st.session_state.pantalla == 3:
    if "datos_inspeccion" not in st.session_state:
        st.session_state.datos_inspeccion = []

    st.markdown(
        """
        <style>
            .titulo-personalizado {
                background-color: #ff0000; /* Fondo rojo */
                color: white !important; /* Texto blanco asegurado */
                padding: 15px; /* Espaciado interno */
                text-align: center; /* Centrar el texto */
                border-radius: 5px; /* Bordes redondeados */
                font-size: 2.25rem; /* Tamaño equivalente a st.title */
                font-weight: bold; /* Texto en negrita */
                text-transform: uppercase; /* Convertir el texto a mayúsculas*/
                margin-bottom: 25px; /* Separación con contenido siguiente */
            }
        </style>
        <div class="titulo-personalizado">
            Evaluación de Equipos
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div style="text-align: center; 
                    font-size: 30px; 
                    background-color: #ffe7e7; 
                    padding: 10px; 
                    border-radius: 15px; 
                    border: 2px solid #FF0000;">
            <b>{st.session_state.equipo_seleccionado}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Preguntas personalizadas por tipo de equipo
    preguntas_por_equipo = {
        "Aire Acondicionado": ["Llantas", "Freno", "Calzos",
                               "Luces", "Extintor", "Enganche"],
        "Agua Potable": ["Llantas", "Freno", "Calzos", "Luces",
                         "Extintor"],
        "Arranque": ["Llantas", "Freno Pies", "Freno Mano",
                     "Cinturón", "Capuchon GPU", "Beacon"],
        "CBL": ["Llantas", "Freno", "Cinturón", "Calzos", "Luces",
                "Extintor", "Enganche", "Beacon"],
        "Drenaje": ["Llantas", "Freno", "Calzos", "Luces", "Extintor"],
        "Escalera": ["Llantas", "Estabilizadores", "Puertas Corredizas",
                     "Luces", "Bumpers", "Extintor", "Beacon"],
        "GPU": ["Llantas", "Freno", "Calzos", "Luces", "Bumpers", "Barra",
                "Extintor", "Enganche", "Capuchon GPU"],
        "Loader": ["Llantas", "Freno Pies", "Freno Mano", "Cinturón", "Calzos",
                   "Luces", "Bumpers", "Extintor", "Beacon"],
        "Remolque": ["Llantas", "Freno", "Calzos", "Luces", "Bumpers", "Extintor",
                     "Enganche", "Beacon"],
        "Tractor": ["Llantas", "Freno Pies", "Freno Mano", "Cinturón", "Calzos",
                    "Luces", "Bumpers", "Extintor", "Enganche", "Beacon"],
        "Escalera": ["Llantas", "Calzos", "Luces", "Bumpers", "Estabilizadores", "Baranda"],
        "Carreta": ["Llantas", "Freno", "Barra", "Enganche", "Malla", "Argollas", "Cadena"],
        "Barra de Tiro": ["Llantas", "Pines", "Enganche"],
        "Conos": ["Estado general", "Cintas Reflectantes"],

    }

    # Usar datos_inspeccion del session_state para evitar que se sobrescriba
    datos_inspeccion = st.session_state.datos_inspeccion

    vuelo_id = st.session_state.get("vuelo_id", None)
    if not vuelo_id:
        st.error("⚠️ No se encuentra un Vuelo_ID generado. Vuelve a la pantalla anterior.")
        st.stop()

    for i in range(st.session_state.cantidad):
        st.markdown(f"### Inspección del equipo {i + 1}")

        # Número del equipo
        numero_equipo = st.text_input(
            f"Número del equipo {i + 1}",
            value=st.session_state.get(f"num_eq_{i}", ""),
            key=f"num_eq_{i}"
        ).strip()

        if not numero_equipo:
            st.error(f"⚠️ El Número de Equipo es obligatorio para el equipo {i + 1}.")
            st.stop()

        # Crear el diccionario para agrupar todas las respuestas del equipo
        respuestas_por_equipo = {}
        for j, pregunta in enumerate(preguntas_por_equipo[st.session_state.equipo_seleccionado]):
            respuesta = st.radio(
                f"**{pregunta} ({i + 1})**",
                ["Operativo", "No Operativo", "No Aplica"],
                key=f"preg_{i}_{j}",
                horizontal=True
            )
            respuestas_por_equipo[pregunta] = respuesta  # Guardar la pregunta y respuesta

        # Capturar limpieza, observaciones e imagen
        limpieza = st.radio(
            f"¿Estado de limpieza del equipo {i + 1}?",
            ["Limpio", "Sucio"],
            key=f"limpieza_{i}",
            horizontal=True
        )
        observaciones = st.text_area(f"Observaciones {i + 1}", key=f"obs_{i}")
        imagen_subida = st.file_uploader(f"Subir foto del equipo {i + 1}", type=["png", "jpg", "jpeg"], key=f"img_{i}")

        # Guardar la imagen en una carpeta
        if not os.path.exists("imagenes"):
            os.makedirs("imagenes")

        imagen_path = None
        if imagen_subida:
            imagen_path = f"imagenes/{imagen_subida.name}"
            with open(imagen_path, "wb") as f:
                f.write(imagen_subida.getbuffer())

        # Crear inspecciones para cada pregunta
        for pregunta, respuesta in respuestas_por_equipo.items():
            # Crear un registro temporal para la inspección
            inspeccion = {
                "Vuelo_ID": st.session_state.get("vuelo_id"),
                "Tipo de Equipo": st.session_state.tipo_equipo,
                "Equipo": st.session_state.equipo_seleccionado,
                "Número de Equipo": numero_equipo,
                "Pregunta": pregunta,
                "Respuesta": respuesta,
                "Limpieza": limpieza,
                "Observaciones": observaciones.strip() if observaciones else "",
                "Imagen": imagen_path,
            }

            # Verificar si el registro ya existe antes de agregarlo
            if inspeccion not in st.session_state.datos_inspeccion:
                st.session_state.datos_inspeccion.append(inspeccion)

    # Agregar estilos personalizados para cada botón
    st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] > div:nth-child(1) div.stButton > button {
            background-color: #28a745; /* Verde */
            color: white; 
            font-size: 16px; 
            padding: 8px 16px; 
            border: none; 
            border-radius: 8px;
            cursor: pointer;
        }

        div[data-testid="stHorizontalBlock"] > div:nth-child(2) div.stButton > button {
            background-color: #007bff; /* Azul */
            color: white; 
            font-size: 16px; 
            padding: 8px 16px; 
            border: none; 
            border-radius: 8px;
            cursor: pointer;
        }

        div[data-testid="stHorizontalBlock"] > div:nth-child(3) div.stButton > button {
            background-color: #fd7e14; /* Naranja */
            color: white; 
            font-size: 16px; 
            padding: 8px 16px; 
            border: none; 
            border-radius: 8px;
            cursor: pointer;
        }

        div.stButton > button:hover {
            opacity: 0.9; /* Efecto hover común */
        }

        div.stButton > button:active {
            transform: scale(0.97); /* Efecto click */
        }
        </style>
    """, unsafe_allow_html=True)

    # Colocamos columnas con opciones de navegación
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        with col1:
            if st.button("✅ Agregar Otro Equipo"):
                errores = []  # Lista para almacenar errores
                for i in range(st.session_state.cantidad):
                    if not st.session_state.get(f"num_eq_{i}", "").strip():
                        errores.append(f"⚠️ Debes ingresar el número de equipo {i + 1}.")

                if errores:
                    for error in errores:
                        st.error(error)
                else:
                    # Validar que los datos inspeccionados existen en el estado
                    if "datos_inspeccion" not in st.session_state:
                        st.session_state.datos_inspeccion = []

                    # Aquí llamamos a la lógica para cada equipo inspeccionado
                    for registro in datos_inspeccion:
                        # Validar si el equipo ya fue agregado para evitar duplicados
                        if registro not in st.session_state.datos_inspeccion:
                            st.session_state.datos_inspeccion.append(registro)  # Agregar registro al estado

                    # Limpiar `datos_inspeccion` temporalmente solo para el nuevo equipo asegurando que no sobrescribe
                    datos_inspeccion.clear()

                    # Avanzar a inspeccionar otro equipo
                    st.session_state.cantidad += 1  # Incrementar la cantidad de equipos inspeccionados
                    st.rerun()

    with col2:
        if st.button("💾 Finalizar y Guardar", disabled=st.session_state.datos_guardados):

            # Validar si hay datos de inspección en sesión
            if not st.session_state.datos_inspeccion:
                st.error("⚠️ Debes ingresar al menos un equipo antes de guardar.")
            else:
                # Especificar el orden de las columnas requeridas
                columnas_requeridas = [
                    "Vuelo_ID", "Fecha", "Estación", "Número de Vuelo", "Aerolínea",
                    "Matrícula", "PIT de Parqueo", "Jefe de Grupo", "Supervisor",
                    "Tipo de Equipo", "Equipo", "Número de Equipo", "Pregunta",
                    "Respuesta", "Limpieza", "Observaciones", "Imagen"
                ]

                # Recuperar datos generales y datos de inspección desde el estado de sesión
                datos_generales = st.session_state.datos_generales
                datos_inspeccion = st.session_state.datos_inspeccion

                # Construir registros con orden correcto de las columnas
                registros_finales = []
                for registro in datos_inspeccion:
                    registro_final = {
                        "Vuelo_ID": registro["Vuelo_ID"],
                        "Fecha": datos_generales.get("Fecha", ""),
                        "Estación": datos_generales.get("Estación", ""),
                        "Número de Vuelo": datos_generales.get("Número de Vuelo", ""),
                        "Aerolínea": datos_generales.get("Aerolínea", ""),
                        "Matrícula": datos_generales.get("Matrícula", ""),
                        "PIT de Parqueo": datos_generales.get("PIT de Parqueo", ""),
                        "Jefe de Grupo": datos_generales.get("Jefe de Grupo", ""),
                        "Supervisor": datos_generales.get("Supervisor", ""),
                        "Tipo de Equipo": registro["Tipo de Equipo"],
                        "Equipo": registro["Equipo"],
                        "Número de Equipo": registro["Número de Equipo"],
                        "Pregunta": registro["Pregunta"],
                        "Respuesta": registro["Respuesta"],
                        "Limpieza": registro["Limpieza"],
                        "Observaciones": registro["Observaciones"],
                        "Imagen": registro["Imagen"],
                    }
                    registros_finales.append(registro_final)

                # Convertir a DataFrame con columnas en el orden correcto
                df_inspeccion = pd.DataFrame(registros_finales, columns=columnas_requeridas)

                # Verificar y agregar encabezados a la hoja si no existen
                encabezados_actuales = hoja_equipos.row_values(1)  # Leer los encabezados de la primera fila
                nuevos_encabezados = list(df_inspeccion.columns)  # Encabezados del DataFrame

                if not encabezados_actuales:  # Si los encabezados todavía no están presentes
                    hoja_equipos.insert_row(nuevos_encabezados, index=1)  # Agregar encabezados a la hoja
                    st.info("ℹ️ Encabezados agregados automáticamente a la hoja de cálculo.")

                # Guardar los datos reordenados en Google Sheets
                guardar_con_retraso(hoja_equipos, df_inspeccion.values.tolist())  # Guardar filas nuevas en la hoja

                # Mostrar mensajes de confirmación al usuario
                if not df_inspeccion.empty:
                    st.success(f"✅ {len(df_inspeccion)} registros guardados correctamente.")
                else:
                    st.info("ℹ️ No se encontraron registros nuevos para guardar.")

                # Bloquear futuros guardados y avanzar a la pantalla siguiente
                st.session_state.datos_guardados = True  # Evitar duplicado
                st.session_state.pantalla = 4  # Cambiar a la pantalla 4
                st.rerun()

    # Botón "Nuevo Equipo" para volver a la pantalla 2
    if st.button("➕ Nuevo Equipo"):
        # Cambiar a la pantalla de selección de equipo
        st.session_state.pantalla = 2  # Volver a Pantalla 2
        st.rerun()  # Recargar la app para ir a Pantalla 2

    # Inspección del equipo actual
    st.markdown(f"### Inspección del equipo: {st.session_state.get('equipo_seleccionado', 'No seleccionado')}")

    if st.session_state.get("equipo_seleccionado"):
        datos_inspeccion = []

        # (Lógica para realizar la inspección de equipos permanece aquí...)

    if st.button("⬅️ Volver"):
        st.session_state.pantalla = 2
        st.rerun()


# ---------- PANTALLA 4: CONFIRMACIÓN DE INSPECCIÓN ----------
elif st.session_state.pantalla == 4:
    st.title("✅ Inspección Guardada")
    st.success("La inspección ha sido agregada con éxito.")
    st.write(f"Total de equipos inspeccionados: {len(st.session_state.equipos_inspeccionados)}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🏠 Salir"):
            st.session_state.pantalla = 0
            st.session_state.equipos_inspeccionados = []
            st.rerun()
    with col2:
        if st.button("➕ Nueva Inspección"):
            st.session_state.clear()  # Limpia toda la sesión
            st.session_state.vuelo_id = str(uuid.uuid4())[:8]  # Genera un nuevo Vuelo_ID
            st.session_state.pantalla = 1
            st.rerun()

    with col3:
        if st.button("📋 Agregar Más Datos"):
            st.session_state.pantalla = 5
            st.rerun()



# PANTALLA 5: AGREGANDO DATOS FALTANTES
elif st.session_state.pantalla == 5:
    st.title("Agregar Datos Faltantes")

    # Obtener el Vuelo_ID actual
    vuelo_id = st.session_state.get("vuelo_id", None)
    if not vuelo_id:
        st.error("⚠️ No se encuentra un Vuelo_ID generado. Vuelve a la pantalla anterior.")
        st.stop()

    st.subheader(f"Datos Faltantes para el Vuelo: {vuelo_id}")

    # ----------- FORMULARIOS MEJORADOS PARA CADA BODEGA -----------

    # Bodega Main Deck
    st.markdown(
        "<div style='padding: 10px; border: 2px solid #008CBA; border-radius: 10px; background-color: #f0f8ff;'>",
        unsafe_allow_html=True)
    st.markdown("### 🛫 **Bodega (MAIN DECK)**")
    bodega_main_deck = st.selectbox("¿Calzos en Bodega (MAIN DECK)?", ["", "Sí", "No"], key="bodega_main_deck",
                                    help="¿Utilizó calzos en MAIN DECK?")

    hora_entrada_main_deck = st.time_input("Hora de Entrada (MAIN DECK)", key="hora_entrada_main_deck",
                                           help="Ingrese la hora de entrada al MAIN DECK")
    hora_salida_main_deck = st.time_input("Hora de Salida (MAIN DECK)", key="hora_salida_main_deck",
                                          help="Ingrese la hora de salida del MAIN DECK")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)  # Espaciado

    # Bodega Delantera (Lower Deck)
    st.markdown(
        "<div style='padding: 10px; border: 2px solid #FFA500; border-radius: 10px; background-color: #fff7e6;'>",
        unsafe_allow_html=True)
    st.markdown("### 🛬 **Bodega Delantera (LOWER DECK)**")
    punta_ala = st.selectbox("¿Punta de Ala?", ["", "Sí", "No"], key="punta_ala",
                             help="Seleccione si hay uso de punta de ala en LOWER DECK")

    hora_entrada_lower_front = st.time_input("Hora de Entrada (LOWER DECK Frontal)", key="hora_entrada_lower_front",
                                             help="Ingrese la hora de entrada al LOWER DECK Frontal")
    hora_salida_lower_front = st.time_input("Hora de Salida (LOWER DECK Frontal)", key="hora_salida_lower_front",
                                            help="Ingrese la hora de salida del LOWER DECK Frontal")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)  # Espaciado

    # Bodega Posterior (Lower Deck)
    st.markdown(
        "<div style='padding: 10px; border: 2px solid #28a745; border-radius: 10px; background-color: #e9fbe5;'>",
        unsafe_allow_html=True)
    st.markdown("### 🚚 **Bodega Posterior (LOWER DECK)**")
    bulk = st.selectbox("¿Bulk?", ["", "Sí", "No"], key="bulk", help="Seleccione si hubo uso de almacenamiento en bulk")

    hora_entrada_lower_rear = st.time_input("Hora de Entrada (LOWER DECK Posterior)", key="hora_entrada_lower_rear",
                                            help="Ingrese la hora de entrada al LOWER DECK Posterior")
    hora_salida_lower_rear = st.time_input("Hora de Salida (LOWER DECK Posterior)", key="hora_salida_lower_rear",
                                           help="Ingrese la hora de salida del LOWER DECK Posterior")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)  # Espaciado

    if "datos_guardados" not in st.session_state:
        st.session_state.datos_guardados = False  # Estado inicial: el botón está habilitado

    # Cuando el usuario haga clic en el botón "Guardar"
    if st.button("Guardar Datos Faltantes"):
        # ----------- VALIDAR CAMPOS OBLIGATORIOS Y HORAS DE CADA SECCIÓN -----------
        errores = []

        # Validar datos de la Bodega (MAIN DECK)
        if not bodega_main_deck or not hora_entrada_main_deck or not hora_salida_main_deck:
            errores.append("⚠️ Campos obligatorios en la Bodega (MAIN DECK) son requeridos.")
        elif hora_salida_main_deck <= hora_entrada_main_deck:
            errores.append(
                "⚠️ La hora de salida no puede ser menor o igual a la hora de entrada en la Bodega (MAIN DECK).")

        # Validar datos de la Bodega Delantera (LOWER DECK Frontal)
        if not punta_ala or not hora_entrada_lower_front or not hora_salida_lower_front:
            errores.append("⚠️ Campos obligatorios en la Bodega Delantera (LOWER DECK) son requeridos.")
        elif hora_salida_lower_front <= hora_entrada_lower_front:
            errores.append(
                "⚠️ La hora de salida no puede ser menor o igual a la hora de entrada en la Bodega Delantera (LOWER DECK).")

        # Validar datos de la Bodega Posterior (LOWER DECK Posterior)
        if not bulk or not hora_entrada_lower_rear or not hora_salida_lower_rear:
            errores.append("⚠️ Campos obligatorios en la Bodega Posterior (LOWER DECK) son requeridos.")
        elif hora_salida_lower_rear <= hora_entrada_lower_rear:
            errores.append(
                "⚠️ La hora de salida no puede ser menor o igual a la hora de entrada en la Bodega Posterior (LOWER DECK).")

        # Mostrar errores si los hubiera
        if errores:
            for error in errores:
                st.error(error)
        else:
            # ----------- PREPARAR LOS DATOS PARA GUARDAR EN GSPREAD -----------
            datos_faltantes = [
                # MAIN DECK
                {
                    "Vuelo_ID": vuelo_id,
                    "Sección": "Bodega (MAIN DECK)",
                    "Hora de Entrada": hora_entrada_main_deck,
                    "Hora de Salida": hora_salida_main_deck,
                    "Calzos": bodega_main_deck,
                    "Punta de Ala": "",
                    "Bulk": ""
                },
                # LOWER DECK (FRONTAL)
                {
                    "Vuelo_ID": vuelo_id,
                    "Sección": "Bodega Delantera (LOWER DECK)",
                    "Hora de Entrada": hora_entrada_lower_front,
                    "Hora de Salida": hora_salida_lower_front,
                    "Calzos": "",
                    "Punta de Ala": punta_ala,
                    "Bulk": ""
                },
                # LOWER DECK (POSTERIOR)
                {
                    "Vuelo_ID": vuelo_id,
                    "Sección": "Bodega Posterior (LOWER DECK)",
                    "Hora de Entrada": hora_entrada_lower_rear,
                    "Hora de Salida": hora_salida_lower_rear,
                    "Calzos": "",
                    "Punta de Ala": "",
                    "Bulk": bulk
                }
            ]

            # Crear un DataFrame para los datos
            df_faltantes = pd.DataFrame(datos_faltantes)

            # Reorganizar las columnas en el orden deseado
            columnas_ordenadas = [
                "Vuelo_ID",
                "Sección",
                "Hora de Entrada",
                "Hora de Salida",
                "Calzos",
                "Punta de Ala",
                "Bulk"
            ]
            df_faltantes = df_faltantes[columnas_ordenadas]  # Reorganizar las columnas
            df_faltantes = df_faltantes.fillna("").astype(str)  # Aseguramos compatibilidad

            # ----------- GUARDAR DATOS EN GOOGLE SHEETS -----------

            if not df_faltantes.empty:
                # Cargar encabezados actuales
                faltantes_data = get_cached_data(hoja_faltantes, "cached_faltantes")
                current_headers = faltantes_data[0].keys() if faltantes_data else []

                # Si no hay encabezados, escribirlos en la primera fila
                if not current_headers:  # Si no existen encabezados
                    hoja_faltantes.insert_row(df_faltantes.columns.tolist(),
                                              index=1)  # Insertar encabezados en la fila 1
                    st.info("Encabezados agregados en la hoja.")

                # Agregar los datos debajo de los encabezados
                guardar_con_retraso(hoja_faltantes, df_faltantes.values.tolist())  # Agregar los registros
                st.success("✅ Datos faltantes guardados en Google Sheets correctamente.")

                # Deshabilitar el botón de guardar
                st.session_state.datos_guardados = True  # Los datos ya se han guardado
            else:
                st.error("⚠️ Error al procesar los datos, no se guardaron.")

            # Navegar a Pantalla 6
            st.session_state.pantalla = 6  # Cambiar a pantalla 6
            st.rerun()  # Recargar Streamlit con la nueva configuración

# PANTALLA 6: FIN
elif st.session_state.pantalla == 6:

    # Título central llamativo
    st.title("¡Gracias por cumplir con tu deber! 🎉")
    st.markdown(
        """
        <div style='text-align: center; font-size: 18px; background-color: #f1f8ff; padding: 20px; border-radius: 10px; 
                    border: 2px solid #bbe1fa;'>
            <p><b>Con pequeñas acciones de <span style='color: #1b262c;'>compromiso</span>, garantizamos un servicio de calidad.</b></p>
            <p><i>💪 Juntos somos más fuertes y logramos grandes cosas. 🌟</i></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Espaciado estético
    st.markdown("<br>", unsafe_allow_html=True)

    # CSS para personalizar y alinear los botones
    st.markdown(
        """
        <style>
        /* Botón personalizado */
        div.stButton > button {
            background-color: #28a745; /* Color azul */
            color: white; 
            font-size: 16px; 
            padding: 8px 16px; 
            margin: 10px 5px;
            border: none; 
            border-radius: 8px; 
            cursor: pointer;
            transition: all 0.3s ease-in-out;
        }

        div.stButton > button:hover {
            background-color: #0056b3; /* Hover */
            transform: scale(1.05);
        }

        div.stButton > button:active {
            background-color: #003f7f; /* Active */
            transform: scale(0.97);
        }

        div[data-testid="stHorizontalBlock"] > div:first-child div.stButton > button:active {
            background-color: #1e7e34; /* Active más oscuro */
            transform: scale(0.97);
        }

        div[data-testid="stHorizontalBlock"] > div:last-child div.stButton {
            text-align: right; /* Botón de la segunda columna alineado a la derecha */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Colocamos columnas con opciones de navegación
    col1, col2 = st.columns([1, 1], gap="large")


    with col1:
        if st.button("🏠 Inicio", key="boton_inicio"):
            # Cambiar a la pantalla inicial amigable
            st.session_state.pantalla = 0  # Definimos la pantalla 0 como la de inicio
            st.rerun()

    with col2:
        if st.button("✚  Nueva Inspección", key="boton_nueva_inspeccion_inicio"):
            st.session_state.clear()  # Limpiar sesión para una nueva inspección
            st.session_state.vuelo_id = str(uuid.uuid4())[:8]  # Generar nuevo Vuelo_ID
            st.cache_data.clear()
            st.session_state.pantalla = 1  # Regresar a la pantalla inicial
            st.rerun()

    # Espaciado estético adicional
    st.markdown("<br><br>", unsafe_allow_html=True)

    # Mensaje final motivador
    st.markdown(
        """
        <div style='text-align: center; font-size: 16px; color: #3a506b;'>
            <p><i>¡Tu dedicación es clave para garantizar <b>seguridad</b> y <b>calidad</b>!</i></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# PANTALLA 0: PANTALLA "INICIO"
if st.session_state.pantalla == 0:
    # Pantalla inicial atractiva y amigable
    st.markdown(
        """
        <div style='text-align: center; font-size: 30px; color: #003366; padding: 20px; background-color: #f2f6fc; border-radius: 15px; margin-top: 20px;'>
            <h1>Bienvenido al Sistema de Inspección GSE</h1>
            <p style='font-size: 18px;'>Con esta herramienta, gestionamos inspecciones y datos con eficiencia y calidad.</p>
            <p style='font-size: 16px; color: #0073e6;'>¡Haga clic en la opción que desee para comenzar con confianza! ✈️</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # CSS para personalizar y alinear los botones
    st.markdown(
        """
        <style>
        /* Botón personalizado */
        div.stButton > button {
            background-color: #28a745; /* Color azul */
            color: white; 
            font-size: 16px; 
            padding: 8px 16px; 
            margin: 10px 5px;
            border: none; 
            border-radius: 8px; 
            cursor: pointer;
            transition: all 0.3s ease-in-out;
        }

        div.stButton > button:hover {
            background-color: #0056b3; /* Hover */
            transform: scale(1.05);
        }

        div.stButton > button:active {
            background-color: #003f7f; /* Active */
            transform: scale(0.97);
        }

        div[data-testid="stHorizontalBlock"] > div:first-child div.stButton > button:active {
            background-color: #1e7e34; /* Active más oscuro */
            transform: scale(0.97);
        }

        div[data-testid="stHorizontalBlock"] > div:last-child div.stButton {
            text-align: right; /* Botón de la segunda columna alineado a la derecha */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

   # Contenedor HTML para alinear el botón a la derecha
    st.markdown(
        """
        <div style="display: flex; justify-content: flex-end;">
            <button style="
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 12px;
                cursor: pointer;
            " onclick="window.location.reload(true);">
                ✚ Iniciar Inspección
            </button>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Manejador de eventos con el botón. Evento lógico en Python.
    if st.button("✚ Iniciar Inspección", key="boton_nueva_inspeccion_inicio"):
        st.session_state.clear()
        st.session_state.vuelo_id = str(uuid.uuid4())[:8]
        st.session_state.pantalla = 1
        st.cache_data.clear()
        st.rerun()

    # Imagen en el centro de la pantalla
    imagen_path = Path(__file__).parent / "imag" / "aeropuerto_de_quito_5.jpg"
    if imagen_path.exists():
        st.image(str(imagen_path), use_container_width=True,
             caption="Operaciones GSE seguras y eficientes.")
    else:
        st.warning("⚠️ Imagen de encabezado no encontrada.")
