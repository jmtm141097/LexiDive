"""FastAPI web app for Immersion Reader."""
import json
import os
import shutil
import tempfile
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

ROOT = Path(__file__).parent
DICT_DIR = ROOT / "diccionarios"

MAX_EPUB_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_JOBS = 500
JOB_TTL_SECONDS = 7200  # 2 horas

limiter = Limiter(key_func=get_remote_address)

_DICT_NOMBRES = {
    "fantasia": "Fantasía medieval",
    "romance": "Romance",
    "terror": "Terror / Horror",
    "ciencia_ficcion": "Ciencia ficción",
}


def _dict_nombre(tipo: str) -> str:
    return _DICT_NOMBRES.get(tipo, tipo.replace("_", " ").title())


_dict_cache: list | None = None


def _build_dict_list() -> list:
    result = []
    for f in sorted(DICT_DIR.glob("*.json")):
        parts = f.stem.split("_", 2)
        if len(parts) < 3:
            continue
        orig, dest, tipo = parts[0], parts[1], "_".join(parts[2:])
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            palabras = len(data)
        except Exception:
            continue
        result.append({
            "id": f.stem,
            "origen": orig,
            "destino": dest,
            "tipo": tipo,
            "nombre": _dict_nombre(tipo),
            "palabras": palabras,
        })
    return result


def _warm_dict_cache() -> None:
    global _dict_cache
    _dict_cache = _build_dict_list()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _warm_dict_cache()
    yield


