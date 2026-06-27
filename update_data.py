#!/usr/bin/env python3
"""
update_data.py -- Procesador de Excel para UCEN - Salas 2026
Corre en GitHub Actions (CI) o localmente.

ENTRADAS:
  planeacion_anual.xlsx  -- Hojas nombradas igual que las claves en dict b
                            (ej: 202601_res, 202601_det, 202602_fac, etc.)
  reservas.xlsx          -- Una hoja con reservas de salas -> clave "rev"

SALIDA:
  data_source.py         -- Reescrito con dict b actualizado.
                            Los mapeos estaticos se conservan intactos.
"""

import sys
import os
import base64
import io
import datetime
from zoneinfo import ZoneInfo
import importlib.util

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas no instalado. Ejecutar: pip install pandas openpyxl")
    sys.exit(1)

# ---- CONFIGURACION -----------------------------------------------------------

PLANEACION_FILE = "planeacion_anual.xlsx"
RESERVAS_FILE   = "reservas.xlsx"
RESERVAS_KEY    = "rev"
DATASOURCE_FILE = "data_source.py"

# Columnas que se fuerzan a int (comparacion case-insensitive)
INT_COLUMNS_LOWER = {
    "capacidad", "cupo", "cap", "capacidad_sala",
    "cap_sala", "cap_actual", "cap_sugerida",
}

# Detectar GitHub Actions u otro CI
IS_CI = os.environ.get("CI", "false").lower() == "true"


# ---- FUNCIONES DE DATOS ------------------------------------------------------

def force_int_columns(df):
    """Convierte a int todas las columnas de capacidad/cupo."""
    for col in df.columns:
        if col.lower() in INT_COLUMNS_LOWER:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def df_to_b64(df):
    """DataFrame -> CSV UTF-8 -> Base64 ASCII."""
    df = force_int_columns(df.copy())
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return base64.b64encode(csv_bytes).decode("ascii")


def b64_to_df(b64_str):
    """Base64 -> DataFrame (para verificacion de roundtrip)."""
    raw = base64.b64decode(b64_str)
    return pd.read_csv(io.StringIO(raw.decode("utf-8")))


# ---- FUNCIONES DE data_source.py ---------------------------------------------

def load_current_b(datasource_path):
    """Importa data_source.py y devuelve el dict b actual."""
    spec = importlib.util.spec_from_file_location("_ds_tmp", datasource_path)
    mod  = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        print("ERROR: No se pudo importar %s: %s" % (datasource_path, exc))
        sys.exit(1)
    if not hasattr(mod, "b"):
        print("ERROR: %s no contiene el dict b." % datasource_path)
        sys.exit(1)
    return dict(mod.b)


