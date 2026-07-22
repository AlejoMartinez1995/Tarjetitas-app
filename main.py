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
            if "TOTAL" in row_str:
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
                formula = "$ 0.00"
            batch_values.append({"range": f"{letra}{fila_t}", "values": [[formula]]})

    # Escribir fórmula SUM para la fila final de total general
    fila_general = filas_total[-1]
    fila_totales_inicio = filas_total[0]
    fila_totales_fin = filas_total[-2] if len(filas_total) > 1 else filas_total[0]

    for col_idx in range(10, 22):
        letra = chr(64 + col_idx)
        # =SUM(letra_totales_inicio:letra_totales_fin)
        formula = f"=SUM({letra}{fila_totales_inicio}:{letra}{fila_totales_fin})"
        batch_values.append({"range": f"{letra}{fila_general}", "values": [[formula]]})

    if batch_values:
        sheet.batch_update(batch_values, value_input_option="USER_ENTERED")


# --- Helper para analizar monto numérico ---
def parse_monto(monto_str):
    monto_str = str(monto_str).replace("$", "").strip()
    if not monto_str:
        return 0.0
    
    # Caso: tiene comas y puntos (ej: 1.500,50)
    if "," in monto_str and "." in monto_str:
        monto_str = monto_str.replace(".", "").replace(",", ".")
    # Caso: tiene solo comas (ej: 1500,50)
    elif "," in monto_str:
        monto_str = monto_str.replace(",", ".")
    # Caso: tiene solo un punto (ej: 1.500 o 1500.50)
    elif "." in monto_str:
        partes = monto_str.split(".")
        # Si la última parte tiene exactamente 3 dígitos, es un separador de miles (ej: 1.500)
        if len(partes[-1]) == 3:
            monto_str = monto_str.replace(".", "")
        else:
            # Si tiene 1 o 2 dígitos es un decimal (ej: 1500.5 o 1500.50)
            pass
            
    return float(monto_str)


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
                row_str = " ".join(row).upper()
                if "TOTAL" in row_str:
                    continue  # Mantener filas de totales
                # Si la fila tiene algún dato, la borramos
                if any(cell.strip() for cell in row):
                    rows_to_delete.append(row_num)
            
            # Borrar de abajo hacia arriba para no alterar índices
            for row_num in reversed(rows_to_delete):
                sheet.delete_rows(row_num)
        except Exception as e:
            print(f"Error al limpiar la hoja {sheet.title}: {str(e)}")


def eliminar_gasto(spreadsheet_id, tarjeta, fecha, detalle, monto, responsable):
    client = obtener_cliente()
    ss = client.open_by_key(spreadsheet_id)
    
    try:
        año_actual = datetime.strptime(fecha, "%d/%m/%Y").year
    except Exception:
        año_actual = datetime.now().year
        
    monto_val = float(monto)
    
    for año in range(año_actual, año_actual + 6):
        try:
            sheet = ss.worksheet(f"Gastos {año}")
        except Exception:
            continue
            
        data = sheet.get_all_values()
        fila_a_borrar = None
        
        for idx, row in enumerate(data):
            if idx < 3:
                continue
            if len(row) < 9:
                continue
                
            try:
                row_monto = float(row[6].replace("$", "").replace(".", "").replace(",", ".").strip()) if row[6] else 0.0
            except:
                row_monto = 0.0
                
            row_detalle = row[1].strip()
            row_responsable = row[3].strip()
            row_fecha = row[0].strip()
            
            if año == año_actual:
                if row_fecha == fecha and row_responsable.upper() == responsable.upper() and abs(row_monto - monto_val) < 0.01 and detalle.upper() in row_detalle.upper():
                    fila_a_borrar = idx + 1
                    break
            else:
                if row_responsable.upper() == responsable.upper() and abs(row_monto - monto_val) < 0.01 and detalle.upper() in row_detalle.upper() and "(CONT.)" in row_detalle.upper():
                    fila_a_borrar = idx + 1
                    break
                    
        if fila_a_borrar:
            sheet.delete_rows(fila_a_borrar)
            formatear_y_totalizar(sheet, tarjeta)