app = FastAPI(title="Immersion Reader", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

_lock = threading.Lock()
jobs: dict[str, dict] = {}


def _update_job(job_id: str, **kwargs):
    with _lock:
        if job_id in jobs:
            jobs[job_id].update(kwargs)


def _schedule_cleanup(tmpdir: str, delay: int = 3600):
    def _do_cleanup():
        shutil.rmtree(tmpdir, ignore_errors=True)

    t = threading.Timer(delay, _do_cleanup)
    t.daemon = True
    t.start()


def _evict_old_jobs() -> None:
    """Remove completed/errored jobs older than JOB_TTL_SECONDS. Cap at MAX_JOBS."""
    now = time.time()
    to_delete = [
        jid for jid, job in jobs.items()
        if job["status"] in ("done", "error")
        and now - job.get("created_at", now) > JOB_TTL_SECONDS
    ]
    for jid in to_delete:
        del jobs[jid]

    if len(jobs) > MAX_JOBS:
        overflow = sorted(
            [(jid, job["created_at"]) for jid, job in jobs.items()
             if job["status"] in ("done", "error")],
            key=lambda x: x[1],
        )
        for jid, _ in overflow[: len(jobs) - MAX_JOBS]:
            del jobs[jid]


def _user_friendly_error(exc: Exception) -> str:
    """Map exceptions to user-friendly Spanish messages without leaking internals."""
    cls_name = type(exc).__name__
    msg = str(exc)

    # Type checks first (most specific)
    if isinstance(exc, ValueError):
        # Only pass through messages from our own controlled raises
        safe_keywords = ("diccionario", "api key", "proporciona", "vacío")
        if any(kw in msg.lower() for kw in safe_keywords):
            return msg
        return "Error de validación al procesar el libro. Verifica los parámetros e inténtalo de nuevo."
    if isinstance(exc, FileNotFoundError):
        return "Error al leer el archivo. Verifica que el epub no esté dañado."

    # Class name checks for known API exceptions
    if "AuthorizationException" in cls_name or "authorization" in msg.lower():
        return "API key inválida. Verifica que sea correcta e inténtalo de nuevo."
    if "QuotaExceededException" in cls_name or "quota" in msg.lower():
        return "Límite de caracteres de la API alcanzado. Intenta más tarde o usa un diccionario base."
    if "ConnectionException" in cls_name:
        return "Error de conexión con el proveedor de traducción. Intenta más tarde."

    return "Error interno al procesar el libro. Intenta de nuevo con otro archivo."


def _run_pipeline(job_id: str, params: dict):
    from immersion.extractor import extraer_vocab
    from immersion.traductor import cargar_diccionario, guardar_diccionario, traducir_palabras, traducir_palabras_google
    from immersion.anotador import anotar_epub
    from immersion.anki_export import exportar_anki

    try:
        _update_job(job_id, status="running")
        salida = Path(params["ruta_salida"])

        # Step 1: load base dictionary
        _update_job(job_id, message="Cargando diccionario base...", progress=8)
        diccionario: dict[str, str] = {}
        if params.get("ruta_diccionario"):
            diccionario = cargar_diccionario(params["ruta_diccionario"])

        # Step 2: extract vocabulary
        _update_job(job_id, message="Extrayendo vocabulario del libro...", progress=20)
        vocab = extraer_vocab(
            params["ruta_epub"],
            idioma=params["origen"],
            min_longitud=params.get("min_longitud", 4),
            max_palabras=params.get("max_palabras", 500),
            excluir=set(diccionario.keys()),
        )
        palabras_nuevas = [p for p, _ in vocab]
        _update_job(job_id, message=f"{len(palabras_nuevas)} palabras nuevas encontradas", progress=35)

        # Step 3: translate via DeepL or Google AI
        api_key = params.get("api_key")
        google_api_key = params.get("google_api_key")
        if palabras_nuevas and (api_key or google_api_key):
            provider = "Google AI" if google_api_key else "DeepL"
            _update_job(job_id, message=f"Traduciendo {len(palabras_nuevas)} palabras con {provider}...", progress=50)
            if google_api_key:
                nuevas = traducir_palabras_google(palabras_nuevas, params["origen"], params["destino"], google_api_key)
            else:
                nuevas = traducir_palabras(palabras_nuevas, params["origen"], params["destino"], api_key)
            diccionario.update(nuevas)
            guardar_diccionario(diccionario, str(salida.with_suffix(".json")))
            _update_job(job_id, message=f"Diccionario guardado ({len(diccionario)} entradas)", progress=65)

        diccionario_activo = {k: v for k, v in diccionario.items() if v}
        if not diccionario_activo:
            raise ValueError(
                "El diccionario está vacío. Proporciona una API key de DeepL o Google AI, o un diccionario JSON con traducciones."
            )

        # Step 4: annotate epub
        _update_job(job_id, message=f"Anotando el libro (intensidad={params['intensidad']})...", progress=75)
        capitulos = anotar_epub(
            params["ruta_epub"],
            params["ruta_salida"],
            diccionario_activo,
            params["intensidad"],
            params.get("semilla"),
        )
        _update_job(job_id, message=f"{capitulos} capítulos anotados", progress=84)

        # Step 4b: generate StarDict dictionary for KOReader
        from immersion.stardict import generar_stardict
        ruta_zip = salida.with_suffix(".stardict.zip")
        generar_stardict(diccionario_activo, str(ruta_zip), params.get("nombre_mazo", "Immersion Reader"))
        _update_job(job_id, message="Diccionario KOReader generado", progress=88)

        # Step 5: export Anki deck
        if params.get("exportar_anki_deck", True):
            _update_job(job_id, message=f"Generando mazo Anki ({len(diccionario_activo)} tarjetas)...", progress=94)
            exportar_anki(
                diccionario_activo,
                str(salida.with_suffix(".apkg")),
                nombre_mazo=params.get("nombre_mazo"),
            )

        stats = {
            "capitulos": capitulos,
            "palabras_nuevas": len(palabras_nuevas),
            "total_diccionario": len(diccionario_activo),
        }
        _update_job(job_id, status="done", stats=stats, progress=100,
                    message=f"¡Completado! {capitulos} capítulos, {len(diccionario_activo)} palabras",
                    has_dict=ruta_zip.exists())

    except Exception as exc:
        _update_job(job_id, status="error", message=_user_friendly_error(exc), progress=0)


@app.get("/diccionarios")
async def listar_diccionarios(origen: Optional[str] = None, destino: Optional[str] = None):
    cache = _dict_cache if _dict_cache is not None else _build_dict_list()
    result = [
        d for d in cache
        if (not origen or d["origen"] == origen)
        and (not destino or d["destino"] == destino)
    ]
    return result


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((ROOT / "static" / "index.html").read_text(encoding="utf-8"))


@app.post("/process")
@limiter.limit("5/minute")
async def process(
    request: Request,
    epub: UploadFile = File(...),
    google_key: Optional[str] = Form(None),
    diccionario_tipo: str = Form("fantasia"),
    diccionario_json: Optional[UploadFile] = File(None),
    intensidad: int = Form(3),
    max_palabras: int = Form(500),
    semilla: Optional[int] = Form(None),
    origen: str = Form("es"),
    destino: str = Form("en"),
    sin_anki: str = Form("false"),
):
    if not epub.filename or not epub.filename.lower().endswith(".epub"):
        raise HTTPException(400, "El archivo debe ser un .epub")

    job_id = str(uuid.uuid4())
    tmpdir = tempfile.mkdtemp(prefix=f"immersion_{job_id[:8]}_")
    tmp = Path(tmpdir)

    epub_path = tmp / epub.filename
    content = bytearray()
    while True:
        chunk = await epub.read(65536)
        if not chunk:
            break
        content += chunk
        if len(content) > MAX_EPUB_BYTES:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise HTTPException(
                400,
                f"El archivo supera el límite de {MAX_EPUB_BYTES // (1024 * 1024)} MB"
            )
    epub_path.write_bytes(bytes(content))
    salida_path = tmp / (epub_path.stem + "_anotado.epub")

    ruta_diccionario = None
    if diccionario_tipo == "propio" and diccionario_json:
        dict_path = tmp / "diccionario_custom.json"
        dict_bytes = await diccionario_json.read()
        try:
            json.loads(dict_bytes)
        except (json.JSONDecodeError, ValueError):
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise HTTPException(400, "El diccionario JSON no es válido")
        dict_path.write_bytes(dict_bytes)
        ruta_diccionario = str(dict_path)
    elif diccionario_tipo not in ("propio", "ninguno"):
        builtin = DICT_DIR / f"{diccionario_tipo}.json"
        if builtin.exists():
            ruta_diccionario = str(builtin)

    deepl_api_key = os.environ.get("DEEPL_API_KEY")
    google_api_key = (google_key.strip() or None) if google_key else None

    if not deepl_api_key and not google_api_key and not ruta_diccionario:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(
            400,
            "El servidor no tiene configurada una API key de DeepL. "
            "Selecciona un diccionario base o usa Google AI con tu propia clave."
        )

    params = dict(
        ruta_epub=str(epub_path),
        ruta_salida=str(salida_path),
        origen=origen,
        destino=destino,
        intensidad=intensidad,
        api_key=deepl_api_key,
        google_api_key=google_api_key,
        ruta_diccionario=ruta_diccionario,
        semilla=semilla,
        max_palabras=max_palabras,
        exportar_anki_deck=(sin_anki.lower() != "true"),
        nombre_mazo=epub_path.stem,
    )

    with _lock:
        _evict_old_jobs()
        jobs[job_id] = {
            "status": "pending",
            "message": "Iniciando...",
            "progress": 3,
            "stats": None,
            "tmpdir": tmpdir,
            "stem": salida_path.stem,
            "created_at": time.time(),
            "files": {
                "epub": str(salida_path),
                "json": str(salida_path.with_suffix(".json")),
                "apkg": str(salida_path.with_suffix(".apkg")),
                "dict": str(salida_path.with_suffix(".stardict.zip")),
            },
        }

    _schedule_cleanup(tmpdir, delay=3600)

    t = threading.Thread(target=_run_pipeline, args=(job_id, params), daemon=True)
    t.start()

    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def status(job_id: str):
    with _lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    return {
        "status": job["status"],
        "message": job["message"],
        "progress": job.get("progress", 0),
        "stats": job["stats"],
    }


@app.get("/download/{job_id}/{file_type}")
async def download(job_id: str, file_type: str):
    with _lock:
        job = jobs.get(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Archivo no disponible aún")

    file_map = {
        "epub": (".epub", "application/epub+zip"),
        "json": (".json", "application/json"),
        "apkg": (".apkg", "application/octet-stream"),
        "dict": (".stardict.zip", "application/zip"),
    }
    if file_type not in file_map:
        raise HTTPException(400, "Tipo de archivo inválido")

    ext, media_type = file_map[file_type]
    path = Path(job["files"][file_type])
    if not path.exists():
        raise HTTPException(404, f"El archivo {file_type} no fue generado")

    filename = job["stem"] + ext
    return FileResponse(path, media_type=media_type, filename=filename)


if __name__ == "__main__":
    uvicorn.run("webapp:app", host="0.0.0.0", port=8000, reload=True)
