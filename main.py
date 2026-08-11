import flet as ft
from datetime import datetime
import os
import sys
from types import ModuleType

# --- 1. MOCK REFORZADO PARA ANDROID ---
if "wsgiref" not in sys.modules:
    mock_wsgiref = ModuleType("wsgiref")
    mock_ss = ModuleType("simple_server")
    mock_util = ModuleType("util")

    class MockHandler:
        pass

    class MockServer:
        pass

    mock_ss.WSGIRequestHandler = MockHandler
    mock_ss.make_server = lambda *args, **kwargs: MockServer()
    sys.modules["wsgiref"] = mock_wsgiref
    sys.modules["wsgiref.simple_server"] = mock_ss
    sys.modules["wsgiref.util"] = mock_util
    mock_wsgiref.simple_server = mock_ss
    mock_wsgiref.util = mock_util


import gspread
from supabase import create_client, Client

SUPABASE_URL = "https://sqyitowpahouqglsrcil.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNxeWl0b3dwYWhvdXFnbHNyY2lsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYwODUwOTUsImV4cCI6MjEwMTY2MTA5NX0.RiDmI2styrbCJ4Ip4gCyVZdTJGGh-8CmN1B_tk6JEX0"

def obtener_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def obtener_consejo_ia(api_key, gastos_lista):
    import requests
    if not api_key:
        return "❌ Por favor, configurá tu Gemini API Key en el menú de arriba."
        
    if not gastos_lista:
        return "🤖 No tenés gastos registrados en la base de datos para analizar todavía. ¡Cargá algunos!"
        
    resumen = []
    for g in gastos_lista:
        resumen.append(
            f"- Detalle: {g.get('detalle')}, Monto: ${g.get('monto')}, Cuotas: {g.get('cuotas')}, Responsable: {g.get('responsable')}, Tarjeta: {g.get('tarjeta')}, Mes Inicio: {g.get('mes_inicio')}"
        )
    resumen_txt = "\n".join(resumen)
    
    prompt = (
        "Actúa como un asistente financiero personal y muy canchero, de Argentina, que le habla de forma graciosa, directa y con estilo neo-brutalista (usá modismos como che, ojo, mira, etc.). "
        "Analizá la siguiente lista de gastos de tarjeta de crédito de este mes y dale un consejo financiero hiper-personalizado de no más de 3 líneas. "
        "Sé crítico si gasta mucho o decile algo divertido sobre sus prioridades. Sé bien conciso y directo al grano, sin rodeos.\n\n"
        f"Gastos actuales:\n{resumen_txt}"
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            try:
                parts = data["candidates"][0]["content"]["parts"]
                if parts:
                    return parts[0]["text"].strip()
            except Exception:
                pass
            return "🤖 No pude generar una recomendación en este momento."
        else:
            return f"❌ Error de la API de Gemini (Status {response.status_code})"
    except Exception as e:
        return f"❌ Error al conectar con el asistente de IA: {str(e)}"



# --- 2. CONEXIÓN ---
def obtener_cliente():
    base_dir = os.path.dirname(os.path.abspath(__file__)) if __file__ else os.getcwd()
    posibles_rutas = [
        "creds.json",
        "assets/creds.json",
        os.path.join(base_dir, "creds.json"),
        os.path.join(base_dir, "assets", "creds.json"),
        os.path.join(os.getcwd(), "creds.json"),
    ]
    excepciones = []
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            try:
                return gspread.service_account(filename=ruta)
            except Exception as e:
                excepciones.append(f"{ruta}: {str(e)}")
    if excepciones:
        raise Exception("Error al cargar credenciales:\n" + "\n".join(excepciones))
    raise FileNotFoundError("No se encontró el archivo creds.json en ninguna de las rutas esperadas.")


# --- 3. LÓGICA DE FORMATO Y TOTALES ---
def formatear_y_totalizar(sheet, tarjeta):
    """
    Formatea colores, bordes y escribe fórmulas de totales alineadas a la nueva estructura:
      - Gastos agrupados arriba.
      - Totales de responsables abajo.
      - Total general al final.
    """
    data = sheet.get_all_values()
    inicio_bloque = None
    filas_total = []

    en_bloque = False
    for i, row in enumerate(data):
        row_str = " ".join(row).upper()
        if tarjeta.upper() in row_str and "TOTAL" not in row_str:
            en_bloque = True
            inicio_bloque = i + 2  # primera fila de datos (1-indexed)
            filas_total = []
        elif en_bloque:
            val_d = row[3].strip().upper() if len(row) > 3 else ""
            val_a = row[0].strip().upper() if len(row) > 0 else ""
            if val_d.startswith("TOTAL") or val_a.startswith("TOTAL"):
                filas_total.append(i + 1)
            elif filas_total and not any(c.strip() for c in row):
                break

    if not inicio_bloque or not filas_total:
        return

    data_start = inicio_bloque
    data_end = filas_total[0] - 1  # la fila antes del primer total
    fila_ultima_total = filas_total[-1]

    requests = []

    # 1. TÍTULO GENERAL DE LA HOJA (Fila 1 -> Index 0)
    # Fondo Azul Marino Oscuro, texto Blanco bold centrado, combinar de A1 a U1
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 21,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.08, "green": 0.17, "blue": 0.24},
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "fontSize": 12,
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)",
            }
        }
    )
    requests.append(
        {
            "mergeCells": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 21,
                },
                "mergeType": "MERGE_ALL",
            }
        }
    )

    # 2. CABECERA DE LAS COLUMNAS (Fila 2 -> Index 1)
    # Fondo Azul Pizarra, texto Blanco bold centrado, bordes inferiores gruesos
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": 1,
                    "endRowIndex": 2,
                    "startColumnIndex": 0,
                    "endColumnIndex": 21,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.18, "green": 0.30, "blue": 0.41},
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "fontSize": 10,
                            "bold": True,
                            "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        },
                        "borders": {
                            "bottom": {"style": "SOLID_MEDIUM"},
                            "top": {"style": "SOLID"},
                            "left": {"style": "SOLID"},
                            "right": {"style": "SOLID"},
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat,borders)",
            }
        }
    )
    # Combinar celdas de la cabecera (B2-C2 y D2-E2)
    requests.append(
        {
            "mergeCells": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": 1,
                    "endRowIndex": 2,
                    "startColumnIndex": 1,
                    "endColumnIndex": 3,
                },
                "mergeType": "MERGE_ALL",
            }
        }
    )
    requests.append(
        {
            "mergeCells": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": 1,
                    "endRowIndex": 2,
                    "startColumnIndex": 3,
                    "endColumnIndex": 5,
                },
                "mergeType": "MERGE_ALL",
            }
        }
    )

    # 3. BANNER DE LA TARJETA (VISA o MASTERCARD -> Index inicio_bloque - 2)
    # Fondo Gris/Celeste suave, texto Azul Marino bold centrado, combinar de A a U
    idx_banner = data_start - 2
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": idx_banner,
                    "endRowIndex": idx_banner + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 21,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.88, "green": 0.92, "blue": 0.94},
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "fontSize": 11,
                            "bold": True,
                            "foregroundColor": {"red": 0.08, "green": 0.17, "blue": 0.24},
                        },
                        "borders": {
                            "top": {"style": "SOLID"},
                            "bottom": {"style": "SOLID"},
                            "left": {"style": "SOLID"},
                            "right": {"style": "SOLID"},
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat,borders)",
            }
        }
    )
    requests.append(
        {
            "mergeCells": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": idx_banner,
                    "endRowIndex": idx_banner + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 21,
                },
                "mergeType": "MERGE_ALL",
            }
        }
    )

    # 4. Formato de moneda para columnas de dinero de gastos y totales
    # Total (Columna G -> Index 6)
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": data_start - 1,
                    "endRowIndex": fila_ultima_total,
                    "startColumnIndex": 6,
                    "endColumnIndex": 7,
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "CURRENCY", "pattern": '"$" #,##0.00'},
                    }
                },
                "fields": "userEnteredFormat(numberFormat)",
            }
        }
    )
    # Valor Cuota (Columna I -> Index 8)
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": data_start - 1,
                    "endRowIndex": fila_ultima_total,
                    "startColumnIndex": 8,
                    "endColumnIndex": 9,
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "CURRENCY", "pattern": '"$" #,##0.00'},
                    }
                },
                "fields": "userEnteredFormat(numberFormat)",
            }
        }
    )
    # Meses (Columnas J a U -> Index 9 a 21)
    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": data_start - 1,
                    "endRowIndex": fila_ultima_total,
                    "startColumnIndex": 9,
                    "endColumnIndex": 21,
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "CURRENCY", "pattern": '"$" #,##0.00'},
                    }
                },
                "fields": "userEnteredFormat(numberFormat)",
            }
        }
    )

    # Colores, Bordes y ALINEACIÓN CENTRADA
    for r in range(data_start, fila_ultima_total + 1):
        idx = r - 1
        row_data = data[idx] if idx < len(data) else []
        responsable = row_data[3] if len(row_data) > 3 else ""
        fila_str = " ".join(row_data).upper()

        if "TOTAL" in fila_str:
            # FILA DE TOTAL: Limpiar toda la fila (quitar bordes y pintar del azul profundo de fondo)
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": idx,
                            "endRowIndex": r,
                            "startColumnIndex": 0,
                            "endColumnIndex": 21,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.08, "green": 0.17, "blue": 0.24},  # Azul profundo
                                "borders": {
                                    "top": {"style": "NONE"},
                                    "bottom": {"style": "NONE"},
                                    "left": {"style": "NONE"},
                                    "right": {"style": "NONE"},
                                },
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,borders)",
                    }
                }
            )

            # Aplicar formato sólo a Columna D (Label) y Columnas J a U (Valores)
            color_total = {"red": 0.85, "green": 0.88, "blue": 0.92} # Azul Pizarra Suave Medio
            estilo_borde_inf = "DOUBLE" if tarjeta.upper() in fila_str else "SOLID"
            text_format_total = {
                "bold": True,
                "foregroundColor": {"red": 0.08, "green": 0.17, "blue": 0.24} # Azul Marino Grafito
            }
            
            # Formatear Columna D (Responsable - index 3 a 5 debido al merge)
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": idx,
                            "endRowIndex": r,
                            "startColumnIndex": 3,
                            "endColumnIndex": 5,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": color_total,
                                "horizontalAlignment": "CENTER",
                                "textFormat": text_format_total,
                                "borders": {
                                    "top": {"style": "SOLID"},
                                    "bottom": {"style": estilo_borde_inf},
                                    "left": {"style": "SOLID"},
                                    "right": {"style": "SOLID"},
                                },
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat,borders)",
                    }
                }
            )

            # Formatear Columnas J a U (Meses - index 9 a 21)
            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": idx,
                            "endRowIndex": r,
                            "startColumnIndex": 9,
                            "endColumnIndex": 21,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": color_total,
                                "horizontalAlignment": "CENTER",
                                "textFormat": text_format_total,
                                "borders": {
                                    "top": {"style": "SOLID"},
                                    "bottom": {"style": estilo_borde_inf},
                                    "left": {"style": "SOLID"},
                                    "right": {"style": "SOLID"},
                                },
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat,borders)",
                    }
                }
            )
        else:
            # FILA DE GASTOS: Borde sólido y color pastel desaturado de la paleta unificada
            color = {"red": 1, "green": 1, "blue": 1}
            if responsable.strip():
                h = sum(ord(c) for c in responsable.lower()) % 3
                if h == 0:
                    color = {"red": 0.92, "green": 0.945, "blue": 0.96} # Azul Pizarra Muy Suave
                elif h == 1:
                    color = {"red": 0.93, "green": 0.96, "blue": 0.95} # Verde Pizarra Muy Suave
                else:
                    color = {"red": 0.97, "green": 0.955, "blue": 0.92} # Gris Cálido Suave

            requests.append(
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": idx,
                            "endRowIndex": r,
                            "startColumnIndex": 0,
                            "endColumnIndex": 21,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": color,
                                "horizontalAlignment": "CENTER",
                                "borders": {
                                    "top": {"style": "SOLID"},
                                    "bottom": {"style": "SOLID"},
                                    "left": {"style": "SOLID"},
                                    "right": {"style": "SOLID"},
                                },
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,borders)",
                    }
                }
            )

        if "TOTAL" not in fila_str:
            # Combinar B con C
            requests.append(
                {
                    "mergeCells": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": idx,
                            "endRowIndex": r,
                            "startColumnIndex": 1,
                            "endColumnIndex": 3,
                        },
                        "mergeType": "MERGE_ALL",
                    }
                }
            )
        
        # Combinar D con E para todos (tanto gastos como totales) para que sea una celda unificada
        requests.append(
            {
                "mergeCells": {
                    "range": {
                        "sheetId": sheet.id,
                        "startRowIndex": idx,
                        "endRowIndex": r,
                        "startColumnIndex": 3,
                        "endColumnIndex": 5,
                    },
                    "mergeType": "MERGE_ALL",
                }
            }
        )

    if requests:
        sheet.spreadsheet.batch_update({"requests": requests})

    # --- FÓRMULAS DE TOTALES ---
    batch_values = []
    # Escribir fórmulas SUMIF para cada responsable individual
    # (todas las filas de totales excepto la última)
    for idx_t in range(len(filas_total) - 1):
        fila_t = filas_total[idx_t]
        cell_val = data[fila_t - 1][3].upper() if len(data[fila_t - 1]) > 3 else ""
        # Obtener el nombre del responsable desde 'TOTAL [NOMBRE]'
        nombre = cell_val.replace("TOTAL", "").strip()

        for col_idx in range(10, 22):
            letra = chr(64 + col_idx)
            # =SUMIF($D$data_start:$D$data_end; "NOMBRE"; letra$data_start:letra$data_end)
            if data_end >= data_start:
                formula = f'=SUMIF($D${data_start}:$D${data_end}; "{nombre}"; {letra}${data_start}:{letra}${data_end})'
            else:
                formula = 0.0
            batch_values.append({"range": f"{letra}{fila_t}", "values": [[formula]]})

    # Escribir fórmula SUM para la fila final de total general
    fila_general = filas_total[-1]
    if len(filas_total) > 1:
        fila_totales_inicio = filas_total[0]
        fila_totales_fin = filas_total[-2]
        for col_idx in range(10, 22):
            letra = chr(64 + col_idx)
            # =SUM(letra_totales_inicio:letra_totales_fin)
            formula = f"=SUM({letra}{fila_totales_inicio}:{letra}{fila_totales_fin})"
            batch_values.append({"range": f"{letra}{fila_general}", "values": [[formula]]})
    else:
        # Solo hay una fila de total general y no hay gastos ni otros totales. Escribir 0.0
        for col_idx in range(10, 22):
            letra = chr(64 + col_idx)
            batch_values.append({"range": f"{letra}{fila_general}", "values": [[0.0]]})

    if batch_values:
        sheet.batch_update(batch_values, value_input_option="USER_ENTERED")


