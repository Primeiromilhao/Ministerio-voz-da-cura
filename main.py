import os
import asyncio
import logging
import uuid
import glob
from fastapi import FastAPI, BackgroundTasks, Form, HTTPException, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Baixador Ministério Voz da Cura")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads_temp")
DEFAULT_COOKIES = os.path.join(BASE_DIR, "cookies.txt")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)

def clean_files(*paths):
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

def find_downloaded_file(session_id: str):
    patterns = [
        os.path.join(DOWNLOAD_DIR, f"{session_id}.*"),
        os.path.join(DOWNLOAD_DIR, f"{session_id}_*.*"),
    ]
    for pattern in patterns:
        files = glob.glob(pattern)
        if files:
            return files[0]
    return None

def run_download(url: str, mode: str, session_id: str, cookie_path: str = None):
    output_template = os.path.join(DOWNLOAD_DIR, f"{session_id}.%(ext)s")

    # Use o cookies.txt do repo se nenhum foi enviado pelo utilizador
    effective_cookie = cookie_path
    if not effective_cookie and os.path.exists(DEFAULT_COOKIES):
        effective_cookie = DEFAULT_COOKIES
        logger.info("Usando cookies.txt do repositorio")

    http_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.youtube.com/",
        "Origin": "https://www.youtube.com",
    }

    base_opts = {
        "outtmpl": output_template,
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,
        "http_headers": http_headers,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        "sleep_interval": 2,
        "max_sleep_interval": 5,
        "sleep_interval_requests": 1,
    }

    if effective_cookie:
        base_opts["cookiefile"] = effective_cookie

    if mode == "audio":
        base_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        base_opts.update({
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
        })

    client_strategies = [
        {"extractor_args": {"youtube": {"player_client": ["tv_embedded"]}}},
        {"extractor_args": {"youtube": {"player_client": ["ios"]}}},
        {"extractor_args": {"youtube": {"player_client": ["web_embedded"]}}},
        {"extractor_args": {"youtube": {"player_client": ["mweb"]}}},
        {},
    ]

    last_error = None
    for strategy in client_strategies:
        opts = {**base_opts, **strategy}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            result = find_downloaded_file(session_id)
            if result:
                logger.info(f"Download OK com strategy: {strategy}")
                return result
        except yt_dlp.utils.DownloadError as e:
            last_error = str(e)
            logger.warning(f"Strategy {strategy} falhou: {last_error[:200]}")
            for f in glob.glob(os.path.join(DOWNLOAD_DIR, f"{session_id}*")):
                try: os.remove(f)
                except: pass
            continue
        except Exception as e:
            last_error = str(e)
            logger.error(f"Erro inesperado com strategy {strategy}: {last_error}")
            continue

    raise Exception(last_error or "Todos os clientes falharam ao baixar o vídeo.")

@app.post("/api/download")
async def api_download(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    mode: str = Form(...),
    cookies: UploadFile = File(None)
):
    if not url or not url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL inválida.")

    session_id = str(uuid.uuid4())
    cookie_path = None

    if cookies and cookies.filename:
        cookie_path = os.path.join(DOWNLOAD_DIR, f"{session_id}_cookies.txt")
        content = await cookies.read()
        with open(cookie_path, "wb") as f:
            f.write(content)

    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(
            None, run_download, url, mode, session_id, cookie_path
        )
    except Exception as e:
        error_msg = str(e)
        if cookie_path:
            background_tasks.add_task(clean_files, cookie_path)
        logger.error(f"Download falhou: {error_msg}")

        detail = "O download falhou. Verifique o link e tente novamente."
        if "bot" in error_msg.lower() or "sign in" in error_msg.lower() or "confirm" in error_msg.lower():
            detail += " ⚠️ O YouTube bloqueou este download. Por favor, abra as 'Configurações Avançadas' e envie um arquivo cookies.txt do seu navegador (extensão 'Get Cookies.txt LOCALLY' no Chrome/Edge)."
        elif "copyright" in error_msg.lower():
            detail += " Este vídeo está bloqueado por direitos autorais."
        elif "private" in error_msg.lower():
            detail += " Este vídeo é privado."

        raise HTTPException(status_code=500, detail=detail)

    filename = os.path.basename(file_path)
    background_tasks.add_task(clean_files, file_path, cookie_path)

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )

app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
