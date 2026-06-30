from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.database import Base

class PersistentAgentState(Base):
    """Persistent state for any autonomous agent (Manus, ECC, Langflow, APEX)"""
    __tablename__ = "persistent_agent_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(String(50), nullable=False, index=True)  # manus, ecc, langflow, apex
    agent_name = Column(String(100))
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # State management
    state = Column(JSON)  # Current execution state
    memory = Column(JSON)  # Agent memory/context
    tool_schema = Column(JSON)  # Available tools for this agent
    system_prompt = Column(String(8000))  # System prompt template
    
    # Execution tracking
    status = Column(String(50), default="idle")  # idle, running, paused, completed, error
    error_message = Column(String(1000))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Execution info
    execution_count = Column(Integer, default=0)
    last_tool_call = Column(JSON)
    total_tokens_used = Column(Integer, default=0)

class ToolCallLog(Base):
    """Log of all tool calls for audit and replay"""
    __tablename__ = "tool_call_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_state_id = Column(UUID(as_uuid=True), ForeignKey("persistent_agent_states.id"), index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    
    # Tool call details
    tool_name = Column(String(100), nullable=False, index=True)
    tool_category = Column(String(50))  # cli, browser, mcp, sandbox, db
    parameters = Column(JSON)
    result = Column(JSON)
    error = Column(String(1000))
    
    # Execution tracking
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)

class AgentWorkspace(Base):
    """Workspace for multi-agent collaboration"""
    __tablename__ = "agent_workspaces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    
    # Workspace config
    agents = Column(JSON)  # List of active agents in workspace
    shared_memory = Column(JSON)  # Shared context across agents
    workflow = Column(JSON)  # Workflow definition
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)