# --- Helper para analizar monto numérico de forma robusta en cualquier locale ---
def parse_monto(monto_str):
    val_str = str(monto_str).replace("$", "").strip()
    if not val_str:
        return 0.0
    
    # Si tiene comas y puntos (ej: 1.500,50 o 1,500.50)
    if "," in val_str and "." in val_str:
        idx_comma = val_str.find(",")
        idx_dot = val_str.find(".")
        if idx_dot < idx_comma:
            # Estilo español/regional: 1.250,50
            val_str = val_str.replace(".", "").replace(",", ".")
        else:
            # Estilo inglés/US: 1,250.50
            val_str = val_str.replace(",", "")
    elif "," in val_str:
        # Solo coma: 1250,50 o 1,250
        partes = val_str.split(",")
        if len(partes[-1]) == 3 and len(partes) > 1:
            # Miles: 1,250
            val_str = val_str.replace(",", "")
        else:
            # Decimal: 1250,50 o 1250,5
            val_str = val_str.replace(",", ".")
    elif "." in val_str:
        # Solo punto: 1250.50 o 1.250
        partes = val_str.split(".")
        if len(partes[-1]) == 3 and len(partes) > 1 and len(partes[0]) <= 3:
            # Miles: 1.250
            val_str = val_str.replace(".", "")
        else:
            # Decimal: 1250.50
            pass
            
    try:
        return float(val_str)
    except Exception:
        return 0.0


