import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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

def get_config():
    return {
        "model_alias": os.environ.get("MODEL_ALIAS", "deepseek-v3"),
        "nim_model": os.environ.get("NIM_MODEL", "deepseek-ai/deepseek-v3"),
        "force_stream": os.environ.get("FORCE_STREAM", "false").lower() == "true",
    }

def check_auth(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {MASTER_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/")
@app.head("/")
async def health():
    return JSONResponse({"status": "ok"})

@app.get("/v1/models")
@app.get("/models")
async def list_models(request: Request):
    check_auth(request)
    config = get_config()
    return JSONResponse({
        "object": "list",
        "data": [{
            "id": config["model_alias"],
            "object": "model",
            "created": 1700000000,
            "owned_by": "nvidia"
        }]
    })

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
@app.post("/")
async def chat(request: Request):
    check_auth(request)
    config = get_config()
    body = await request.json()
    body["model"] = config["nim_model"]

    if config["force_stream"]:
        body["stream"] = True
    else:
        body["stream"] = False

    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
        "Content-Type": "application/json"
    }

    if body["stream"]:
        async def generate():
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("POST", f"{NIM_BASE}/chat/completions", json=body, headers=headers) as r:
                    async for chunk in r.aiter_bytes():
                        yield chunk
        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{NIM_BASE}/chat/completions", json=body, headers=headers)
            return JSONResponse(r.json())