def read_static_header(datasource_path):
    """
    Lee data_source.py y devuelve todo el contenido hasta (sin incluir)
    la linea 'b = {'. Preserva intactos RANGO_ORDER, FAC_SHORT, etc.
    """
    with open(datasource_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    header = []
    for line in lines:
        if line.rstrip() == "b = {":
            break
        header.append(line)
    return "".join(header)


def build_b_block(b):
    """
    Construye el bloque 'b = { ... }' como string.
    - update_dt -> comillas simples (texto plano)
    - Resto     -> comillas dobles (Base64)
    - Orden: update_dt primero, luego claves alfabeticas
    """
    lines = ["b = {\n"]
    if "update_dt" in b:
        lines.append("    \"update_dt\": '%s',\n" % b["update_dt"])
    for key in sorted(k for k in b if k != "update_dt"):
        lines.append("    \"%s\": \"%s\",\n" % (key, b[key]))
    lines.append("}\n")
    return "".join(lines)


def write_datasource(datasource_path, header, b_block):
    """Escribe el nuevo data_source.py. Crea .bak solo si no estamos en CI."""
    if not IS_CI:
        backup = datasource_path + ".bak"
        with open(datasource_path, "rb") as f_in, open(backup, "wb") as f_out:
            f_out.write(f_in.read())
        print("   Backup local guardado: %s" % os.path.basename(backup))

    with open(datasource_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(b_block)


def verify_roundtrip(b, keys):
    """Verifica que cada clave actualizada decodifica correctamente."""
    errores = []
    for key in keys:
        try:
            df = b64_to_df(b[key])
            print("   OK '%s': %d filas x %d cols" % (key, len(df), len(df.columns)))
        except Exception as exc:
            print("   ERROR '%s': %s" % (key, exc))
            errores.append(key)
    return errores


# ---- PROCESADORES DE EXCEL ---------------------------------------------------

def procesar_planeacion(excel_path, b):
    """
    Lee planeacion_anual.xlsx.
    Cada hoja cuyo nombre coincide con una clave en b actualiza esa clave.
    """
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
            print("   ADVERTENCIA hoja '%s': error al leer - %s" % (hoja, exc))
            continue

        if df.empty:
            print("   ADVERTENCIA hoja '%s': vacia - conservando valor anterior." % hoja)
            continue

        b64 = df_to_b64(df)
        b[key] = b64
        keys_updated.append(key)
        print("   '%s': %d filas x %d cols -> %.1f KB Base64" % (
            key, len(df), len(df.columns), len(b64) / 1024))

    return keys_updated


def procesar_reservas(excel_path, b):
    """
    Lee reservas.xlsx. Usa la hoja llamada 'rev' si existe,
    sino la primera hoja. Mapea a la clave 'rev' en b.
    """
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

    if df.empty:
        print("   ADVERTENCIA: hoja de reservas vacia - conservando valor anterior.")
        return []

    b64 = df_to_b64(df)
    b[RESERVAS_KEY] = b64
    print("   '%s': %d filas x %d cols -> %.1f KB Base64" % (
        RESERVAS_KEY, len(df), len(df.columns), len(b64) / 1024))
    return [RESERVAS_KEY]


# ---- MAIN --------------------------------------------------------------------

def main():
    entorno = "GitHub Actions (CI)" if IS_CI else "local"
    _chile = ZoneInfo("America/Santiago")
    t_inicio = datetime.datetime.now(_chile)

    print("=" * 62)
    print("  UCEN - Actualizador de datos  [%s]" % entorno)
    print("  %s (hora Chile)" % t_inicio.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 62)

    # Verificar que data_source.py existe
    if not os.path.exists(DATASOURCE_FILE):
        print("\nERROR: No se encontro '%s'." % DATASOURCE_FILE)
        print("   Ejecuta este script desde la raiz del proyecto.")
        sys.exit(1)

    # Detectar que archivos Excel estan disponibles
    tiene_planeacion = os.path.exists(PLANEACION_FILE)
    tiene_reservas   = os.path.exists(RESERVAS_FILE)

    if not tiene_planeacion and not tiene_reservas:
        print("\n⚠️ No se detectaron archivos Excel para procesar. Saltando compilacion de Base64.")
        print("   Esperados en la raiz del repositorio:")
        print("     - %s" % PLANEACION_FILE)
        print("     - %s" % RESERVAS_FILE)
        print("\n   Sube al menos uno de estos archivos a GitHub para activar el pipeline.")
        sys.exit(0)  # EXIT CODE 0 — no es un error, solo no hay nada que hacer

    print("\nArchivos detectados:")
    print("   %s %s" % ("OK" if tiene_planeacion else "AUSENTE", PLANEACION_FILE))
    print("   %s %s" % ("OK" if tiene_reservas else "AUSENTE", RESERVAS_FILE))

    # Cargar el dict b actual
    print("\nCargando estado actual de %s..." % DATASOURCE_FILE)
    b = load_current_b(DATASOURCE_FILE)
    print("   Claves existentes: %d" % len(b))

    # Leer el header estatico
    header_estatico = read_static_header(DATASOURCE_FILE)

    # Procesar los Excel disponibles
    all_updated = []

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

    # Actualizar timestamp
    now_str = datetime.datetime.now(ZoneInfo("America/Santiago")).strftime("%d/%m/%Y %H:%M")
    b["update_dt"] = now_str
    print("\nupdate_dt -> %s (hora Chile)" % now_str)

    # Verificar roundtrip antes de escribir
    print("\nVerificando integridad de %d claves..." % len(all_updated))
    errores = verify_roundtrip(b, all_updated)

    if errores:
        print("\nERROR: %d clave(s) fallaron la verificacion:" % len(errores))
        for k in errores:
            print("   - %s" % k)
        print("\n   data_source.py NO fue modificado.")
        sys.exit(1)

    print("   Todas las claves pasaron la verificacion.")

    # Construir y escribir el nuevo data_source.py
    print("\nEscribiendo %s..." % DATASOURCE_FILE)
    b_block = build_b_block(b)
    write_datasource(DATASOURCE_FILE, header_estatico, b_block)

    # Resumen final
    duracion = (datetime.datetime.utcnow() - t_inicio).seconds
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