def obtener_ultimos_gastos(spreadsheet_id):
    client = obtener_cliente()
    ss = client.open_by_key(spreadsheet_id)
    año_actual = datetime.now().year
    
    try:
        sheet = ss.worksheet(f"Gastos {año_actual}")
    except Exception:
        for s in ss.worksheets():
            if s.title.startswith("Gastos "):
                sheet = s
                break
        else:
            return []
            
    data = sheet.get_all_values()
    gastos = []
    
    for idx in reversed(range(len(data))):
        if idx < 3:
            continue
        row = data[idx]
        if len(row) < 9:
            continue
            
        fecha = row[0].strip()
        detalle = row[1].strip()
        responsable = row[3].strip()
        monto_str = row[6].strip()
        cuotas_str = row[7].strip()
        
        if not (fecha and "/" in fecha):
            continue
            
        row_str = " ".join(row).upper()
        if "TOTAL" in row_str:
            continue
            
        if not (detalle and monto_str):
            continue
            
        try:
            monto = float(monto_str.replace("$", "").replace(".", "").replace(",", ".").strip())
        except:
            monto = 0.0
            
        tarjeta = "VISA"
        for i in reversed(range(idx)):
            row_prev_str = " ".join(data[i]).upper()
            if "VISA" in row_prev_str and "TOTAL" not in row_prev_str:
                tarjeta = "VISA"
                break
            elif "MASTERCARD" in row_prev_str and "TOTAL" not in row_prev_str:
                tarjeta = "MASTERCARD"
                break
                
        gastos.append({
            "fecha": fecha,
            "detalle": detalle,
            "responsable": responsable,
            "monto": monto,
            "cuotas": cuotas_str,
            "tarjeta": tarjeta
        })
        
        if len(gastos) >= 5:
            break
            
    return gastos

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



