import os
import asyncio
import logging
import uuid
import glob
import shutil
from fastapi import FastAPI, Form, HTTPException, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Baixador Ministerio Voz da Cura")

DOWNLOAD_DIR = "/app/downloads"
TEMP_DIR = "/app/downloads_temp"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="/app/static"), name="static")

def get_cookies_path(uploaded_cookies=None):
    if uploaded_cookies and os.path.exists(uploaded_cookies):
        logger.info(f"Usando cookies do usuario: {uploaded_cookies}")
        return uploaded_cookies
    
    secret_path = "/etc/secrets/cookies.txt"
    if os.path.exists(secret_path):
        dest = os.path.join(TEMP_DIR, "server_cookies.txt")
        try:
            shutil.copy2(secret_path, dest)
            logger.info(f"Usando cookies secret: {dest}")
            return dest
        except Exception as e:
            logger.warning(f"Erro ao copiar secret cookies: {e}")
    
    repo_cookies = "/app/cookies.txt"
    if os.path.exists(repo_cookies):
        dest = os.path.join(TEMP_DIR, "server_cookies.txt")
        try:
            shutil.copy2(repo_cookies, dest)
            logger.info(f"Usando cookies repositorio: {dest}")
            return dest
        except Exception as e:
            logger.warning(f"Erro ao copiar repo cookies: {e}")
    
    return None

def build_ydl_opts(output_path, format_type, cookies_path=None):
    if format_type == "audio":
        ydl_format = "bestaudio/best"
        postprocessors = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        ydl_format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        postprocessors = []
    
    opts = {
        "format": ydl_format,
        "outtmpl": output_path,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android", "mweb"],
            }
        },
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "postprocessors": postprocessors,
    }
    
    if cookies_path and os.path.exists(cookies_path):
        opts["cookiefile"] = cookies_path
        logger.info(f"Cookies ativos: {cookies_path}")
    
    return opts

async def do_download(url: str, format_type: str, job_id: str, cookies_path: str = None):
    output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")
    opts = build_ydl_opts(output_template, format_type, cookies_path)
    
    loop = asyncio.get_event_loop()
    
    def run_download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.download([url])
    
    try:
        await loop.run_in_executor(None, run_download)
        files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{job_id}.*"))
        if files:
            return files[0]
        return None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Download falhou: {error_msg}")
        
        if "Sign in to confirm" in error_msg or ("bot" in error_msg.lower() and "youtube" in error_msg.lower()):
            raise HTTPException(
                status_code=403,
                detail="O YouTube bloqueou o acesso. Faca upload do seu cookies.txt para continuar. Use a extensao 'Get cookies.txt LOCALLY' no seu navegador."
            )
        raise HTTPException(status_code=500, detail=f"Erro no download: {error_msg}")

@app.get("/")
async def index():
    return FileResponse("/app/static/index.html")

@app.get("/style.css")
async def style():
    return FileResponse("/app/static/style.css")

@app.get("/app.js")
async def appjs():
    return FileResponse("/app/static/app.js")

@app.post("/api/download")
async def api_download(
    url: str = Form(...),
    mode: str = Form("video"),
    cookies: UploadFile = File(None)
):
    job_id = str(uuid.uuid4())
    cookies_path = None
    
    if cookies and cookies.filename:
        cookies_dest = os.path.join(TEMP_DIR, f"user_cookies_{job_id}.txt")
        content = await cookies.read()
        with open(cookies_dest, "wb") as f:
            f.write(content)
        cookies_path = cookies_dest
        logger.info(f"Cookies do usuario: {cookies_dest}")
    
    if not cookies_path:
        cookies_path = get_cookies_path()
    
    format_type = "audio" if mode == "audio" else "video"
    logger.info(f"Download: url={url}, mode={mode}, format={format_type}")
    
    file_path = await do_download(url, format_type, job_id, cookies_path)
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Arquivo nao encontrado apos download.")
    
    filename = os.path.basename(file_path)
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )

@app.post("/download")
async def download_compat(
    url: str = Form(...),
    format: str = Form("mp4"),
    mode: str = Form(None),
    cookies: UploadFile = File(None)
):
    effective_mode = mode if mode else ("audio" if format == "mp3" else "video")
    return await api_download(url=url, mode=effective_mode, cookies=cookies)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
