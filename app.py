# app.py
import asyncio
import logging
from typing import Dict, Any, Optional, List
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import time
from datetime import datetime

# Import local modules
import config
from runner import create_default_runner, BankingBotRunner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the FastAPI app
app = FastAPI(
    title="Banking Bot API",
    description="API for interacting with Banking Assistant, an intelligent agent-based system for banking operations.",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.API_CONFIG["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create the banking bot runner
runner = create_default_runner()

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Mount static files if the directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
else:
    logger.warning("Static directory not found. UI features will be limited.")
    templates = None

# --- Pydantic Models for Request/Response ---

class MessageRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class SessionRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    initial_state: Optional[Dict[str, Any]] = None

class StateUpdateRequest(BaseModel):
    user_id: str
    session_id: str
    state_updates: Dict[str, Any]

class UserSessionRequest(BaseModel):
    user_id: str

# --- Helper Functions ---

def get_session_key(request: Request) -> str:
    """Generate a deterministic session key from the request."""
    # In production, you'd likely use authentication to get user ID
    user_agent = request.headers.get("user-agent", "unknown")
    ip = request.client.host if request.client else "unknown"
    return f"{ip}_{user_agent}"

def get_or_create_user_id(request: Request = None, user_id: str = None) -> str:
    """Get user ID from request/parameter or generate a new one."""
    if user_id:
        return user_id
    elif request:
        # Generate deterministic user ID from request info
        return f"user_{hash(get_session_key(request)) % 10000000}"
    else:
        return f"user_{uuid.uuid4().hex[:8]}"

# --- Routes ---

@app.get("/")
async def root():
    """Root endpoint - provides basic info about the API."""
    return {
        "name": "Banking Bot API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "POST /api/chat": "Send a message to the banking assistant",
            "POST /api/sessions": "Create a new session",
            "GET /api/sessions/{user_id}/{session_id}": "Get session info",
            "PUT /api/sessions/{user_id}/{session_id}": "Update session state",
            "GET /api/sessions/{user_id}": "List user sessions",
            "DELETE /api/sessions/{user_id}/{session_id}": "Delete a session",
            "GET /ui": "Web interface"
        }
    }

@app.post(f"{config.API_CONFIG['api_prefix']}/chat")
async def chat(request: MessageRequest):
    """
    Send a message to the Banking Bot and get a response.
    
    If user_id and session_id are not provided, they will be generated.
    """
    user_id = get_or_create_user_id(user_id=request.user_id)
    session_id = request.session_id or f"session_{uuid.uuid4().hex}"
    
    try:
        response = await runner.process_message(
            user_id=user_id,
            session_id=session_id,
            message=request.message,
            context=request.context
        )
        
        # Add timing information
        response["timestamp"] = datetime.now().isoformat()
        response["user_id"] = user_id
        response["session_id"] = session_id
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post(f"{config.API_CONFIG['api_prefix']}/sessions")
async def create_session(request: SessionRequest):
    """Create a new session for a user."""
    try:
        user_id = get_or_create_user_id(user_id=request.user_id)
        
        session_info = await runner.create_session(
            user_id=user_id,
            session_id=request.session_id,
            initial_state=request.initial_state
        )
        
        return session_info
        
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@app.get(f"{config.API_CONFIG['api_prefix']}/sessions/{{user_id}}/{{session_id}}")
async def get_session(user_id: str, session_id: str):
    """Get information about a specific session."""
    try:
        session_info = await runner.get_session_info(
            user_id=user_id,
            session_id=session_id
        )
        
        if not session_info:
            raise HTTPException(status_code=404, detail=f"Session not found: {user_id}/{session_id}")
            
        return session_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting session: {str(e)}")

@app.put(f"{config.API_CONFIG['api_prefix']}/sessions/{{user_id}}/{{session_id}}")
async def update_session(user_id: str, session_id: str, request: StateUpdateRequest):
    """Update session state."""
    try:
        if request.user_id != user_id or request.session_id != session_id:
            raise HTTPException(status_code=400, detail="User ID and session ID in URL must match request body")
            
        updated_session = await runner.update_session_state(
            user_id=user_id,
            session_id=session_id,
            state_updates=request.state_updates
        )
        
        if not updated_session:
            raise HTTPException(status_code=404, detail=f"Session not found: {user_id}/{session_id}")
            
        return updated_session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating session: {str(e)}")

@app.get(f"{config.API_CONFIG['api_prefix']}/sessions/{{user_id}}")
async def list_sessions(user_id: str):
    """List all sessions for a user."""
    try:
        sessions = await runner.list_user_sessions(user_id=user_id)
        return {"user_id": user_id, "sessions": sessions}
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")

@app.delete(f"{config.API_CONFIG['api_prefix']}/sessions/{{user_id}}/{{session_id}}")
async def delete_session(user_id: str, session_id: str):
    """Delete a session."""
    try:
        deleted = await runner.delete_session(
            user_id=user_id,
            session_id=session_id
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Session not found: {user_id}/{session_id}")
            
        return {"status": "success", "message": f"Session {user_id}/{session_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

# --- UI Routes ---

@app.get("/ui")
async def ui_home(request: Request):
    """Serve the web UI for the Banking Bot."""
    if not templates:
        return JSONResponse(
            status_code=404,
            content={"message": "UI not available. Templates directory not found."}
        )
    
    user_id = get_or_create_user_id(request)
    
    # Create a default session if none exists
    try:
        sessions = await runner.list_user_sessions(user_id)
        if not sessions:
            session_info = await runner.create_session(
                user_id=user_id,
                initial_state={"source": "web_ui"}
            )
            session_id = session_info["session_id"]
        else:
            # Use the most recent session
            session_id = sessions[0]["session_id"]
    except Exception as e:
        logger.error(f"Error setting up UI session: {e}", exc_info=True)
        session_id = f"session_{uuid.uuid4().hex}"
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "user_id": user_id,
            "session_id": session_id,
            "welcome_message": config.BANKING_CONFIG["welcome_message"]
        }
    )

# --- WebSocket for Real-time Chat ---

@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    
    try:
        # Check if session exists or create it
        session_info = await runner.get_session_info(user_id, session_id)
        if not session_info:
            await runner.create_session(user_id, session_id, {"source": "websocket"})
        
        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "content": config.BANKING_CONFIG["welcome_message"],
            "user_id": user_id,
            "session_id": session_id
        })
        
        # Main conversation loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if "message" not in data:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format. Missing 'message' field."
                })
                continue
            
            # Process message
            response = await runner.process_message(
                user_id=user_id,
                session_id=session_id,
                message=data["message"],
                context=data.get("context")
            )
            
            # Send response back to client
            await websocket.send_json({
                "type": "response",
                "content": response["response_text"],
                "full_response": response,
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {user_id}/{session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"An error occurred: {str(e)}"
            })
        except:
            pass  # Client likely already disconnected

# --- Health Check ---

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "app_name": config.APP_NAME,
            "session_type": config.SESSION_TYPE
        }
    }