def reestructurar_hoja_completa(sheet, año, nuevo_gasto=None, tarjeta_nuevo=None):
    """
    Lee la hoja completa de gastos, separa los gastos de los totales para VISA y MASTERCARD,
    e inserta en memoria el nuevo gasto si viene especificado.
    Reconstruye el diseño agrupado limpio:
      - Gastos arriba.
      - Totales de responsables abajo con SUMIF.
      - Total general al final con SUM.
    Escribe todo en una sola llamada de actualización y aplica formatos.
    """
    data = sheet.get_all_values()
    if len(data) < 3:
        # Inicializar estructura mínima si la hoja está totalmente vacía
        resp_inicial = nuevo_gasto[3] if nuevo_gasto else "ALEJO"
        # inicializar_estructura ya crea la estructura limpia base
        return

    titulo_hoja = data[0]
    cabeceras = data[1]

    idx_visa = None
    idx_master = None

    for i, row in enumerate(data):
        if not row:
            continue
        first_cell = row[0].strip().upper()
        if first_cell == "VISA":
            idx_visa = i
        elif first_cell == "MASTERCARD":
            idx_master = i

    # Si por alguna razón la hoja existía pero no tiene VISA o MASTERCARD,
    # la reinicializamos limpia para evitar fallos.
    if idx_visa is None or idx_master is None:
        return

    filas_visa_raw = data[idx_visa + 1 : idx_master]
    filas_master_raw = data[idx_master + 1 :]

    def clasificar_bloque(filas_raw, tarjeta):
        gastos = []
        responsables_set = set()
        nombres_bonitos = {}

        for row in filas_raw:
            if not any(c.strip() for c in row):
                continue
            row_str = " ".join(row).upper()
            if "TOTAL" in row_str:
                # Recopilar responsables de los totales anteriores para no perder nombres
                parts = row[0].split()
                for p in parts:
                    p_upper = p.upper()
                    if p_upper not in ["TOTAL", tarjeta.upper()]:
                        norm = normalizar_nombre(p_upper)
                        responsables_set.add(norm)
                        nombres_bonitos[norm] = p.strip().title()
                continue

            fecha = row[0].strip()
            detalle = row[1].strip()
            responsable = row[3].strip() if len(row) > 3 else ""

            if fecha or detalle:
                gasto_row = list(row) + [""] * (21 - len(row))
                
                # --- LIMPIAR MONTOS Y TIPOS DE DATOS ---
                # Evita que se escriban strings formateados como '$ 50.000,00' en las celdas,
                # lo que rompe las sumas y totales. Escribimos números limpios.
                try:
                    gasto_row[6] = parse_monto(gasto_row[6]) if gasto_row[6] else 0.0
                except Exception:
                    gasto_row[6] = 0.0
                
                try:
                    gasto_row[7] = int(str(gasto_row[7]).replace(".0", "").strip()) if gasto_row[7] else 1
                except Exception:
                    gasto_row[7] = 1

                try:
                    gasto_row[8] = parse_monto(gasto_row[8]) if gasto_row[8] else 0.0
                except Exception:
                    gasto_row[8] = 0.0

                gastos.append(gasto_row)
                if responsable:
                    norm = normalizar_nombre(responsable)
                    responsables_set.add(norm)
                    nombres_bonitos[norm] = responsable.strip().title()

        return gastos, responsables_set, nombres_bonitos

    gastos_visa, resp_visa, bonitos_visa = clasificar_bloque(filas_visa_raw, "VISA")
    gastos_master, resp_master, bonitos_master = clasificar_bloque(filas_master_raw, "MASTERCARD")

    # Si hay un nuevo gasto a insertar
    if nuevo_gasto is not None and tarjeta_nuevo is not None:
        gasto_cleaned = list(nuevo_gasto) + [""] * (21 - len(nuevo_gasto))
        gasto_cleaned[6] = parse_monto(gasto_cleaned[6])
        gasto_cleaned[7] = int(str(gasto_cleaned[7]).replace(".0", "").strip())
        gasto_cleaned[8] = parse_monto(gasto_cleaned[8])

        if tarjeta_nuevo.upper() == "VISA":
            gastos_visa.append(gasto_cleaned)
            norm = normalizar_nombre(nuevo_gasto[3])
            resp_visa.add(norm)
            bonitos_visa[norm] = nuevo_gasto[3].strip().title()
        else:
            gastos_master.append(gasto_cleaned)
            norm = normalizar_nombre(nuevo_gasto[3])
            resp_master.add(norm)
            bonitos_master[norm] = nuevo_gasto[3].strip().title()

    # Re-asegurar que haya al menos un responsable
    if not resp_visa:
        resp_visa.add("alejo")
        bonitos_visa["alejo"] = "Alejo"
    if not resp_master:
        resp_master.add("alejo")
        bonitos_master["alejo"] = "Alejo"

    # Construir las nuevas filas del documento
    nuevas_filas = []
    nuevas_filas.append(titulo_hoja + [""] * (21 - len(titulo_hoja)))
    nuevas_filas.append(cabeceras + [""] * (21 - len(cabeceras)))

    # --- Reconstruir VISA ---
    nuevas_filas.append(["VISA"] + [""] * 20)
    for g in gastos_visa:
        fila_idx_nueva = len(nuevas_filas) + 1
        # Convertir cuotas mensuales a referencias a la columna I de la fila actual
        for m_idx in range(9, 21):
            val_m = str(g[m_idx]).strip()
            if val_m and val_m not in ["0", "0.0", "0.00", "$ 0.00", "$ 0,00"]:
                g[m_idx] = f"=$I{fila_idx_nueva}"
            else:
                g[m_idx] = ""
        nuevas_filas.append(g)

    for r in sorted(list(resp_visa)):
        nombre = bonitos_visa[r]
        nuevas_filas.append(["", "", "", f"TOTAL {nombre.upper()}"] + [""] * 17)
    nuevas_filas.append(["", "", "", "TOTAL VISA"] + [""] * 17)

    # Separador
    nuevas_filas.append([""] * 21)

    # --- Reconstruir MASTERCARD ---
    nuevas_filas.append(["MASTERCARD"] + [""] * 20)
    for g in gastos_master:
        fila_idx_nueva = len(nuevas_filas) + 1
        for m_idx in range(9, 21):
            val_m = str(g[m_idx]).strip()
            if val_m and val_m not in ["0", "0.0", "0.00", "$ 0.00", "$ 0,00"]:
                g[m_idx] = f"=$I{fila_idx_nueva}"
            else:
                g[m_idx] = ""
        nuevas_filas.append(g)

    for r in sorted(list(resp_master)):
        nombre = bonitos_master[r]
        nuevas_filas.append(["", "", "", f"TOTAL {nombre.upper()}"] + [""] * 17)
    nuevas_filas.append(["", "", "", "TOTAL MASTERCARD"] + [""] * 17)

    # Limpiar formato de bordes y colores desde la fila 3 (index 2) hacia abajo para evitar restos visuales
    try:
        sheet.spreadsheet.batch_update({
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet.id,
                            "startRowIndex": 2,  # desde fila 3
                            "endRowIndex": 200,  # rango amplio
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
            ]
        })
    except Exception:
        pass

    # Escribir la hoja completa de forma instantánea
    sheet.clear()
    sheet.update(range_name="A1", values=nuevas_filas, value_input_option="USER_ENTERED")


