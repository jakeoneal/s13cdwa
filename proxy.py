import os
import httpx
import json
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
        "nim_model": os.environ.get("NIM_MODEL", "deepseek-ai/deepseek-v3.2"),
        "thinking": os.environ.get("THINKING_MODE", "false").lower() == "true",
        "debug": os.environ.get("DEBUG", "false").lower() == "true",
    }

def debug_log(config, label, data):
    if not config["debug"]:
        return
    print(f"\n{'='*50}")
    print(f"DEBUG [{label}]")
    print('='*50)
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)
    print('='*50 + "\n")

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
    body["stream"] = True
    body["extra_body"] = {"chat_template_kwargs": {"thinking": config["thinking"]}}

    if config["debug"]:
        messages = body.get("messages", [])
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            debug_log(config, f"{role} MESSAGE", content)

    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
        "Content-Type": "application/json"
    }

    accumulated_response = []

    async def generate():
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", f"{NIM_BASE}/chat/completions", json=body, headers=headers) as r:
                async for chunk in r.aiter_bytes():
                    if config["debug"]:
                        try:
                            text = chunk.decode("utf-8")
                            for line in text.splitlines():
                                if line.startswith("data: ") and line != "data: [DONE]":
                                    data = json.loads(line[6:])
                                    delta = data.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        accumulated_response.append(content)
                        except Exception:
                            pass
                    yield chunk

        if config["debug"] and accumulated_response:
            debug_log(config, "ASSISTANT RESPONSE", "".join(accumulated_response))

    return StreamingResponse(generate(), media_type="text/event-stream")
