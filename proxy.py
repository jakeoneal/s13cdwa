import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import json

app = FastAPI()

NIM_API_KEY = os.environ["NVIDIA_NIM_API_KEY"]
MASTER_KEY = os.environ["LITELLM_MASTER_KEY"]
NIM_BASE = "https://integrate.api.nvidia.com/v1"
MODEL_ALIAS = "deepseek-v3.2"
NIM_MODEL = "deepseek-ai/deepseek-v3.2"

def check_auth(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {MASTER_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/v1/models")
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
async def chat(request: Request):
    check_auth(request)
    body = await request.json()
    body["model"] = NIM_MODEL

    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
        "Content-Type": "application/json"
    }

    stream = body.get("stream", False)

    async with httpx.AsyncClient(timeout=120) as client:
        if stream:
            async def generate():
                async with client.stream("POST", f"{NIM_BASE}/chat/completions", json=body, headers=headers) as r:
                    async for chunk in r.aiter_bytes():
                        yield chunk
            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            r = await client.post(f"{NIM_BASE}/chat/completions", json=body, headers=headers)
            return JSONResponse(r.json())