def cargar_gasto(spreadsheet_id, detalle, monto, cuotas, responsable, mes_inicio, tarjeta):
    client = obtener_cliente()
    ss = client.open_by_key(spreadsheet_id)
    año_actual = datetime.now().year
    monto_f = parse_monto(monto)
    cant_c = int(cuotas)
    val_c = monto_f / cant_c
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    idx_m = meses.index(mes_inicio)

    def procesar_hoja(año, cuotas_restantes, start_idx):
        # Crear/inicializar la hoja si no existe
        try:
            sheet = ss.worksheet(f"Gastos {año}")
        except Exception:
            sheet = inicializar_estructura(ss, año, responsable)
        else:
            # Asegurar que tenga estructura mínima
            data_check = sheet.get_all_values()
            tiene_estructura = any(
                "VISA" in " ".join(r).upper() or "MASTERCARD" in " ".join(r).upper()
                for r in data_check
            )
            if not tiene_estructura:
                sheet = inicializar_estructura(ss, año, responsable)

        # Generar los datos del nuevo gasto temporal (sin fórmulas de fila dura aún)
        det_final = (
            detalle.strip().title()
            if año == año_actual
            else f"{detalle.strip().title()} (Cont.)"
        )
        # Fila: Fecha, Detalle, Vacío, Responsable, Vacío, ID-Mes, Total, Cuotas, Valor Cuota
        gasto_fila = [
            datetime.now().strftime("%d/%m/%Y"),
            det_final,
            "",
            responsable.strip().title(),
            "",
            f"{str(año)[2:]}-{meses[start_idx][:3].lower()}",
            monto_f,
            cant_c,
            val_c,
        ]

        # Rellenar los 12 meses (indicador temporal '=')
        for i in range(12):
            if i >= start_idx and cuotas_restantes > 0:
                gasto_fila.append("=")  # Marcador que reestructurar_hoja_completa reemplazará con f'=$I{fila}'
                cuotas_restantes -= 1
            else:
                gasto_fila.append("")

        # Insertar y reestructurar la hoja entera en memoria + formatear
        reestructurar_hoja_completa(sheet, año, nuevo_gasto=gasto_fila, tarjeta_nuevo=tarjeta)
        formatear_y_totalizar(sheet, "VISA")
        formatear_y_totalizar(sheet, "MASTERCARD")

        return cuotas_restantes

    quedan = procesar_hoja(año_actual, cant_c, idx_m)
    año_iter = año_actual
    while quedan > 0:
        año_iter += 1
        if año_iter > año_actual + 5:
            break
        quedan = procesar_hoja(año_iter, quedan, 0)
