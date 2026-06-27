# 🏫 Disponibilidad de Salas · UCEN 2026

> Panel web de ocupación y disponibilidad de salas para la Universidad Central de Chile.  
> Los datos se actualizan subiendo un Excel a GitHub — sin instalar nada, sin línea de comandos.

---

## ¿Cómo funciona el sistema?

```
  Tú subes el Excel          GitHub lo procesa          La app se actualiza
  en la web de GitHub   →    automáticamente        →   en ~60 segundos
  (sin instalar nada)        (robot en la nube)         (Streamlit Cloud)
```

Cuando subes `planeacion_anual.xlsx` o `reservas.xlsx`, un robot de GitHub:
1. Lee el Excel y convierte cada hoja en datos optimizados
2. Guarda el resultado en el archivo `data_source.py`
3. Streamlit Cloud detecta el cambio y redespliega la app

---

## Actualizar los datos (flujo normal)

### Paso 1 — Abre el repositorio en GitHub

Ve a la página principal del repositorio en tu navegador.  
Deberías ver la lista de archivos del proyecto.

---

### Paso 2 — Sube el archivo Excel

**Opción A — Arrastrar y soltar (más fácil)**

1. Abre la carpeta de tu computador donde está el Excel
2. Arrastra el archivo y suéltalo sobre la lista de archivos en GitHub

```
  ┌─────────────────────────────────────────────┐
  │  📁 UCEN  /  main                           │
  │  ─────────────────────────────────────────  │
  │  📄 app.py                                  │
  │  📄 data_source.py                          │
  │  📄 update_data.py              ← suelta    │
  │                                    aquí ↓   │
  │  ╔═══════════════════════════════════════╗  │
  │  ║  Arrastra archivos para subirlos      ║  │
  │  ╚═══════════════════════════════════════╝  │
  └─────────────────────────────────────────────┘
```

**Opción B — Botón de carga**

1. Haz clic en **"Add file"** → **"Upload files"**
2. Selecciona el archivo desde tu computador
3. En el campo **"Commit changes"**, escribe una descripción breve  
   (ej: `Actualización semestre 2026-02`)
4. Haz clic en **"Commit changes"** (botón verde)

> **Importante:** el nombre del archivo debe ser exactamente  
> `planeacion_anual.xlsx` o `reservas.xlsx` (en minúsculas, sin espacios).

---

### Paso 3 — El robot se activa solo

En cuanto GitHub recibe el archivo, el robot se activa automáticamente.  
No necesitas hacer nada más — solo esperar.

Puedes observar el progreso en tiempo real:

1. Ve a la pestaña **"Actions"** del repositorio
2. Verás una fila nueva con el nombre **"Actualizar datos UCEN"**

```
  ┌──────────────────────────────────────────────────────┐
  │  Actions                                             │
  │  ──────────────────────────────────────────────────  │
  │  ● Actualizar datos UCEN   · hace 30 seg  · en curso │
  │  ✓ Actualizar datos UCEN   · hace 2 horas · exitoso  │
  │  ✓ Actualizar datos UCEN   · hace 1 día   · exitoso  │
  └──────────────────────────────────────────────────────┘
```

