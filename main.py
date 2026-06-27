from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import subprocess
import os
import time
import sys
from pydantic import BaseModel
import asyncio

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER_PATH = os.path.join(BASE_DIR, "mcp_server", "redmes_server.py")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Import logic
from db.database import init_db
from mcp_server.redmes_server import mcp
from orchestrator import analyze_message, format_for_channel

app = FastAPI(title="Redmes")

# Serve static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Subprocess tracking
mcp_process = None

# Rate limiting (in-memory, simple implementation)
last_request_time = {}

class AnalyzeRequest(BaseModel):
    raw_text: str
    recipient_name: str
    platform: str

class FormatRequest(BaseModel):
    chosen_message: str
    platform: str
    relationship_type: str

class OutcomeRequest(BaseModel):
    recipient_name: str
    message: str
    tone: str
    relationship_type: str
    scenario: str
    detected_language: str
    output_language: str
    risk_score: int
    chosen_version: str
    outcome: str

@app.on_event("startup")
def startup_event():
    global mcp_process
    init_db()
    # Launch MCP server as background subprocess
    mcp_process = subprocess.Popen(
        [sys.executable, MCP_SERVER_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=BASE_DIR
    )
    print(f"MCP Server started with PID: {mcp_process.pid}")

@app.on_event("shutdown")
def shutdown_event():
    global mcp_process
    if mcp_process:
        try:
            mcp_process.terminate()
            mcp_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            mcp_process.kill()
        print("MCP Server terminated.")

# Dependency for rate limiting
async def check_rate_limit(request: Request):
    client_ip = request.client.host
    current_time = time.time()
    
    if client_ip in last_request_time:
        if current_time - last_request_time[client_ip] < 2.0:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Maximum 1 request per 2 seconds.")
            
    last_request_time[client_ip] = current_time

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.post("/analyze")
async def api_analyze(request: AnalyzeRequest, req: Request):
    await check_rate_limit(req)
    
    if not request.raw_text or not request.recipient_name or not request.platform:
        raise HTTPException(status_code=400, detail="Missing required fields.")
        
    # Sanitize input via MCP tool
    sanitized_text = mcp._tool_manager.get_tool("sanitize_input").fn(request.raw_text)
    sanitized_name = mcp._tool_manager.get_tool("sanitize_input").fn(request.recipient_name)
    
    if not sanitized_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty after sanitization.")
        
    try:
        result = await analyze_message(sanitized_text, sanitized_name, request.platform)
        # Pass the sanitized text back so the UI has it
        result["sanitized_text"] = sanitized_text
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/format")
async def api_format(request: FormatRequest):
    if not request.chosen_message or not request.platform:
        raise HTTPException(status_code=400, detail="Missing required fields.")
        
    sanitized_msg = mcp._tool_manager.get_tool("sanitize_input").fn(request.chosen_message)
    
    try:
        result = await format_for_channel(sanitized_msg, request.platform, request.relationship_type)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/outcome")
async def api_outcome(request: OutcomeRequest):
    if not request.recipient_name or not request.outcome:
        raise HTTPException(status_code=400, detail="Missing required fields.")
        
    sanitized_name = mcp._tool_manager.get_tool("sanitize_input").fn(request.recipient_name)
    sanitized_msg = mcp._tool_manager.get_tool("sanitize_input").fn(request.message)
    
    try:
        mcp._tool_manager.get_tool("save_message_log").fn(
            name=sanitized_name,
            raw_message=sanitized_msg,
            tone=request.tone,
            relationship_type=request.relationship_type,
            scenario=request.scenario,
            detected_language=request.detected_language,
            output_language=request.output_language,
            risk_score=request.risk_score,
            chosen_version=request.chosen_version,
            outcome=request.outcome
        )
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