# --- 4. PROCESO DE CARGA Y ELIMINACIÓN ---
def limpiar_planilla(ss):
    for sheet in ss.worksheets():
        if not sheet.title.startswith("Gastos "):
            continue
        try:
            data = sheet.get_all_values()
            rows_to_delete = []
            for idx, row in enumerate(data):
                row_num = idx + 1
                if row_num <= 3:
                    continue  # Mantener las primeras 3 filas de cabecera
                val_d = row[3].strip().upper() if len(row) > 3 else ""
                val_a = row[0].strip().upper() if len(row) > 0 else ""
                if val_d.startswith("TOTAL") or val_a.startswith("TOTAL"):
                    continue  # Mantener filas de totales
                # Si la fila tiene algún dato, la borramos
                if any(cell.strip() for cell in row):
                    rows_to_delete.append(row_num)
            
            # Borrar de abajo hacia arriba para no alterar índices
            for row_num in reversed(rows_to_delete):
                sheet.delete_rows(row_num)
        except Exception as e:
            print(f"Error al limpiar la hoja {sheet.title}: {str(e)}")


def eliminar_gasto(gasto_id, spreadsheet_id):
    try:
        supabase = obtener_supabase_client()
        supabase.table("gastos").delete().eq("id", gasto_id).execute()
        sincronizar_supabase_a_sheets(spreadsheet_id)
    except Exception as e:
        raise Exception(f"Error al eliminar gasto en Supabase: {str(e)}")


def obtener_ultimos_gastos(spreadsheet_id):
    try:
        supabase = obtener_supabase_client()
        res = supabase.table("gastos")\
            .select("*")\
            .eq("spreadsheet_id", spreadsheet_id)\
            .order("id", desc=True)\
            .limit(5)\
            .execute()
        # Mapear de base de datos a formato de UI de Flet
        gastos = []
        for g in (res.data or []):
            gastos.append({
                "id": g["id"],
                "fecha": g["fecha"],
                "detalle": g["detalle"],
                "responsable": g["responsable"],
                "monto": g["monto"],
                "cuotas": str(g["cuotas"]),
                "tarjeta": g["tarjeta"]
            })
        return gastos
    except Exception as e:
        print(f"Error al obtener gastos: {str(e)}")
        return []

