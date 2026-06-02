import os
import asyncio
import logging
import uuid
from fastapi import FastAPI, BackgroundTasks, Form, HTTPException, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Baixador Ministério Voz da Cura")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads_temp")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)

def clean_file(filepath: str):
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.error(f"Erro ao deletar {filepath}: {e}")

def clean_files(filepath: str, cookies_path: str = None):
    clean_file(filepath)
    if cookies_path:
        clean_file(cookies_path)

def run_download(url: str, mode: str, cookies_path: str = None) -> str:
    unique_id = str(uuid.uuid4())[:8]
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{unique_id}_%(title)s.%(ext)s")
    is_youtube = "youtube.com" in url or "youtu.be" in url

    if mode == "audio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        ydl_opts = {
            'format': 'bestvideo[vcodec*=avc]+bestaudio[acodec*=m4a]/bestvideo[vcodec*=avc]+bestaudio/best',
            'outtmpl': outtmpl,
            'noplaylist': True,
            'merge_output_format': 'mp4',
        }

    if is_youtube:
        ydl_opts['extractor_args'] = {
            'youtube': {
                'player_client': ['ios'],
            }
        }
        ydl_opts['http_headers'] = {
            'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
        }

    if cookies_path and os.path.exists(cookies_path):
        ydl_opts['cookiefile'] = cookies_path
        logger.info(f"Usando cookies: {cookies_path}")

    logger.info(f"Iniciando download: {url} modo: {mode}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if mode == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"
            else:
                if not os.path.exists(filename):
                    mp4_filename = os.path.splitext(filename)[0] + ".mp4"
                    if os.path.exists(mp4_filename):
                        filename = mp4_filename
            return filename
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Erro yt-dlp: {error_msg}")
        if is_youtube and ("Sign in" in error_msg or "bot" in error_msg.lower() or "confirm" in error_msg.lower()):
            raise Exception(
                "⚠️ O YouTube bloqueou este download. "
                "Por favor, abra as 'Configurações Avançadas' e envie um arquivo cookies.txt "
                "do seu navegador (extensão 'Get Cookies.txt LOCALLY' no Chrome/Edge)."
            )
        raise

@app.post("/api/download")
async def api_download(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    mode: str = Form(...),
    cookies: UploadFile = File(None)
):
    if mode not in ["video", "audio"]:
        raise HTTPException(status_code=400, detail="Modo inválido.")

    cookies_path = None
    if cookies and cookies.filename:
        cookies_id = str(uuid.uuid4())[:8]
        cookies_path = os.path.join(DOWNLOAD_DIR, f"{cookies_id}_cookies.txt")
        try:
            content = await cookies.read()
            if content:
                with open(cookies_path, "wb") as f:
                    f.write(content)
                logger.info(f"Cookies guardados: {cookies_path}")
            else:
                cookies_path = None
        except Exception as e:
            logger.error(f"Erro ao guardar cookies: {e}")
            cookies_path = None

    try:
        filepath = await asyncio.to_thread(run_download, url, mode, cookies_path)
        if not os.path.exists(filepath):
            if cookies_path:
                clean_file(cookies_path)
            raise HTTPException(status_code=500, detail="Arquivo não encontrado após download.")

        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        logger.info(f"Download OK. Tamanho: {file_size_mb:.2f} MB")

        display_name = os.path.basename(filepath)
        if "_" in display_name:
            display_name = display_name.split("_", 1)[1]

        background_tasks.add_task(clean_files, filepath, cookies_path)
        return FileResponse(
            path=filepath,
            filename=display_name,
            media_type="application/octet-stream"
        )
    except Exception as e:
        logger.error(f"Erro no download: {e}")
        if cookies_path:
            clean_file(cookies_path)
        return JSONResponse(
            status_code=500,
            content={"detail": f"O download falhou. Verifique o link e tente novamente. Detalhes: {str(e)}"}
        )

app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
