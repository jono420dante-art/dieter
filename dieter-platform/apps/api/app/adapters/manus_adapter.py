import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.agent import PersistentAgentState, AgentWorkspace
from app.services.execution_parser import ExecutionParser
import uuid
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ManusMCPAdapter:
    """Adapter for Manus Agent Hub → DIETER integration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = ExecutionParser(db)
    
    async def create_agent_workspace(
        self,
        user_id: str,
        name: str,
        agents: list
    ) -> Dict[str, Any]:
        """
        Create workspace for agent collaboration
        """
        workspace = AgentWorkspace(
            user_id=uuid.UUID(user_id),
            name=name,
            agents=agents,
            shared_memory={},
            workflow={}
        )
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        
        logger.info(f"Created workspace: {workspace.id}")
        
        return {
            "workspace_id": str(workspace.id),
            "name": name,
            "agents": agents
        }
    
    async def initialize_agent(
        self,
        user_id: str,
        agent_type: str,
        agent_name: str,
        workspace_id: str,
        tool_schema: Dict[str, Any],
        system_prompt: str
    ) -> Dict[str, Any]:
        """
        Initialize agent with system prompt and tools
        """
        agent_state = PersistentAgentState(
            user_id=uuid.UUID(user_id),
            agent_type=agent_type,
            agent_name=agent_name,
            workspace_id=uuid.UUID(workspace_id),
            tool_schema=tool_schema,
            system_prompt=system_prompt,
            state={"phase": "initialized"},
            memory={},
            status="idle"
        )
        self.db.add(agent_state)
        self.db.commit()
        self.db.refresh(agent_state)
        
        logger.info(f"Initialized agent: {agent_name} ({agent_state.id})")
        
        return {
            "agent_state_id": str(agent_state.id),
            "agent_type": agent_type,
            "agent_name": agent_name,
            "status": "initialized",
            "tool_count": len(tool_schema.get("tools", []))
        }
    
    async def dispatch_task_to_agent(
        self,
        agent_state_id: str,
        task_description: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Dispatch task to agent for execution
        """
        agent_state = self.db.query(PersistentAgentState).filter(
            PersistentAgentState.id == uuid.UUID(agent_state_id)
        ).first()
        
        if not agent_state:
            return {"error": "Agent not found"}
        
        # Update agent state
        agent_state.status = "running"
        agent_state.started_at = datetime.utcnow()
        agent_state.memory = {
            **agent_state.memory,
            "current_task": task_description,
            "context": context or {}
        }
        self.db.commit()
        
        logger.info(f"Task dispatched to agent: {task_description[:50]}...")
        
        return {
            "agent_state_id": agent_state_id,
            "status": "running",
            "task": task_description,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def process_agent_response(
        self,
        agent_state_id: str,
        llm_response: Dict[str, Any],
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process LLM response and execute tool calls
        """
        # Parse and execute tools
        result = await self.parser.parse_agent_response(
            agent_state_id=agent_state_id,
            agent_response=llm_response,
            job_id=job_id
        )
        
        # Update agent state with execution results
        agent_state = self.db.query(PersistentAgentState).filter(
            PersistentAgentState.id == uuid.UUID(agent_state_id)
        ).first()
        
        if agent_state:
            agent_state.memory["last_execution"] = result
            agent_state.total_tokens_used += llm_response.get("usage", {}).get("total_tokens", 0)
            self.db.commit()
        
        return result
    
    async def get_agent_state(
        self,
        agent_state_id: str
    ) -> Dict[str, Any]:
        """
        Get current agent state
        """
        agent_state = self.db.query(PersistentAgentState).filter(
            PersistentAgentState.id == uuid.UUID(agent_state_id)
        ).first()
        
        if not agent_state:
            return {"error": "Agent not found"}
        
        return {
            "agent_state_id": str(agent_state.id),
            "agent_type": agent_state.agent_type,
            "agent_name": agent_state.agent_name,
            "status": agent_state.status,
            "memory": agent_state.memory,
            "state": agent_state.state,
            "execution_count": agent_state.execution_count,
            "total_tokens_used": agent_state.total_tokens_used,
            "created_at": agent_state.created_at.isoformat(),
            "updated_at": agent_state.updated_at.isoformat()
        }

class ECCSubagentAdapter:
    """Adapter for ECC Subagents → DIETER"""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = ExecutionParser(db)
    
    # Similar implementation to ManusMCPAdapter
    # Routes ECC subagent calls (planner, architect, reviewer, etc.)

class LangflowAdapter:
    """Adapter for Langflow Visual Builder → DIETER"""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = ExecutionParser(db)
    
    # Routes Langflow workflow execution to DIETER job system

class APEXAdapter:
    """Adapter for APEX Trading Engine → DIETER"""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = ExecutionParser(db)
    
    # Routes trading signals and portfolio actions to DIETER jobs