def _cabeceras_hoja():
    """Devuelve la fila de cabeceras estándar de cada hoja de gastos."""
    return [
        "FECHA", "DETALLE", "", "RESPONSABLE", "",
        "ID-MES", "TOTAL", "CUOTAS", "VALOR CUOTA",
        "Ene", "Feb", "Mar", "Abr", "May", "Jun",
        "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
    ]


def normalizar_nombre(nombre):
    """
    Normaliza un nombre para comparar sin importar mayúsculas, tildes o espacios extras.
    Ej: 'alejo', 'Alejo ', 'ALEJO' → 'alejo'
         'María José' → 'maria jose'
    """
    import unicodedata
    nombre = nombre.strip()
    # Quitar tildes y caracteres diacríticos
    nombre = unicodedata.normalize("NFD", nombre)
    nombre = "".join(c for c in nombre if unicodedata.category(c) != "Mn")
    return nombre.lower()


def _nombre_en_fila_total(fila_str, nombre_norm):
    """
    Verifica si una fila TOTAL corresponde al nombre normalizado dado.
    fila_str: cadena UPPERCASE de la fila completa
    nombre_norm: nombre ya normalizado (lowercase, sin tildes)
    """
    if "TOTAL" not in fila_str:
        return False
    fila_norm = normalizar_nombre(fila_str.replace("TOTAL", "").strip())
    return fila_norm == nombre_norm


def inicializar_estructura(ss, año, responsable):
    """
    Crea la hoja 'Gastos {año}' si no existe, con la estructura mínima.
    Si la hoja existe pero está vacía, la inicializa.
    Estructura:
      Fila 1: título
      Fila 2: cabeceras
      Fila 3: VISA
      Fila 4: TOTAL {RESPONSABLE}
      Fila 5: (vacía separadora)
      Fila 6: MASTERCARD
      Fila 7: TOTAL {RESPONSABLE}
    """
    titulo_hoja = f"Gastos {año}"
    sheet = None
    try:
        sheet = ss.worksheet(titulo_hoja)
        # Si ya existe, verificar si tiene estructura (fila VISA o MASTERCARD)
        data = sheet.get_all_values()
        tiene_estructura = any(
            "VISA" in " ".join(r).upper() or "MASTERCARD" in " ".join(r).upper()
            for r in data
        )
        if tiene_estructura:
            return sheet
        # Tiene hoja pero sin estructura → inicializar
    except Exception:
        # No existe → crear hoja nueva
        sheet = ss.add_worksheet(title=titulo_hoja, rows=200, cols=21)

    resp_upper = responsable.strip().upper()
    cab = _cabeceras_hoja()
    filas = [
        [f"GASTOS {año} - TARJETAS"] + [""] * 20,
        cab,
        ["VISA"] + [""] * 20,
        ["", "", "", f"TOTAL {resp_upper}"] + [""] * 17,
        [""] * 21,
        ["MASTERCARD"] + [""] * 20,
        ["", "", "", f"TOTAL {resp_upper}"] + [""] * 17,
    ]
    # Limpiar hoja antes de escribir si ya tenía algo
    sheet.clear()
    sheet.update(range_name="A1", values=filas, value_input_option="USER_ENTERED")
    return sheet



# --- Old reestructurar_hoja_completa cleaned up ---

