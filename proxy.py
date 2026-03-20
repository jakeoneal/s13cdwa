import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NIM_API_KEY = os.environ["NVIDIA_NIM_API_KEY"]
MASTER_KEY = os.environ["LITELLM_MASTER_KEY"]
NIM_BASE = "https://integrate.api.nvidia.com/v1"
MODEL_ALIAS = "deepseek-v3"
NIM_MODEL = "deepseek-ai/deepseek-v3"

def check_auth(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {MASTER_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/v1/models")
@app.get("/models")
async def list_models(request: Request):
    check_auth(request)
    return JSONResponse({
        "object": "list",
        "data": [{
            "id": MODEL_ALIAS,
            "object": "model",
            "created": 1700000000,
            "owned_by": "nvidia"
        }]
    })

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat(request: Request):
    check_auth(request)
    body = await request.json()
    body["model"] = NIM_MODEL
    body["stream"] = True  # Force streaming so NIM responds immediately

    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
        "Content-Type": "application/json"
    }

    async def generate():
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", f"{NIM_BASE}/chat/completions", json=body, headers=headers) as r:
                async for chunk in r.aiter_bytes():
                    yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")
