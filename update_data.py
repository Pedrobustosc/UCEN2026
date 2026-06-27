#!/usr/bin/env python3
"""
update_data.py -- Procesador de Excel para UCEN - Salas 2026
Versión producción con arquitectura de backend robusta.

ARQUITECTURA:
  ┌─────────────────────────────────────────────┐
  │  EXCEPCIONES TIPADAS                        │
  │  DataError     — datos inválidos/corruptos  │
  │  PipelineError — error de escritura/IO      │
  ├─────────────────────────────────────────────┤
  │  VALIDACIÓN DE ESQUEMA                      │
  │  Cada hoja se valida antes de codificar.    │
  │  Hojas vacías o sin columnas → advertencia. │
  ├─────────────────────────────────────────────┤
  │  ESCRITURA ATÓMICA                          │
  │  .tmp + os.replace() — nunca estado parcial │
  └─────────────────────────────────────────────┘

ENTRADAS:
  planeacion_anual.xlsx  — Hojas nombradas como claves en dict b
  reservas.xlsx          — Hoja "rev" (o primera hoja)

SALIDA:
  data_source.py         — Reescrito con dict b actualizado.
                           Mapeos estáticos preservados intactos.
"""

import sys
import os
import base64
import io
import datetime
import warnings
from zoneinfo import ZoneInfo

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style",
    category=UserWarning,
    module="openpyxl",
)

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas no instalado. Ejecutar: pip install pandas openpyxl")
    sys.exit(1)

import importlib.util

# ── CONFIGURACION ─────────────────────────────────────────────────────────────

PLANEACION_FILE = "planeacion_anual.xlsx"
RESERVAS_FILE   = "reservas.xlsx"
RESERVAS_KEY    = "rev"
DATASOURCE_FILE = "data_source.py"

_CHILE = ZoneInfo("America/Santiago")
IS_CI  = os.environ.get("CI", "false").lower() == "true"

INT_COLUMNS_LOWER = {
    "capacidad", "cupo", "cap", "capacidad_sala",
    "cap_sala", "cap_actual", "cap_sugerida",
}

# Mínimo de columnas que debe tener un DataFrame para considerarse válido
MIN_COLUMNS = 1
MIN_ROWS    = 1


# ── EXCEPCIONES TIPADAS ───────────────────────────────────────────────────────

class DataError(Exception):
    """Dato de entrada inválido, corrupto o que no cumple el contrato de esquema."""

class PipelineError(Exception):
    """Error de infraestructura: lectura de archivo, escritura o importación."""


# ── CAPA DE TRANSFORMACIÓN DE DATOS ──────────────────────────────────────────

def force_int_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Fuerza a int las columnas de capacidad/cupo (comparación case-insensitive)."""
    for col in df.columns:
        if col.lower() in INT_COLUMNS_LOWER:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def strip_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina espacios fantasma en todas las columnas object.
    Previene mismatch de claves por padding del Excel."""
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    return df


def validate_dataframe(df: pd.DataFrame, key: str) -> None:
    """Valida que el DataFrame cumpla el contrato mínimo de esquema.
    Lanza DataError si no pasa la validación."""
    if df.shape[0] < MIN_ROWS:
        raise DataError(f"'{key}': DataFrame sin filas de datos (solo encabezado o vacío).")
    if df.shape[1] < MIN_COLUMNS:
        raise DataError(f"'{key}': DataFrame sin columnas.")
    # Detectar DataFrames que son puramente NaN (Excel con celdas vacías)
    if df.dropna(how="all").empty:
        raise DataError(f"'{key}': DataFrame con todas las celdas vacías.")


def df_to_b64(df: pd.DataFrame) -> str:
    """DataFrame → CSV UTF-8 → Base64 ASCII.
    Aplica strip de strings y fuerza tipos int antes de codificar."""
    df = df.copy()
    df = strip_string_columns(df)
    df = force_int_columns(df)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return base64.b64encode(csv_bytes).decode("ascii")


def b64_to_df(b64_str: str) -> pd.DataFrame:
    """Base64 → DataFrame. low_memory=False suprime DtypeWarning por tipos mixtos."""
    raw = base64.b64decode(b64_str)
    return pd.read_csv(io.StringIO(raw.decode("utf-8")), low_memory=False)


# ── CAPA DE ACCESO A data_source.py ──────────────────────────────────────────

def load_current_b(datasource_path: str) -> dict:
    """Importa data_source.py y devuelve el dict b actual.
    Lanza PipelineError si el archivo no puede importarse."""
    spec = importlib.util.spec_from_file_location("_ds_tmp", datasource_path)
    mod  = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        raise PipelineError(f"No se pudo importar {datasource_path}: {exc}") from exc
    if not hasattr(mod, "b"):
        raise PipelineError(f"{datasource_path} no contiene el dict b.")
    return dict(mod.b)