Un círculo girando `●` significa que está procesando.  
Una marca verde `✓` significa que terminó con éxito.  
Una `✗` roja significa que algo falló (ver sección [Solución de problemas](#solución-de-problemas)).

---

### Paso 4 — Verifica en la app

Espera ~60 segundos después de que el robot termine y abre la app de Streamlit.  
La fecha de la última actualización aparece en la esquina superior derecha de la pantalla:

```
                              ┌──────────────────────┐
                              │ 🕐 Última actualización │
                              │    27/06/2026  14:35  │
                              └──────────────────────┘
```

Si la fecha coincide con la hora en que subiste el archivo, **el ciclo está completo**.

---

## Verificar un despliegue exitoso

### ✓ En GitHub Actions — pestaña "Summary"

Haz clic en la ejecución más reciente y luego en **"Summary"**.  
Verás una tabla de resumen como esta:

```
  ✅ UCEN · Resumen de actualización

  ┌────────────────────┬────────────────────────────┐
  │ Estado             │ ✅ success                  │
  │ Disparado por      │ tu-usuario                  │
  │ Hora UTC           │ 2026-06-27 17:35:12 UTC     │
  │ Motivo             │ push de Excel               │
  └────────────────────┴────────────────────────────┘

  Resultado
  📦 data_source.py actualizado — Streamlit redespliegará en ~60 s
```

Si en **Resultado** dice `📦 data_source.py actualizado`, el despliegue está en camino.  
Si dice `ℹ️ Sin cambios detectados`, el Excel subido era idéntico al anterior.

### ✓ En los logs del robot (opcional)

Para ver el detalle técnico, haz clic en el paso **"Procesar Excel → data_source.py"**:

```
  ══════════════════════════════════════════════════════════════
    UCEN - Actualizador de datos  [GitHub Actions (CI)]
    2026-06-27 14:35:01 (hora Chile)
  ══════════════════════════════════════════════════════════════

  Archivos detectados:
     OK      planeacion_anual.xlsx
     AUSENTE reservas.xlsx

  ──────────────────────────────────────────────────────────────
    [PLANEACIÓN] Procesando: planeacion_anual.xlsx
  ──────────────────────────────────────────────────────────────
    Hojas encontradas (12): 202601_res, 202601_det, ...

    [1/12] Procesando hoja '202601_res' → clave '202601_res'
     ✓ [REMEDIACIÓN '202601_res'] Datos limpios — sin correcciones.
     ✓ CODIFICADO: 245 filas × 8 cols → 12.3 KB Base64

    [2/12] Procesando hoja '202601_det' → clave '202601_det'
     ✓ CODIFICADO: 1840 filas × 11 cols → 94.1 KB Base64
     ...

  ──────────────────────────────────────────────────────────────
    [VERIFICACIÓN] Comprobando integridad de 12 clave(s)...
  ──────────────────────────────────────────────────────────────
     ✓ '202601_res': 245 filas x 8 cols
     ✓ '202601_det': 1840 filas x 11 cols
     ...
     Todas las claves pasaron la verificacion de integridad.

  ══════════════════════════════════════════════════════════════
    ✓ COMPLETADO en 8s
    Claves actualizadas (12):
      ✓ 202601_res
      ✓ 202601_det
      ...
  ══════════════════════════════════════════════════════════════
```

**Lo que indica éxito:**
- Cada hoja muestra `✓ CODIFICADO`
- La sección de verificación muestra `✓` para todas las claves
- El resumen final dice `✓ COMPLETADO`

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| El robot no se activa tras subir el Excel | El nombre del archivo tiene mayúsculas o espacios | Renombrar a `planeacion_anual.xlsx` (sin espacios, en minúsculas) |
| El robot muestra `✗` roja en Actions | El Excel tiene una hoja completamente vacía | Abrir el Excel, eliminar la hoja vacía y volver a subir |
| La app no se actualiza después de 5 minutos | Streamlit Cloud tarda más de lo normal | Esperar 3-5 minutos más; si persiste, entrar a share.streamlit.io y forzar redeploy |
| El robot dice "Sin cambios detectados" | El Excel subido es idéntico al anterior | Verificar que guardaste los cambios en el Excel antes de subir |
| La fecha de actualización en la app muestra hora incorrecta | — | La hora se muestra en zona horaria Chile (America/Santiago) |
| El robot se cancela después de 15 minutos | El Excel es muy grande o tiene formato corrupto | Reducir el tamaño del archivo o guardar como nuevo Excel |

### Si el robot falla con `⚠` (advertencia)

Una advertencia `⚠` en los logs **no detiene el proceso** — solo indica que esa hoja específica no fue actualizada y se conservó el valor anterior. El resto de las hojas se actualiza normalmente.

```
  [3/12] Procesando hoja '202602_xyz' → clave '202602_xyz'
  ⚠  '202602_xyz': DataFrame sin filas de datos — conservando valor anterior.
```

Esto ocurre cuando una hoja del Excel está vacía. Si esa hoja tiene datos importantes, revisa el archivo y vuelve a subirlo.

### Si necesitas forzar una actualización sin subir Excel

En la pestaña **Actions** → **"Actualizar datos UCEN"** → **"Run workflow"**:

```
  ┌─────────────────────────────────────────────────┐
  │  Run workflow                                    │
  │  Branch: main                                   │
  │  Motivo (opcional): Refresco forzado manual     │
  │                                           [Run] │
  └─────────────────────────────────────────────────┘
```

Esto re-ejecuta el robot con los archivos Excel que ya están en el repositorio.

---

## Estructura del repositorio

```
  UCEN/
  ├── app.py                   ← Aplicación Streamlit (visualizaciones)
  ├── data_source.py           ← Datos codificados (generado automáticamente)
  ├── update_data.py           ← Robot de procesamiento de Excel
  ├── planeacion_anual.xlsx    ← Excel de entrada (tú lo subes)
  ├── reservas.xlsx            ← Excel de reservas (tú lo subes)
  ├── LÉAME.md                 ← Esta guía
  └── .github/
      └── workflows/
          └── deploy.yml       ← Configuración del robot de GitHub Actions
```

> **Nunca edites `data_source.py` manualmente.**  
> Es generado automáticamente por el robot cada vez que subes un Excel.  
> Cualquier cambio manual se sobreescribirá en la próxima actualización.

---

## Ciclo completo en resumen

```
  1. Preparas el Excel en tu computador
         ↓
  2. Lo arrastras a GitHub (web)
         ↓
  3. El robot corre automáticamente (~30-60 segundos)
         ↓
  4. Streamlit Cloud redespliega la app (~60 segundos)
         ↓
  5. La fecha de actualización cambia en la esquina de la app
         ↓
  ✓ Listo — los usuarios ya ven los datos nuevos
```

**Tiempo total desde subir el Excel hasta ver los datos actualizados: ~2 minutos.**
