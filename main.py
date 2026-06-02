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

# Cria pastas necessárias
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads_temp")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)

# Define caminhos locais para FFmpeg no Windows
LOCAL_FFMPEG = r"C:\Users\Utilizador\BaixadorUniversal"

def get_ffmpeg_location():
    if os.path.exists(LOCAL_FFMPEG):
        return LOCAL_FFMPEG
    return None

def clean_file(filepath: str):
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Arquivo temporário deletado: {filepath}")
    except Exception as e:
        logger.error(f"Erro ao deletar arquivo {filepath}: {e}")

def clean_files(filepath: str, cookies_path: str = None):
    clean_file(filepath)
    if cookies_path:
        clean_file(cookies_path)

def run_download(url: str, mode: str, cookies_path: str = None) -> str:
    unique_id = str(uuid.uuid4())[:8]
    # Limita o template de output para incluir um ID único e evitar conflitos de nomes simultâneos
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{unique_id}_%(title)s.%(ext)s")
    
    ffmpeg_loc = get_ffmpeg_location()
    
    if mode == "audio":
        ydl_opts = {
            'format': 'bestaudio[language*=pt]/bestaudio',
            'outtmpl': outtmpl,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:  # video
        ydl_opts = {
            'format': 'bestvideo[vcodec*=avc]+bestaudio[acodec*=m4a]/bestvideo[vcodec*=avc]+bestaudio/best[vcodec*=avc]/best',
            'outtmpl': outtmpl,
            'noplaylist': True,
            'merge_output_format': 'mp4',
        }
        
    if ffmpeg_loc:
        ydl_opts['ffmpeg_location'] = ffmpeg_loc
        logger.info(f"Usando FFmpeg local em: {ffmpeg_loc}")

    if cookies_path:
        ydl_opts['cookiefile'] = cookies_path
        logger.info(f"Usando arquivo de cookies: {cookies_path}")

    logger.info(f"Iniciando download para url: {url} em modo: {mode}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # ydl.prepare_filename resolve o nome final, mas para o áudio com pós-processador do FFmpeg, a extensão vira .mp3
        filename = ydl.prepare_filename(info)
        
        if mode == "audio":
            filename = os.path.splitext(filename)[0] + ".mp3"
        else:
            # Garante que a extensão final seja .mp4 caso o download original tenha sido fundido pelo ffmpeg
            if not os.path.exists(filename):
                mp4_filename = os.path.splitext(filename)[0] + ".mp4"
                if os.path.exists(mp4_filename):
                    filename = mp4_filename
                    
        return filename

@app.post("/api/download")
async def api_download(
    background_tasks: BackgroundTasks, 
    url: str = Form(...), 
    mode: str = Form(...),
    cookies: UploadFile = File(None)
):
    if mode not in ["video", "audio"]:
        raise HTTPException(status_code=400, detail="Modo inválido. Escolha 'video' ou 'audio'.")
        
    cookies_path = None
    if cookies and cookies.filename:
        # Salva o arquivo de cookies temporário
        cookies_id = str(uuid.uuid4())[:8]
        cookies_path = os.path.join(DOWNLOAD_DIR, f"{cookies_id}_cookies.txt")
        try:
            content = await cookies.read()
            if content:
                with open(cookies_path, "wb") as f:
                    f.write(content)
                logger.info(f"Arquivo de cookies salvo temporariamente em: {cookies_path}")
            else:
                cookies_path = None
        except Exception as e:
            logger.error(f"Erro ao salvar cookies: {e}")
            cookies_path = None
            
    try:
        # Executa o download de forma não-bloqueante na thread pool
        filepath = await asyncio.to_thread(run_download, url, mode, cookies_path)
        
        if not os.path.exists(filepath):
            logger.error("Arquivo baixado não foi encontrado no disco.")
            if cookies_path:
                clean_file(cookies_path)
            raise HTTPException(status_code=500, detail="Erro ao localizar o arquivo baixado.")
            
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        logger.info(f"Download concluído com sucesso. Tamanho: {file_size_mb:.2f} MB")
        
        display_name = os.path.basename(filepath)
        # Remove o ID único do nome exibido ao usuário
        if "_" in display_name:
            display_name = display_name.split("_", 1)[1]
            
        # Adiciona a limpeza do arquivo para rodar em segundo plano após o download terminar
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

# Serve os arquivos estáticos (HTML/CSS/JS)
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Inicia localmente na porta 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
