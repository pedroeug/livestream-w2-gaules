from fastapi import APIRouter, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse

router = APIRouter()

class TranslationRequest(BaseModel):
    channel: str

@router.post("/start-translation")
async def start_translation(request: TranslationRequest):
    channel = request.channel

    # Aqui será substituído pela lógica real de dublagem e stream com delay
    # Por enquanto, simulamos uma resposta estática
    result_url = f"https://livestream-w2-gaules-v2.onrender.com/fake-output/{channel}.mp4"

    return JSONResponse(content={"video_url": result_url})