# --- 5. INTERFAZ FLET ---
class LocalStorage:
    def __init__(self):
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
    if hasattr(page, "client_storage") and page.client_storage is not None:
        storage = page.client_storage
    else:
        storage = LocalStorage()

    page.title = "Tarjetita 2.0"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0B0C10"  # Midnight dark background
    page.window_width = 450
    page.window_height = 800
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    input_style = {
        "border_color": "#45A29E",
        "focused_border_color": "#66FCF1",
        "label_style": ft.TextStyle(color="#C5C6C7"),
        "text_style": ft.TextStyle(color="#FFFFFF"),
        "border_radius": 10,
    }

    def es_correo_valido(email):
        import re
        patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(patron, email))

    main_container = ft.Container(
        bgcolor="#1F2833",
        border_radius=20,
        padding=25,
        width=400,
        border=ft.Border.all(1, "#45A29E"),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=20,
            color="#99000000",
            offset=ft.Offset(0, 10),
        ),
        margin=ft.Margin.only(top=10, bottom=10)
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
                
                # Limpiar cualquier gasto demo del maestro para empezar de cero
                limpiar_planilla(ss)
                
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
                        ft.Icon(ft.icons.Icons.CREDIT_CARD, color="#66FCF1", size=36),
                        ft.Text(
                            "Tarjetita 2.0",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                            color="#66FCF1"
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
                ft.Divider(color="#45A29E", thickness=1, height=10),

                # ── Instrucciones sin botones ──────────────────────────────
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Cómo conectar tu planilla:", size=13, weight="bold", color="#FFFFFF"),
                            ft.Text(
                                "1. Abrí Google Drive en tu navegador y creá una planilla nueva (o usá la que ya tenés).",
                                size=12, color="#C5C6C7"
                            ),
                            ft.Text(
                                "2. En esa planilla, tocá Compartir e ingresá este correo con permiso de Editor:",
                                size=12, color="#C5C6C7"
                            ),
                            ft.Container(
                                content=ft.Text(
                                    "creds-json@targetita-app.iam.gserviceaccount.com",
                                    size=11,
                                    color="#66FCF1",
                                    selectable=True,
                                    text_align="center",
                                ),
                                bgcolor="#0B0C10",
                                padding=8,
                                border_radius=6,
                            ),
                            ft.Text(
                                "3. Copiá el enlace de tu planilla (Compartir → Copiar enlace) y pegalo acá abajo junto con tu correo de Google.",
                                size=12, color="#C5C6C7"
                            ),
                        ],
                        spacing=8,
                    ),
                    bgcolor="#151B24",
                    padding=14,
                    border_radius=10,
                    border=ft.Border.all(0.5, "#45A29E"),
                ),

                email_input,
                link_input,
                
                ft.ElevatedButton(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.Icons.LINK, color="#0B0C10", size=18),
                            ft.Text("VINCULAR PLANILLA", weight=ft.FontWeight.BOLD, color="#0B0C10", size=13),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    on_click=registrar_click,
                    width=320,
                    height=45,
                    style=ft.ButtonStyle(
                        bgcolor={"": "#66FCF1", "hovered": "#45A29E"},
                        shape=ft.RoundedRectangleBorder(radius=10),
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
            prefix=ft.Text("$ ", style=ft.TextStyle(color="#66FCF1")),
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
                    for g in gastos:
                        def make_delete_handler(gasto=g):
                            def handle_delete(e):
                                st.value = f"🗑️ Eliminando '{gasto['detalle']}'..."
                                st.color = "#FF4C4C"
                                page.update()
                                try:
                                    eliminar_gasto(
                                        ss_id,
                                        gasto["tarjeta"],
                                        gasto["fecha"],
                                        gasto["detalle"],
                                        gasto["monto"],
                                        gasto["responsable"]
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
                                                ft.Text(f"{g['detalle']} - $ {g['monto']:.2f}", weight="bold", color="#FFFFFF", size=13),
                                                ft.Text(f"{g['fecha']} | {g['tarjeta']} | {g['responsable']} | {g['cuotas']} c.", color="#C5C6C7", size=10),
                                            ],
                                            spacing=2,
                                            expand=True
                                        ),
                                        ft.IconButton(
                                            ft.icons.Icons.DELETE,
                                            icon_color="#FF4C4C",
                                            icon_size=18,
                                            on_click=make_delete_handler(g),
                                            tooltip="Eliminar este gasto"
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                bgcolor="#151B24",
                                padding=10,
                                border_radius=8,
                                border=ft.Border.all(0.5, "#45A29E")
                            )
                        )
                page.update()
            except Exception as ex:
                recent_list.controls = [
                    ft.Text(f"Error al cargar gastos: {str(ex)}", color="#FF4C4C", size=12, text_align="center")
                ]
                page.update()

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
                        ft.Icon(ft.icons.Icons.CREDIT_CARD, color="#66FCF1", size=32),
                        ft.Text(
                            "Tarjetita 2.0",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="#66FCF1"
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
                ft.Row(
                    [
                        ft.Text(f"Planilla: {email}", size=11, color="#45A29E", expand=True, overflow=ft.TextOverflow.ELLIPSIS),
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
                ft.Divider(color="#45A29E", thickness=1, height=10),
                
                form_grid,
                
                ft.Container(height=10),
                
                ft.ElevatedButton(
                    content=ft.Row(
                        [
                            ft.Icon(ft.icons.Icons.CLOUD_UPLOAD, color="#0B0C10", size=24),
                            ft.Text(
                                "CARGAR GASTO",
                                weight=ft.FontWeight.BOLD,
                                size=15,
                                color="#0B0C10"
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    on_click=click_cargar,
                    width=360,
                    height=50,
                    style=ft.ButtonStyle(
                        bgcolor={"": "#66FCF1", "hovered": "#45A29E"},
                        shape=ft.RoundedRectangleBorder(radius=10),
                        elevation={"": 4, "hovered": 8},
                    ),
                ),
                
                st,
                
                ft.Divider(color="#45A29E", thickness=1, height=15),

                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("ÚLTIMOS 5 GASTOS", size=13, weight="bold", color="#66FCF1"),
                                ft.Text("Toca 🗑️ para eliminar", size=10, color="#45A29E"),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.IconButton(
                            ft.icons.Icons.REFRESH,
                            icon_color="#66FCF1",
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

