from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import subprocess
import os
import shutil
import logging
from typing import Optional

app = FastAPI(title="AutoSubtitle API")

MODEL_SIZE = os.getenv("MODEL_SIZE", "base")
DEVICE = os.getenv("DEVICE", "cpu")
LANGUAGE = os.getenv("LANGUAGE", "en")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.post("/transcribe")
async def transcribe_audio(
        file: Optional[UploadFile] = File(None),
        input_file: Optional[str] = None
):

    temp_dir = "/tmp/autosub"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        if file:
            input_path = os.path.join(temp_dir, file.filename)
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(f"Received uploaded file: {file.filename}")
        elif input_file and os.path.exists(input_file):
            input_path = input_file
            logger.info(f"Using existing file: {input_file}")
        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'file' or 'input_file' must be provided"
            )

        output_srt = "/files/audio.srt"

        cmd = [
            "auto_subtitle",
            input_path,
            "--output_srt", "True",
            "--output_dir", "/files",
            "--model", MODEL_SIZE,
            "--device", DEVICE,
            "--language", LANGUAGE
        ]

        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Transcription failed: {result.stderr}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Transcription failed",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            )

        if os.path.exists(output_srt):
            with open(output_srt, "r", encoding="utf-8") as f:
                subtitles = f.read()

            return JSONResponse(content={
                "status": "success",
                "message": "Transcription successful",
                "subtitles": subtitles,
                "format": "srt"
            })
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "SRT file was not created",
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            )

    except Exception as e:
        logger.error(f"Exception during transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "autosub"}


@app.get("/")
async def root():
    return {"message": "AutoSubtitle API is running"}