def sincronizar_supabase_a_sheets(spreadsheet_id):
    client = obtener_cliente()
    ss = client.open_by_key(spreadsheet_id)
    
    supabase = obtener_supabase_client()
    res = supabase.table("gastos").select("*").eq("spreadsheet_id", spreadsheet_id).execute()
    db_gastos = res.data or []
    
    años_activos = set()
    meses_l = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    
    for g in db_gastos:
        partes_fecha = g["fecha"].split("/")
        año_compra = int(partes_fecha[2]) if len(partes_fecha) == 3 else datetime.now().year
        try:
            mes_idx = meses_l.index(g["mes_inicio"])
        except ValueError:
            mes_idx = 0
        cant_cuotas = g["cuotas"]
        for c in range(cant_cuotas):
            mes_actual = mes_idx + c
            año_del_mes = año_compra + (mes_actual // 12)
            años_activos.add(año_del_mes)
            
    if not años_activos:
        años_activos.add(datetime.now().year)
        
    for año in sorted(list(años_activos)):
        try:
            sheet = ss.worksheet(f"Gastos {año}")
            # Verificación de estructura robusta (Self-Healing)
            data_check = sheet.get_all_values()
            
            cabeceras_ok = False
            if len(data_check) >= 2:
                cabeceras_actuales = data_check[1]
                cabeceras_esperadas = _cabeceras_hoja()
                if len(cabeceras_actuales) >= len(cabeceras_esperadas):
                    # Comparamos las primeras 21 columnas
                    if cabeceras_actuales[:21] == cabeceras_esperadas:
                        cabeceras_ok = True
            
            tiene_visa = any("VISA" in " ".join(r).upper() for r in data_check)
            tiene_master = any("MASTERCARD" in " ".join(r).upper() for r in data_check)
            
            if not cabeceras_ok or not tiene_visa or not tiene_master:
                # Si se detectan columnas rotas o eliminadas, eliminamos la hoja y la volvemos a crear limpia
                try:
                    ss.del_worksheet(sheet)
                except Exception:
                    pass
                primer_resp = db_gastos[0]["responsable"] if db_gastos else "Alejo"
                sheet = inicializar_estructura(ss, año, primer_resp)
        except Exception:
            primer_resp = db_gastos[0]["responsable"] if db_gastos else "Alejo"
            sheet = inicializar_estructura(ss, año, primer_resp)
            
        reestructurar_hoja_completa_desde_db(sheet, año, db_gastos)
        formatear_y_totalizar(sheet, "VISA")
        formatear_y_totalizar(sheet, "MASTERCARD")


def reestructurar_hoja_completa_desde_db(sheet, año, db_gastos):
    meses_l = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    
    gastos_visa = []
    gastos_master = []
    
    for g in db_gastos:
        partes_fecha = g["fecha"].split("/")
        g_año_compra = int(partes_fecha[2]) if len(partes_fecha) == 3 else datetime.now().year
        try:
            g_mes_idx = meses_l.index(g["mes_inicio"])
        except ValueError:
            g_mes_idx = 0
            
        cant_cuotas = g["cuotas"]
        monto_total = g["monto"]
        valor_cuota = monto_total / cant_cuotas
        
        cuotas_en_este_año = []
        for c in range(cant_cuotas):
            mes_actual = g_mes_idx + c
            año_del_mes = g_año_compra + (mes_actual // 12)
            if año_del_mes == año:
                cuotas_en_este_año.append(mes_actual % 12)
                
        if cuotas_en_este_año:
            es_año_compra = (g_año_compra == año)
            det_label = g["detalle"] if es_año_compra else f"{g['detalle']} (Cont.)"
            
            id_mes = f"{str(g_año_compra)[2:]}-{meses_l[g_mes_idx][:3].lower()}"
            fila = [
                g["fecha"],
                det_label,
                "",
                g["responsable"],
                "",
                id_mes,
                float(monto_total),      # Escribir número puro (float)
                int(cant_cuotas),        # Escribir número puro (int)
                float(valor_cuota)       # Escribir número puro (float)
            ]
            for m in range(12):
                if m in cuotas_en_este_año:
                    fila.append("=")
                else:
                    fila.append("")
                    
            if g["tarjeta"].upper() == "VISA":
                gastos_visa.append(fila)
            else:
                gastos_master.append(fila)
                
    nuevas_filas = []
    nuevas_filas.append([f"GASTOS {año} - TARJETAS"] + [""] * 20)
    nuevas_filas.append(_cabeceras_hoja())
    
    # --- Reconstruir VISA ---
    nuevas_filas.append(["VISA"] + [""] * 20)
    gastos_visa_sorted = sorted(gastos_visa, key=lambda x: (x[0], x[3].upper()))
    for g in gastos_visa_sorted:
        fila_idx_nueva = len(nuevas_filas) + 1
        for m_idx in range(9, 21):
            if g[m_idx] == "=":
                g[m_idx] = f"=$I{fila_idx_nueva}"
        nuevas_filas.append(g)
        
    resp_visa = set(g[3].upper() for g in gastos_visa_sorted)
    bonitos_visa = {r: r.title() for r in resp_visa}
    for r in sorted(list(resp_visa)):
        nombre = bonitos_visa[r]
        nuevas_filas.append(["", "", "", f"TOTAL {nombre.upper()}"] + [""] * 17)
    nuevas_filas.append(["", "", "", "TOTAL VISA"] + [""] * 17)
    
    # Separador
    nuevas_filas.append([""] * 21)
    
    # --- Reconstruir MASTERCARD ---
    nuevas_filas.append(["MASTERCARD"] + [""] * 20)
    gastos_master_sorted = sorted(gastos_master, key=lambda x: (x[0], x[3].upper()))
    for g in gastos_master_sorted:
        fila_idx_nueva = len(nuevas_filas) + 1
        for m_idx in range(9, 21):
            if g[m_idx] == "=":
                g[m_idx] = f"=$I{fila_idx_nueva}"
        nuevas_filas.append(g)
        
    resp_master = set(g[3].upper() for g in gastos_master_sorted)
    bonitos_master = {r: r.title() for r in resp_master}
    for r in sorted(list(resp_master)):
        nombre = bonitos_master[r]
        nuevas_filas.append(["", "", "", f"TOTAL {nombre.upper()}"] + [""] * 17)
    nuevas_filas.append(["", "", "", "TOTAL MASTERCARD"] + [""] * 17)
    
    try:
        max_rows = sheet.row_count
        sheet.spreadsheet.batch_update({
            "requests": [
                {
                    "unmergeCells": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": 2,
                            "endRowIndex": max_rows,
                            "startColumnIndex": 0,
                            "endColumnIndex": 21,
                        }
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": 2,
                            "endRowIndex": max_rows,
                            "startColumnIndex": 0,
                            "endColumnIndex": 21,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.08, "green": 0.17, "blue": 0.24},
                                "borders": {
                                    "top": {"style": "NONE"},
                                    "bottom": {"style": "NONE"},
                                    "left": {"style": "NONE"},
                                    "right": {"style": "NONE"},
                                },
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,borders)",
                    }
                }
            ]
        })
    except Exception:
        pass
        
    sheet.clear()
    sheet.update(range_name="A1", values=nuevas_filas, value_input_option="USER_ENTERED")


def cargar_gasto(spreadsheet_id, detalle, monto, cuotas, responsable, mes_inicio, tarjeta):
    storage = LocalStorage()
    email = storage.get("user_email") or "usuario@gmail.com"
    monto_f = parse_monto(monto)
    cant_c = int(cuotas)
    
    try:
        supabase = obtener_supabase_client()
        gasto_data = {
            "user_email": email,
            "spreadsheet_id": spreadsheet_id,
            "fecha": datetime.now().strftime("%d/%m/%Y"),
            "detalle": detalle.strip().title(),
            "monto": monto_f,
            "cuotas": cant_c,
            "responsable": responsable.strip().title(),
            "mes_inicio": mes_inicio,
            "tarjeta": tarjeta.upper()
        }
        supabase.table("gastos").insert(gasto_data).execute()
    except Exception as e:
        raise Exception(f"Error al registrar en Supabase: {str(e)}")
        
    try:
        sincronizar_supabase_a_sheets(spreadsheet_id)
    except Exception as e:
        raise Exception(f"Error al sincronizar con Sheets: {str(e)}")


# --- 5. INTERFAZ FLET ---
class LocalStorage:
    def __init__(self):
        rutas_posibles = [
            os.environ.get("FILES_DIR"),
            os.environ.get("ANDROID_PRIVATE_FILES"),
            os.path.expanduser("~"),
            os.getcwd()
        ]
        self.filepath = None
        for r in rutas_posibles:
            if r:
                try:
                    # Asegurar que el directorio exista
                    os.makedirs(r, exist_ok=True)
                    path = os.path.join(r, ".tarjetita_storage.json")
                    # Intentar abrir para append para validar escritura
                    with open(path, "a", encoding="utf-8") as f:
                        pass
                    self.filepath = path
                    break
                except Exception:
                    continue
        if not self.filepath:
            self.filepath = os.path.join(os.path.expanduser("~"), ".tarjetita_storage.json")
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                import json
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def save(self):
        try:
            import json
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def clear(self):
        self.data = {}
        self.save()


