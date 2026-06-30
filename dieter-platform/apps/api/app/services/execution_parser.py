import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.agent import ToolCallLog, PersistentAgentState
from app.models.job import Job
import uuid

logger = logging.getLogger(__name__)

class ExecutionParser:
    """Central parser for all agent tool calls - routes to appropriate executor"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def parse_agent_response(
        self,
        agent_state_id: str,
        agent_response: Dict[str, Any],
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse agent response and execute tool calls
        
        Args:
            agent_state_id: ID of the agent state
            agent_response: Response from LLM (contains tool_calls)
            job_id: Optional job ID to link execution
        
        Returns:
            Dict with execution results
        """
        try:
            tool_calls = agent_response.get("tool_calls", [])
            results = []
            
            # Update agent state
            agent_state = self.db.query(PersistentAgentState).filter(
                PersistentAgentState.id == uuid.UUID(agent_state_id)
            ).first()
            
            if not agent_state:
                raise ValueError(f"Agent state not found: {agent_state_id}")
            
            agent_state.last_tool_call = {"count": len(tool_calls), "timestamp": datetime.utcnow().isoformat()}
            
            for tool_call in tool_calls:
                result = await self.execute_tool_call(
                    tool_call=tool_call,
                    agent_state_id=agent_state_id,
                    job_id=job_id
                )
                results.append(result)
            
            agent_state.execution_count += 1
            self.db.commit()
            
            return {
                "status": "success",
                "tool_calls_executed": len(results),
                "results": results
            }
        
        except Exception as e:
            logger.error(f"Error parsing agent response: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def execute_tool_call(
        self,
        tool_call: Dict[str, Any],
        agent_state_id: str,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a single tool call by routing to appropriate executor
        
        Tool categories:
        - cli_*: CLI tool execution
        - browser_*: Browser API calls
        - mcp_*: MCP tool calls
        - sandbox_*: Sandbox execution
        - db_*: Database operations
        """
        start_time = datetime.utcnow()
        tool_name = tool_call.get("name", "")
        parameters = tool_call.get("parameters", {})
        
        # Create tool call log
        log_entry = ToolCallLog(
            agent_state_id=uuid.UUID(agent_state_id),
            job_id=uuid.UUID(job_id) if job_id else None,
            tool_name=tool_name,
            parameters=parameters,
            status="running"
        )
        self.db.add(log_entry)
        self.db.flush()
        
        try:
            # Route based on tool category
            if tool_name.startswith("cli_"):
                result = await self._execute_cli_tool(tool_name, parameters)
                category = "cli"
            
            elif tool_name.startswith("browser_"):
                result = await self._execute_browser_tool(tool_name, parameters)
                category = "browser"
            
            elif tool_name.startswith("mcp_"):
                result = await self._execute_mcp_tool(tool_name, parameters)
                category = "mcp"
            
            elif tool_name.startswith("sandbox_"):
                result = await self._execute_sandbox_tool(tool_name, parameters)
                category = "sandbox"
            
            elif tool_name.startswith("db_"):
                result = await self._execute_database_tool(tool_name, parameters)
                category = "db"
            
            else:
                raise ValueError(f"Unknown tool category: {tool_name}")
            
            # Log successful execution
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            log_entry.status = "completed"
            log_entry.result = result
            log_entry.execution_time_ms = int(execution_time)
            log_entry.tool_category = category
            log_entry.completed_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Tool executed successfully: {tool_name} ({execution_time:.0f}ms)")
            
            return {
                "tool_name": tool_name,
                "status": "success",
                "result": result,
                "execution_time_ms": int(execution_time)
            }
        
        except Exception as e:
            error_msg = str(e)
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_entry.status = "failed"
            log_entry.error = error_msg
            log_entry.execution_time_ms = int(execution_time)
            log_entry.completed_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Tool execution failed: {tool_name} - {error_msg}")
            
            return {
                "tool_name": tool_name,
                "status": "error",
                "error": error_msg,
                "execution_time_ms": int(execution_time)
            }
    
    async def _execute_cli_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """Execute CLI tools via sandbox bridge"""
        # Will be implemented by SandboxBridge
        return {
            "type": "cli",
            "tool": tool_name,
            "status": "delegated_to_sandbox"
        }
    
    async def _execute_browser_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """Execute browser APIs"""
        # Browser tools return data from browser context
        return {
            "type": "browser",
            "tool": tool_name,
            "status": "executed"
        }
    
    async def _execute_mcp_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """Execute MCP tools via OpenClaw"""
        from app.services.openclaw_mcp_service import get_openclaw_service
        
        service = get_openclaw_service()
        return await service.execute_tool(tool_name, parameters)
    
    async def _execute_sandbox_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """Execute in sandbox environment"""
        # Will be implemented by SandboxBridge
        return {
            "type": "sandbox",
            "tool": tool_name,
            "status": "delegated_to_sandbox"
        }
    
    async def _execute_database_tool(self, tool_name: str, parameters: Dict) -> Dict:
        """Execute database operations"""
        # Database tools have direct access to self.db
        return {
            "type": "database",
            "tool": tool_name,
            "status": "executed"
        }
    
    async def get_tool_call_history(
        self,
        agent_state_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get recent tool calls for an agent state"""
        logs = self.db.query(ToolCallLog).filter(
            ToolCallLog.agent_state_id == uuid.UUID(agent_state_id)
        ).order_by(ToolCallLog.created_at.desc()).limit(limit).all()
        
        return [
            {
                "tool_name": log.tool_name,
                "status": log.status,
                "result": log.result,
                "error": log.error,
                "execution_time_ms": log.execution_time_ms,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]

# Global instance
_parser: Optional[ExecutionParser] = None

def get_execution_parser(db: Session) -> ExecutionParser:
    return ExecutionParser(db)