# --- Main Entry Point ---

def create_sample_templates():
    """Create simple templates for UI if they don't exist."""
    if not os.path.exists("templates"):
        os.makedirs("templates", exist_ok=True)
    
    # Create a simple index.html if it doesn't exist
    index_path = os.path.join("templates", "index.html")
    if not os.path.exists(index_path):
        with open(index_path, "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Banking Bot</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; max-width: 800px; margin: 0 auto; }
        .chat-container { border: 1px solid #ddd; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; height: 80vh; }
        .chat-header { background-color: #0066cc; color: white; padding: 10px; text-align: center; }
        .messages { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 10px; }
        .message { padding: 10px; border-radius: 18px; max-width: 70%; }
        .user { align-self: flex-end; background-color: #0084ff; color: white; }
        .bot { align-self: flex-start; background-color: #e9e9eb; color: black; }
        .input-area { display: flex; padding: 10px; border-top: 1px solid #ddd; }
        #message-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        #send-button { background-color: #0066cc; color: white; border: none; padding: 10px 15px; margin-left: 10px; border-radius: 4px; cursor: pointer; }
        .session-info { font-size: 0.8em; color: #666; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h2>Banking Assistant</h2>
        </div>
        <div class="messages" id="messages"></div>
        <div class="input-area">
            <input type="text" id="message-input" placeholder="Type your message here..." />
            <button id="send-button">Send</button>
        </div>
    </div>
    <div class="session-info">
        User ID: <span id="user-id">{{ user_id }}</span> | 
        Session ID: <span id="session-id">{{ session_id }}</span>
    </div>

    <script>
        const userId = "{{ user_id }}";
        const sessionId = "{{ session_id }}";
        const messagesContainer = document.getElementById('messages');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        let ws;
        
        // Add welcome message
        const welcomeMsg = "{{ welcome_message }}";
        addBotMessage(welcomeMsg);
        
        // Initialize WebSocket
        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws/${userId}/${sessionId}`);
            
            ws.onopen = function() {
                console.log('WebSocket connected');
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'response') {
                    addBotMessage(data.content);
                } else if (data.type === 'error') {
                    addBotMessage('Error: ' + data.content);
                } else if (data.type === 'welcome') {
                    // Already added welcome message
                }
            };
            
            ws.onclose = function() {
                console.log('WebSocket disconnected');
                // Try to reconnect after a delay
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        // Send message
        function sendMessage() {
            const text = messageInput.value.trim();
            if (!text) return;
            
            addUserMessage(text);
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ message: text }));
            } else {
                // Fallback to REST API if WebSocket isn't connected
                fetch(`${window.location.origin}/api/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, user_id: userId, session_id: sessionId })
                })
                .then(response => response.json())
                .then(data => {
                    addBotMessage(data.response_text);
                })
                .catch(error => {
                    console.error('Error:', error);
                    addBotMessage('Sorry, there was an error processing your request.');
                });
            }
            
            messageInput.value = '';
        }
        
        // Add a user message to the chat
        function addUserMessage(text) {
            const message = document.createElement('div');
            message.classList.add('message', 'user');
            message.textContent = text;
            messagesContainer.appendChild(message);
            scrollToBottom();
        }
        
        // Add a bot message to the chat
        function addBotMessage(text) {
            const message = document.createElement('div');
            message.classList.add('message', 'bot');
            message.textContent = text;
            messagesContainer.appendChild(message);
            scrollToBottom();
        }
        
        // Scroll to the bottom of the messages container
        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        // Event listeners
        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Connect WebSocket when the page loads
        connectWebSocket();
    </script>
</body>
</html>
            """)
        logger.info(f"Created sample template: {index_path}")

if __name__ == "__main__":
    # Create sample templates for UI
    create_sample_templates()
    
    # Start the API server
    uvicorn.run(
        "app:app", 
        host=config.API_CONFIG["host"], 
        port=config.API_CONFIG["port"],
        reload=config.API_CONFIG["debug"]
    )