def extraer_spreadsheet_id(url_o_id):
    url_o_id = url_o_id.strip()
    if "/d/" in url_o_id:
        partes = url_o_id.split("/d/")
        if len(partes) > 1:
            return partes[1].split("/")[0]
    return url_o_id


def main(page: ft.Page):
    # Usar siempre LocalStorage persistente en archivo para evitar que Android limpie la caché de client_storage
    storage = LocalStorage()

    page.title = "Tarjetita 2.0"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#C2D2C4"  # Sage green background as the canvas
    page.window_width = 450
    page.window_height = 800
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    input_style = {
        "border_color": "#2D2D2D",
        "focused_border_color": "#7D81F7",  # Lavender focused border
        "bgcolor": "#1A1A1A",
        "label_style": ft.TextStyle(color="#8E8E93"),
        "text_style": ft.TextStyle(color="#FFFFFF"),
        "border_radius": 14,
        "content_padding": 12,
    }

    def es_correo_valido(email):
        import re
        patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(patron, email))

    main_container = ft.Container(
        bgcolor="#121212",  # Deep charcoal phone screen body
        border_radius=28,
        padding=25,
        width=400,
        border=ft.Border.all(2, "#2C2C2C"),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=30,
            color="#4D000000",
            offset=ft.Offset(0, 15),
        ),
        margin=ft.Margin.only(top=15, bottom=15)
    )

    def mostrar_registro():
        email_input = ft.TextField(
            label="Tu Correo de Google",
            hint_text="tu.usuario@gmail.com",
            keyboard_type=ft.KeyboardType.EMAIL,
            width=320,
            **input_style
        )

        link_input = ft.TextField(
            label="Enlace o ID de la Planilla",
            hint_text="Pega el link compartido de tu planilla...",
            width=320,
            **input_style
        )
        
        reg_status = ft.Text("", color="#66FCF1", weight="bold", size=13, text_align="center")

        def registrar_click(e):
            email = email_input.value.strip()
            link_val = link_input.value.strip()

            if not email:
                reg_status.value = "❌ Ingresa tu correo de Google"
                reg_status.color = "#FF4C4C"
                page.update()
                return

            if not es_correo_valido(email):
                reg_status.value = "❌ Correo de Google inválido"
                reg_status.color = "#FF4C4C"
                page.update()
                return

            if not link_val:
                reg_status.value = "❌ Pega el Link o ID de tu Planilla"
                reg_status.color = "#FF4C4C"
                page.update()
                return
                
            reg_status.value = "⏳ Verificando acceso a tu planilla..."
            reg_status.color = "#66FCF1"
            page.update()
            
            try:
                ss_id = extraer_spreadsheet_id(link_val)
                
                # Probar conexión con la planilla del usuario
                client = obtener_cliente()
                ss = client.open_by_key(ss_id)
                
                storage.set("user_email", email)
                storage.set("spreadsheet_id", ss_id)
                
                reg_status.value = "✅ ¡Planilla vinculada con éxito!"
                reg_status.color = "#4CAF50"
                page.update()
                
                mostrar_app_principal(email, ss_id)
            except Exception as ex:
                reg_status.value = "❌ No se puede acceder a la planilla.\n¿La compartiste con permisos de Editor?"
                reg_status.color = "#FF4C4C"
                print(f"Error vinculando planilla: {str(ex)}")
                page.update()

        main_container.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.icons.Icons.CREDIT_CARD, color="#FE7A5C", size=36),  # Coral card icon
                        ft.Text(
                            "Tarjetita 2.0",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF"
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
                ft.Divider(color="#2D2D2D", thickness=1, height=10),

                # ── Instrucciones sin botones ──────────────────────────────
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Cómo conectar tu planilla:", size=13, weight="bold", color="#FFFFFF"),
                            ft.Text(
                                "1. Abrí Google Drive en tu navegador y creá una planilla nueva (o usá la que ya tenés).",
                                size=12, color="#8E8E93"
                            ),
                            ft.Text(
                                "2. En esa planilla, tocá Compartir e ingresá este correo con permiso de Editor:",
                                size=12, color="#8E8E93"
                            ),
                            ft.Container(
                                content=ft.Text(
                                    "creds-json@targetita-app.iam.gserviceaccount.com",
                                    size=11,
                                    color="#FE7A5C",  # Highlighted credentials in Coral
                                    selectable=True,
                                    text_align="center",
                                    weight="bold",
                                ),
                                bgcolor="#1A1A1A",
                                padding=10,
                                border_radius=8,
                                border=ft.Border.all(1, "#2D2D2D"),
                            ),
                            ft.Text(
                                "3. Copiá el enlace de tu planilla (Compartir → Copiar enlace) y pegalo acá abajo junto con tu correo de Google.",
                                size=12, color="#8E8E93"
                            ),
                        ],
                        spacing=8,
                    ),
                    bgcolor="#181818",
                    padding=16,
                    border_radius=16,
                    border=ft.Border.all(1, "#2D2D2D"),
                ),

                email_input,
                link_input,
                
                ft.ElevatedButton(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.Icons.LINK, color="#121212", size=18),
                            ft.Text("VINCULAR PLANILLA", weight=ft.FontWeight.BOLD, color="#121212", size=13),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    on_click=registrar_click,
                    width=320,
                    height=48,
                    style=ft.ButtonStyle(
                        bgcolor={"": "#7D81F7", "hovered": "#6C70E6"},  # Lavender button
                        shape=ft.RoundedRectangleBorder(radius=14),
                        color={"": "#121212"},
                        elevation={"": 2, "hovered": 4},
                    ),
                ),
                reg_status
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        page.update()

    def mostrar_app_principal(email, ss_id):
        tar = ft.Dropdown(
            label="Tarjeta",
            value="VISA",
            options=[ft.DropdownOption("VISA"), ft.DropdownOption("MASTERCARD")],
            col=12,
            **input_style
        )
        
        det = ft.TextField(
            label="Detalle de compra",
            capitalization=ft.TextCapitalization.SENTENCES,
            col=12,
            **input_style
        )
        
        mon = ft.TextField(
            label="Monto Total",
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix=ft.Text("$ ", style=ft.TextStyle(color="#FE7A5C")),
            col=7,
            **input_style
        )
        
        cuo = ft.TextField(
            label="Cuotas", 
            value="1", 
            keyboard_type=ft.KeyboardType.NUMBER, 
            col=5,
            **input_style
        )
        
        res = ft.TextField(
            label="Responsable",
            value=storage.get("ultimo_responsable") or "",
            hint_text="Tu nombre...",
            capitalization=ft.TextCapitalization.WORDS,
            col=6,
            **input_style
        )
        
        meses_l = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        
        mes = ft.Dropdown(
            label="Mes Inicio",
            value=meses_l[datetime.now().month - 1],
            options=[ft.DropdownOption(m) for m in meses_l],
            col=6,
            **input_style
        )

        st = ft.Text("", color="#66FCF1", weight="bold", size=14, text_align="center")
        recent_list = ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        def click_cargar(e):
            st.value = "⏳ Procesando en la nube..."
            st.color = "#66FCF1"
            page.update()

            if not det.value or not det.value.strip():
                st.value = "❌ Falta detalle de la compra"
                st.color = "#FF4C4C"
                page.update()
                return
                
            if not mon.value:
                st.value = "❌ Falta ingresar el monto"
                st.color = "#FF4C4C"
                page.update()
                return
                
            try:
                monto_parsed = parse_monto(mon.value)
                if monto_parsed <= 0:
                    st.value = "❌ El monto debe ser mayor a 0"
                    st.color = "#FF4C4C"
                    page.update()
                    return
            except ValueError:
                st.value = "❌ Monto inválido"
                st.color = "#FF4C4C"
                page.update()
                return

            try:
                cuotas_parsed = int(cuo.value)
                if cuotas_parsed <= 0:
                    st.value = "❌ Las cuotas deben ser al menos 1"
                    st.color = "#FF4C4C"
                    page.update()
                    return
            except ValueError:
                st.value = "❌ Las cuotas deben ser un entero"
                st.color = "#FF4C4C"
                page.update()
                return

            try:
                responsable = res.value.strip() if res.value else ""
                if not responsable:
                    st.value = "❌ Ingresá el nombre del responsable"
                    st.color = "#FF4C4C"
                    page.update()
                    return
                storage.set("ultimo_responsable", responsable)
                cargar_gasto(
                    ss_id, det.value, mon.value, cuo.value, responsable, mes.value, tar.value
                )
                st.value = "✅ ¡Gasto cargado correctamente!"
                st.color = "#4CAF50"
                det.value = ""
                mon.value = ""
                cuo.value = "1"
                page.update()
                click_refresh(None)
            except Exception as ex:
                st.value = f"❌ Error: {str(ex)}"
                st.color = "#FF4C4C"
                page.update()

        def click_refresh(e):
            recent_list.controls = [
                ft.Container(
                    content=ft.ProgressRing(color="#66FCF1"),
                    alignment="center",
                    padding=10
                )
            ]
            page.update()
            
            try:
                gastos = obtener_ultimos_gastos(ss_id)
                recent_list.controls = []
                if not gastos:
                    recent_list.controls.append(
                        ft.Text("No hay gastos registrados este mes.", color="#C5C6C7", size=13, text_align="center")
                    )
                else:
                    for idx_card, g in enumerate(gastos):
                        colores_tarjetas = ["#FE7A5C", "#7D81F7", "#FED34A", "#A0E7E5", "#F2BAC9"]
                        color_bg = colores_tarjetas[idx_card % len(colores_tarjetas)]

                        def make_delete_handler(gasto=g):
                            def handle_delete(e):
                                st.value = f"🗑️ Eliminando '{gasto['detalle']}'..."
                                st.color = "#FF4C4C"
                                page.update()
                                try:
                                    eliminar_gasto(
                                        gasto["id"],
                                        ss_id
                                    )
                                    st.value = "✅ ¡Gasto eliminado!"
                                    st.color = "#4CAF50"
                                    page.update()
                                    click_refresh(None)
                                except Exception as ex:
                                    st.value = f"❌ Error al eliminar: {str(ex)}"
                                    st.color = "#FF4C4C"
                                    page.update()
                            return handle_delete

                        recent_list.controls.append(
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Column(
                                            [
                                                ft.Text(f"{g['detalle']} - $ {g['monto']:.2f}", weight="bold", color="#121212", size=13),
                                                ft.Text(f"{g['fecha']} | {g['tarjeta']} | {g['responsable']} | {g['cuotas']} c.", color="#2D2D2D", size=10, weight="bold"),
                                            ],
                                            spacing=2,
                                            expand=True
                                        ),
                                        ft.IconButton(
                                            ft.icons.Icons.DELETE,
                                            icon_color="#121212",
                                            icon_size=18,
                                            on_click=make_delete_handler(g),
                                            tooltip="Eliminar este gasto"
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                bgcolor=color_bg,
                                padding=12,
                                border_radius=14,
                                border=ft.Border.all(1, "#2D2D2D")
                            )
                        )
                page.update()
            except Exception as ex:
                recent_list.controls = [
                    ft.Text(f"Error al cargar gastos: {str(ex)}", color="#FF4C4C", size=12, text_align="center")
                ]
                page.update()

        def click_sync(e):
            st.value = "⏳ Sincronizando con Google Sheets..."
            st.color = "#66FCF1"
            page.update()
            try:
                sincronizar_supabase_a_sheets(ss_id)
                st.value = "✅ ¡Planilla sincronizada correctamente!"
                st.color = "#4CAF50"
                page.update()
                click_refresh(None)
            except Exception as ex:
                st.value = f"❌ Error al sincronizar: {str(ex)}"
                st.color = "#FF4C4C"
                page.update()

        def abrir_config_ia(e):
            key_input = ft.TextField(
                label="Gemini API Key",
                value=storage.get("gemini_api_key") or "",
                password=True,
                can_reveal_password=True,
                **input_style
            )
            
            def guardar_key(e):
                storage.set("gemini_api_key", key_input.value.strip())
                dlg.open = False
                page.update()
                st.value = "✅ ¡API Key de Gemini guardada!"
                st.color = "#4CAF50"
                page.update()
                
            dlg = ft.AlertDialog(
                title=ft.Text("Configuración de Asistente IA 🤖", color="#FFFFFF", size=16, weight="bold"),
                content=ft.Column(
                    [
                        ft.Text("Ingresá tu API Key de Gemini para recibir sugerencias y análisis financiero personalizado.", size=12, color="#8E8E93"),
                        key_input,
                        ft.TextButton(
                            "Obtener API Key gratis en Google AI Studio",
                            url="https://aistudio.google.com/",
                            style=ft.ButtonStyle(color="#7D81F7")
                        )
                    ],
                    spacing=12,
                    height=180,
                    width=300
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(dlg, "open", False) or page.update(), style=ft.ButtonStyle(color="#FF4C4C")),
                    ft.ElevatedButton("Guardar", on_click=guardar_key, style=ft.ButtonStyle(bgcolor="#4CAF50", color="#FFFFFF"))
                ],
                bgcolor="#121212",
                shape=ft.RoundedRectangleBorder(radius=18),
            )
            page.dialog = dlg
            dlg.open = True
            page.update()

        ai_response_txt = ft.Text(
            "Acá aparecerá el análisis del Asistente IA...",
            color="#FFFFFF",
            size=12,
            italic=True
        )
        
        ai_container = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.Icons.AUTO_AWESOME, color="#FED34A", size=18),
                            ft.Text("ASISTENTE FINANCIERO IA", size=12, weight="bold", color="#FED34A"),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    ai_response_txt
                ],
                spacing=8
            ),
            bgcolor="#1A1A1A",
            border_radius=14,
            padding=14,
            border=ft.Border.all(1, "#2D2D2D"),
            visible=False
        )

        def click_consultar_ia():
            gemini_key = storage.get("gemini_api_key")
            if not gemini_key:
                abrir_config_ia(None)
                return
                
            ai_container.visible = True
            ai_response_txt.value = "⏳ Analizando tus consumos del mes con Inteligencia Artificial..."
            ai_response_txt.color = "#8E8E93"
            page.update()
            
            try:
                supabase = obtener_supabase_client()
                res_db = supabase.table("gastos").select("*").eq("spreadsheet_id", ss_id).execute()
                gastos_completos = res_db.data or []
                
                consejo = obtener_consejo_ia(gemini_key, gastos_completos)
                ai_response_txt.value = consejo
                ai_response_txt.color = "#FFFFFF"
                page.update()
            except Exception as ex:
                ai_response_txt.value = f"❌ Error: {str(ex)}"
                ai_response_txt.color = "#FF4C4C"
                page.update()

        btn_consultar_ia = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.Icons.AUTO_AWESOME, color="#FFFFFF", size=18),
                    ft.Text(
                        "PREGUNTAR AL ASISTENTE IA",
                        weight=ft.FontWeight.BOLD,
                        size=13,
                        color="#FFFFFF"
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            ),
            on_click=lambda e: click_consultar_ia(),
            width=360,
            height=40,
            style=ft.ButtonStyle(
                bgcolor={"": "#7D81F7", "hovered": "#6C70E6"},  # Lavender button
                shape=ft.RoundedRectangleBorder(radius=14),
                color={"": "#FFFFFF"},
                elevation={"": 2, "hovered": 4},
            ),
        )

        def logout_click(e):
            storage.clear()
            mostrar_registro()

        form_grid = ft.ResponsiveRow(
            [
                tar,
                det,
                mon,
                cuo,
                res,
                mes,
            ],
            spacing=18,
            run_spacing=18,
        )

        main_container.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.icons.Icons.CREDIT_CARD, color="#FE7A5C", size=32),  # Coral card icon
                        ft.Text(
                            "Tarjetita 2.0",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="#FFFFFF"
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
                ft.Row(
                    [
                        ft.Text(f"Planilla: {email}", size=11, color="#8E8E93", expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.IconButton(
                            ft.icons.Icons.AUTO_AWESOME,
                            icon_color="#FED34A",
                            icon_size=16,
                            on_click=abrir_config_ia,
                            tooltip="Configurar Asistente IA",
                            padding=0
                        ),
                        ft.IconButton(
                            ft.icons.Icons.LOGOUT,
                            icon_color="#FF4C4C",
                            icon_size=16,
                            on_click=logout_click,
                            tooltip="Cambiar de cuenta/planilla",
                            padding=0
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(color="#2D2D2D", thickness=1, height=10),
                
                form_grid,
                
                ft.Container(height=10),
                
                ft.ElevatedButton(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.Icons.CLOUD_UPLOAD, color="#121212", size=24),
                            ft.Text(
                                "CARGAR GASTO",
                                weight=ft.FontWeight.BOLD,
                                size=15,
                                color="#121212"
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    on_click=click_cargar,
                    width=360,
                    height=50,
                    style=ft.ButtonStyle(
                        bgcolor={"": "#FE7A5C", "hovered": "#E0684C"},  # Coral button
                        shape=ft.RoundedRectangleBorder(radius=14),
                        color={"": "#121212"},
                        elevation={"": 2, "hovered": 4},
                    ),
                ),
                
                btn_consultar_ia,
                ai_container,
                
                st,
                
                ft.Divider(color="#2D2D2D", thickness=1, height=15),

                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("ÚLTIMOS 5 GASTOS", size=13, weight="bold", color="#FE7A5C"),  # Coral accent
                                ft.Text("Toca 🗑️ para eliminar", size=10, color="#8E8E93"),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.IconButton(
                            ft.icons.Icons.SYNC,
                            icon_color="#FE7A5C",
                            icon_size=20,
                            on_click=click_sync,
                            tooltip="Resincronizar Planilla"
                        ),
                        ft.IconButton(
                            ft.icons.Icons.REFRESH,
                            icon_color="#FE7A5C",
                            icon_size=20,
                            on_click=click_refresh,
                            tooltip="Actualizar lista"
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                recent_list
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        page.update()
        click_refresh(None)

    saved_email = storage.get("user_email")
    saved_ss_id = storage.get("spreadsheet_id")
    
    page.add(main_container)
    
    if saved_email and saved_ss_id:
        mostrar_app_principal(saved_email, saved_ss_id)
    else:
        mostrar_registro()


if __name__ == "__main__":
    ft.app(target=main)

