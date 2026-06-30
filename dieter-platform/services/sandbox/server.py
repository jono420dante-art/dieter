import os
import sys
from typing import Dict, Any
import subprocess
import json
import logging
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DIETER Sandbox", version="0.1.0")

# API Key validation
def verify_api_key(authorization: str = None) -> bool:
    expected_key = os.getenv("SANDBOX_API_KEY", "sandbox-key-change-in-production")
    if not authorization:
        return False
    token = authorization.replace("Bearer ", "")
    return token == expected_key

class CLIExecuteRequest(BaseModel):
    command: str
    cwd: str = None
    env: Dict[str, str] = None
    timeout: int = 30

class PythonExecuteRequest(BaseModel):
    code: str
    timeout: int = 30

class ScriptExecuteRequest(BaseModel):
    script_path: str
    args: list = []
    timeout: int = 30

class DockerExecuteRequest(BaseModel):
    image: str
    command: str
    env: Dict[str, str] = None
    timeout: int = 60

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "dieter-sandbox",
        "version": "0.1.0"
    }

@app.post("/execute/cli")
async def execute_cli(request: CLIExecuteRequest, authorization: str = None):
    """
    Execute CLI command in sandbox
    """
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        # Set working directory
        cwd = request.cwd or os.getcwd()
        
        # Merge environment
        env = os.environ.copy()
        if request.env:
            env.update(request.env)
        
        # Execute command
        result = subprocess.run(
            request.command,
            shell=True,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=request.timeout
        )
        
        logger.info(f"CLI executed: {request.command[:50]}... (exit_code={result.returncode})")
        
        return {
            "status": "completed",
            "command": request.command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": cwd
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"CLI command timed out: {request.command}")
        return {
            "status": "timeout",
            "error": f"Command timed out after {request.timeout}s"
        }
    
    except Exception as e:
        logger.error(f"CLI execution error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "exit_code": 1
        }

@app.post("/execute/python")
async def execute_python(request: PythonExecuteRequest, authorization: str = None):
    """
    Execute Python code in isolated sandbox
    """
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        # Create temporary script
        temp_script = "/tmp/sandbox_script.py"
        with open(temp_script, "w") as f:
            f.write(request.code)
        
        # Execute
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=request.timeout
        )
        
        logger.info(f"Python code executed (exit_code={result.returncode})")
        
        return {
            "status": "completed",
            "exit_code": result.returncode,
            "output": result.stdout,
            "errors": result.stderr
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"Python execution timed out")
        return {
            "status": "timeout",
            "error": f"Execution timed out after {request.timeout}s"
        }
    
    except Exception as e:
        logger.error(f"Python execution error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/execute/script")
async def execute_script(request: ScriptExecuteRequest, authorization: str = None):
    """
    Execute script file
    """
    if not verify_api_key(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        if not os.path.exists(request.script_path):
            raise FileNotFoundError(f"Script not found: {request.script_path}")
        
        cmd = [request.script_path] + request.args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        logger.info(f"Script executed: {request.script_path}")
        
        return {
            "status": "completed",
            "script": request.script_path,
            "exit_code": result.returncode,
            "output": result.stdout,
            "errors": result.stderr
        }
    
    except Exception as e:
        logger.error(f"Script execution error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )