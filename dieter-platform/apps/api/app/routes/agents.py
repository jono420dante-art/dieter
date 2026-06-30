import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_db
from app.middleware.jwt_auth import verify_jwt
from app.adapters.manus_adapter import ManusMCPAdapter
from app.services.execution_parser import get_execution_parser
from app.services.sandbox_bridge import get_sandbox_bridge
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

class WorkspaceCreate(BaseModel):
    name: str
    agents: list

class AgentInitialize(BaseModel):
    agent_type: str
    agent_name: str
    workspace_id: str
    tool_schema: dict
    system_prompt: str

class TaskDispatch(BaseModel):
    agent_state_id: str
    task_description: str
    context: dict = None

class AgentResponse(BaseModel):
    agent_state_id: str
    llm_response: dict
    job_id: str = None

@router.post("/workspaces/create")
async def create_workspace(
    request: WorkspaceCreate,
    db: Session = Depends(get_db),
    user_data: dict = Depends(verify_jwt)
):
    """
    Create agent workspace for multi-agent collaboration
    """
    adapter = ManusMCPAdapter(db)
    result = await adapter.create_agent_workspace(
        user_id=user_data["user_id"],
        name=request.name,
        agents=request.agents
    )
    return result

@router.post("/agents/initialize")
async def initialize_agent(
    request: AgentInitialize,
    db: Session = Depends(get_db),
    user_data: dict = Depends(verify_jwt)
):
    """
    Initialize agent with system prompt and tools
    """
    adapter = ManusMCPAdapter(db)
    result = await adapter.initialize_agent(
        user_id=user_data["user_id"],
        agent_type=request.agent_type,
        agent_name=request.agent_name,
        workspace_id=request.workspace_id,
        tool_schema=request.tool_schema,
        system_prompt=request.system_prompt
    )
    return result

@router.post("/agents/dispatch")
async def dispatch_task(
    request: TaskDispatch,
    db: Session = Depends(get_db),
    user_data: dict = Depends(verify_jwt)
):
    """
    Dispatch task to agent for execution
    """
    adapter = ManusMCPAdapter(db)
    result = await adapter.dispatch_task_to_agent(
        agent_state_id=request.agent_state_id,
        task_description=request.task_description,
        context=request.context
    )
    return result

@router.post("/agents/process-response")
async def process_agent_response(
    request: AgentResponse,
    db: Session = Depends(get_db),
    user_data: dict = Depends(verify_jwt)
):
    """
    Process LLM response and execute tool calls
    """
    adapter = ManusMCPAdapter(db)
    result = await adapter.process_agent_response(
        agent_state_id=request.agent_state_id,
        llm_response=request.llm_response,
        job_id=request.job_id
    )
    return result

@router.get("/agents/{agent_state_id}/state")
async def get_agent_state(
    agent_state_id: str,
    db: Session = Depends(get_db),
    user_data: dict = Depends(verify_jwt)
):
    """
    Get current agent state
    """
    adapter = ManusMCPAdapter(db)
    result = await adapter.get_agent_state(agent_state_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return result

@router.get("/agents/{agent_state_id}/tool-history")
async def get_tool_history(
    agent_state_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    user_data: dict = Depends(verify_jwt)
):
    """
    Get tool call history for agent
    """
    parser = get_execution_parser(db)
    history = await parser.get_tool_call_history(agent_state_id, limit)
    return {"tool_calls": history, "count": len(history)}

@router.get("/sandbox/status")
async def check_sandbox_status(
    db: Session = Depends(get_db),
    user_data: dict = Depends(verify_jwt)
):
    """
    Check sandbox availability
    """
    sandbox = get_sandbox_bridge()
    status = await sandbox.get_sandbox_status()
    return status