def read_static_header(datasource_path: str) -> str:
    """Lee data_source.py y devuelve todo hasta (sin incluir) la línea 'b = {'.
    Preserva intactos RANGO_ORDER, FAC_SHORT, ED_SHORT, etc."""
    with open(datasource_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    header = []
    for line in lines:
        if line.rstrip() == "b = {":
            break
        header.append(line)
    return "".join(header)


def build_b_block(b: dict) -> str:
    """Construye el bloque 'b = { ... }' como string.
    update_dt en comillas simples (texto plano). Resto en comillas dobles (Base64).
    Orden: update_dt primero, luego claves alfabéticas."""
    lines = ["b = {\n"]
    if "update_dt" in b:
        lines.append("    \"update_dt\": '%s',\n" % b["update_dt"])
    for key in sorted(k for k in b if k != "update_dt"):
        lines.append("    \"%s\": \"%s\",\n" % (key, b[key]))
    lines.append("}\n")
    return "".join(lines)


def write_datasource_atomic(datasource_path: str, header: str, b_block: str) -> None:
    """Escritura atómica de data_source.py:
      1. Escribe contenido completo en .tmp
      2. os.replace() mueve el .tmp sobre el destino (operación atómica en Linux/Mac/Win)
    Si el proceso muere a mitad, el archivo original queda intacto.
    En modo local también guarda .bak del estado anterior."""
    tmp_path = datasource_path + ".tmp"
    content  = header + b_block

    if not IS_CI:
        backup = datasource_path + ".bak"
        with open(datasource_path, "rb") as f_in, open(backup, "wb") as f_out:
            f_out.write(f_in.read())
        print("   Backup guardado: %s" % os.path.basename(backup))

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, datasource_path)
    except OSError as exc:
        # Limpiar .tmp si queda huérfano
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise PipelineError(f"Error escribiendo {datasource_path}: {exc}") from exc


def verify_roundtrip(b: dict, keys: list) -> list:
    """Verifica que cada clave actualizada decodifica correctamente.
    Devuelve lista de claves que fallaron."""
    errores = []
    for key in keys:
        try:
            df = b64_to_df(b[key])
            validate_dataframe(df, key)
            print("   OK '%s': %d filas x %d cols" % (key, len(df), len(df.columns)))
        except (DataError, Exception) as exc:
            print("   ERROR '%s': %s" % (key, exc))
            errores.append(key)
    return errores


# ── PROCESADORES DE EXCEL ─────────────────────────────────────────────────────

def procesar_planeacion(excel_path: str, b: dict) -> list:
    """Lee planeacion_anual.xlsx. Cada hoja cuyo nombre (strip) coincide
    con una clave del dict b la actualiza con validación de esquema."""
    print("\nProcesando %s..." % excel_path)
    try:
        xl = pd.ExcelFile(excel_path)
    except Exception as exc:
        print("   ERROR al abrir: %s" % exc)
        return []

    hojas = xl.sheet_names
    print("   Hojas encontradas (%d): %s" % (len(hojas), ", ".join(hojas)))

    keys_updated = []
    for hoja in hojas:
        key = hoja.strip()
        try:
            df = xl.parse(hoja)
        except Exception as exc:
            print("   ADVERTENCIA '%s': error al leer — %s" % (hoja, exc))
            continue

        try:
            validate_dataframe(df, key)
        except DataError as exc:
            print("   ADVERTENCIA '%s': %s — conservando valor anterior." % (hoja, exc))
            continue

        b64 = df_to_b64(df)
        b[key] = b64
        keys_updated.append(key)
        print("   '%s': %d filas x %d cols → %.1f KB Base64" % (
            key, len(df), len(df.columns), len(b64) / 1024))

    return keys_updated


