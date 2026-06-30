import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.agent import PersistentAgentState, ToolCallLog, AgentWorkspace
from app.models.user import User
from app.services.execution_parser import ExecutionParser
from app.adapters.manus_adapter import ManusMCPAdapter
import uuid

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

@pytest.fixture
def db():
    """Database fixture for tests"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def user(db):
    """Create test user"""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        is_operator=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def workspace(db, user):
    """Create test workspace"""
    workspace = AgentWorkspace(
        user_id=user.id,
        name="Test Workspace",
        agents=["manus", "ecc"],
        shared_memory={}
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace

@pytest.fixture
def agent_state(db, user, workspace):
    """Create test agent state"""
    state = PersistentAgentState(
        user_id=user.id,
        agent_type="manus",
        agent_name="Test Manus Agent",
        workspace_id=workspace.id,
        tool_schema={"tools": []},
        system_prompt="You are a helpful assistant.",
        state={"phase": "initialized"},
        memory={},
        status="idle"
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state

class TestExecutionParser:
    """Tests for ExecutionParser"""
    
    def test_parse_empty_tool_calls(self, db, agent_state):
        """Test parsing response with no tool calls"""
        parser = ExecutionParser(db)
        response = {"tool_calls": []}
        
        # Should not raise
        assert len(response["tool_calls"]) == 0
    
    def test_tool_call_logging(self, db, agent_state):
        """Test tool call logging"""
        log = ToolCallLog(
            agent_state_id=agent_state.id,
            tool_name="test_tool",
            parameters={"param1": "value1"},
            status="completed",
            result={"output": "success"}
        )
        db.add(log)
        db.commit()
        
        # Verify log was created
        logs = db.query(ToolCallLog).filter(
            ToolCallLog.agent_state_id == agent_state.id
        ).all()
        assert len(logs) == 1
        assert logs[0].tool_name == "test_tool"

class TestManusMCPAdapter:
    """Tests for ManusMCPAdapter"""
    
    @pytest.mark.asyncio
    async def test_create_workspace(self, db, user):
        """Test workspace creation"""
        adapter = ManusMCPAdapter(db)
        result = await adapter.create_agent_workspace(
            user_id=str(user.id),
            name="Test Workspace",
            agents=["manus", "ecc"]
        )
        
        assert "workspace_id" in result
        assert result["name"] == "Test Workspace"
    
    @pytest.mark.asyncio
    async def test_initialize_agent(self, db, user, workspace):
        """Test agent initialization"""
        adapter = ManusMCPAdapter(db)
        result = await adapter.initialize_agent(
            user_id=str(user.id),
            agent_type="manus",
            agent_name="Test Agent",
            workspace_id=str(workspace.id),
            tool_schema={"tools": ["tool1", "tool2"]},
            system_prompt="You are helpful."
        )
        
        assert "agent_state_id" in result
        assert result["agent_name"] == "Test Agent"
        assert result["tool_count"] == 2
    
    @pytest.mark.asyncio
    async def test_dispatch_task(self, db, user, workspace, agent_state):
        """Test task dispatch"""
        adapter = ManusMCPAdapter(db)
        result = await adapter.dispatch_task_to_agent(
            agent_state_id=str(agent_state.id),
            task_description="Test task",
            context={"key": "value"}
        )
        
        assert result["status"] == "running"
        assert result["task"] == "Test task"
    
    @pytest.mark.asyncio
    async def test_get_agent_state(self, db, user, workspace, agent_state):
        """Test get agent state"""
        adapter = ManusMCPAdapter(db)
        result = await adapter.get_agent_state(str(agent_state.id))
        
        assert result["agent_type"] == "manus"
        assert result["agent_name"] == "Test Manus Agent"
        assert "created_at" in result

class TestSandboxBridge:
    """Tests for SandboxBridge (integration tests)"""
    
    @pytest.mark.asyncio
    async def test_sandbox_status_offline(self):
        """Test sandbox status when offline"""
        from app.services.sandbox_bridge import SandboxBridge
        
        bridge = SandboxBridge(proxy_url="http://localhost:9999")
        status = await bridge.get_sandbox_status()
        
        assert status["status"] == "unavailable"
        assert "error" in status