import logging
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class SandboxBridge:
    """
    Bridge to sandbox execution environment
    Handles CLI, shell, and isolated code execution
    """
    
    def __init__(self, proxy_url: str = None):
        self.proxy_url = proxy_url or settings.SANDBOX_PROXY_URL or "http://localhost:5000"
        self.timeout = 30
    
    async def execute_cli_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute CLI command in sandbox
        
        Args:
            command: Shell command to execute
            cwd: Working directory
            env: Environment variables
        
        Returns:
            Dict with stdout, stderr, exit_code
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.proxy_url}/execute/cli",
                    json={
                        "command": command,
                        "cwd": cwd,
                        "env": env
                    },
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"CLI command executed: {command[:50]}...")
                return result
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to execute CLI command: {e}")
            return {
                "status": "error",
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1
            }
    
    async def execute_python_code(
        self,
        code: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Execute Python code in isolated sandbox
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.proxy_url}/execute/python",
                    json={"code": code},
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Python code executed")
                return result
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to execute Python code: {e}")
            return {
                "status": "error",
                "error": str(e),
                "output": ""
            }
    
    async def execute_docker_container(
        self,
        image: str,
        command: str,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute command in Docker container
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.proxy_url}/execute/docker",
                    json={
                        "image": image,
                        "command": command,
                        "env": env
                    },
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Docker container executed: {image}")
                return result
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to execute Docker container: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def execute_script(
        self,
        script_path: str,
        args: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Execute script file
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.proxy_url}/execute/script",
                    json={
                        "script_path": script_path,
                        "args": args or []
                    },
                    headers=self._get_headers()
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Script executed: {script_path}")
                return result
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to execute script: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_sandbox_status(self) -> Dict[str, Any]:
        """
        Check sandbox availability and stats
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.proxy_url}/health",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPError as e:
            logger.error(f"Sandbox not available: {e}")
            return {
                "status": "unavailable",
                "error": str(e)
            }
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if settings.SANDBOX_API_KEY:
            headers["Authorization"] = f"Bearer {settings.SANDBOX_API_KEY}"
        return headers

# Global instance
_sandbox_bridge: Optional[SandboxBridge] = None

def get_sandbox_bridge() -> SandboxBridge:
    global _sandbox_bridge
    if not _sandbox_bridge:
        _sandbox_bridge = SandboxBridge()
    return _sandbox_bridge