def procesar_reservas(excel_path: str, b: dict) -> list:
    """Lee reservas.xlsx. Usa la hoja 'rev' si existe, sino la primera.
    Valida esquema antes de codificar."""
    print("\nProcesando %s..." % excel_path)
    try:
        xl = pd.ExcelFile(excel_path)
    except Exception as exc:
        print("   ERROR al abrir: %s" % exc)
        return []

    if RESERVAS_KEY in xl.sheet_names:
        hoja_objetivo = RESERVAS_KEY
    else:
        hoja_objetivo = xl.sheet_names[0]
        print("   INFO: hoja '%s' mapeada a clave '%s'" % (hoja_objetivo, RESERVAS_KEY))

    try:
        df = xl.parse(hoja_objetivo)
    except Exception as exc:
        print("   ERROR al leer hoja '%s': %s" % (hoja_objetivo, exc))
        return []

    try:
        validate_dataframe(df, RESERVAS_KEY)
    except DataError as exc:
        print("   ADVERTENCIA reservas: %s — conservando valor anterior." % exc)
        return []

    b64 = df_to_b64(df)
    b[RESERVAS_KEY] = b64
    print("   '%s': %d filas x %d cols → %.1f KB Base64" % (
        RESERVAS_KEY, len(df), len(df.columns), len(b64) / 1024))
    return [RESERVAS_KEY]


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main() -> None:
    entorno  = "GitHub Actions (CI)" if IS_CI else "local"
    t_inicio = datetime.datetime.now(_CHILE)

    print("=" * 62)
    print("  UCEN - Actualizador de datos  [%s]" % entorno)
    print("  %s (hora Chile)" % t_inicio.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 62)

    # Verificar que data_source.py existe
    if not os.path.exists(DATASOURCE_FILE):
        print("\nERROR: No se encontro '%s'." % DATASOURCE_FILE)
        print("   Ejecuta este script desde la raiz del proyecto.")
        sys.exit(1)

    # Detectar archivos Excel disponibles
    tiene_planeacion = os.path.exists(PLANEACION_FILE)
    tiene_reservas   = os.path.exists(RESERVAS_FILE)

    if not tiene_planeacion and not tiene_reservas:
        print("\nWARNING: No se detectaron archivos Excel para procesar.")
        print("   Esperados:")
        print("     - %s" % PLANEACION_FILE)
        print("     - %s" % RESERVAS_FILE)
        sys.exit(0)   # exit 0 — no es error, solo nada que hacer

    print("\nArchivos detectados:")
    print("   %s %s" % ("OK     " if tiene_planeacion else "AUSENTE", PLANEACION_FILE))
    print("   %s %s" % ("OK     " if tiene_reservas   else "AUSENTE", RESERVAS_FILE))

    # Cargar estado actual
    print("\nCargando estado actual de %s..." % DATASOURCE_FILE)
    try:
        b = load_current_b(DATASOURCE_FILE)
    except PipelineError as exc:
        print("\nERROR CRITICO: %s" % exc)
        sys.exit(1)
    print("   Claves existentes: %d" % len(b))

    header_estatico = read_static_header(DATASOURCE_FILE)
    all_updated: list = []

    # Procesar Excel disponibles
    if tiene_planeacion:
        keys = procesar_planeacion(PLANEACION_FILE, b)
        all_updated.extend(keys)

    if tiene_reservas:
        keys = procesar_reservas(RESERVAS_FILE, b)
        all_updated.extend(keys)

    if not all_updated:
        print("\nADVERTENCIA: Ninguna clave fue actualizada.")
        print("   data_source.py NO fue modificado.")
        sys.exit(0)

    # Timestamp en hora Chile
    now_str = datetime.datetime.now(_CHILE).strftime("%d/%m/%Y %H:%M")
    b["update_dt"] = now_str
    print("\nupdate_dt → %s (hora Chile)" % now_str)

    # Verificar roundtrip con validación de esquema
    print("\nVerificando integridad de %d claves..." % len(all_updated))
    errores = verify_roundtrip(b, all_updated)

    if errores:
        print("\nERROR: %d clave(s) fallaron la verificacion:" % len(errores))
        for k in errores:
            print("   - %s" % k)
        print("\n   data_source.py NO fue modificado.")
        sys.exit(1)

    print("   Todas las claves pasaron la verificacion.")

    # Escritura atómica
    print("\nEscribiendo %s (escritura atomica)..." % DATASOURCE_FILE)
    try:
        b_block = build_b_block(b)
        write_datasource_atomic(DATASOURCE_FILE, header_estatico, b_block)
    except PipelineError as exc:
        print("\nERROR CRITICO al escribir: %s" % exc)
        sys.exit(1)

    # Resumen final
    duracion = (datetime.datetime.now(_CHILE) - t_inicio).seconds
    print("\n" + "=" * 62)
    print("  COMPLETADO en %ds" % duracion)
    print("  Claves actualizadas (%d):" % len(all_updated))
    for k in all_updated:
        print("    - %s" % k)
    print("=" * 62)

    if not IS_CI:
        print("\nProximos pasos (local):")
        print("    git add data_source.py")
        print("    git commit -m \"data: actualizacion %s\"" % now_str)
        print("    git push\n")
    else:
        print("\n  GitHub Actions hara el commit y push automaticamente.\n")


if __name__ == "__main__":
    main()
