from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Dict, Optional
from pydantic import BaseModel
import json
import time
import logging

router = APIRouter(prefix="/im", tags=["WebSocket IM"])


class ConnectionManager:
    """Manages WebSocket connections"""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(json.dumps(message))


manager = ConnectionManager()


class MessageCountResponse(BaseModel):
    remainingCount: int = 0


@router.websocket("/{tempLinkId}")
async def websocket_endpoint(
    websocket: WebSocket,
    tempLinkId: str,
    logType: str = Query(default="default"),
    value: str = Query(default="")
):
    """
    WebSocket endpoint matching frontend: ws://host/im/{tempLinkId}
    Query params: logType, value (Bearer token), tempLinkId
    """
    # Extract token from query params
    token = value.replace("Bearer ", "") if value else ""
    
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    
    # TODO: Validate token here
    # if not validate_token(token):
    #     await websocket.close(code=4003, reason="Invalid token")
    #     return
    
    client_id = tempLinkId
    
    await manager.connect(websocket, client_id)
    
    # Send login response command to trigger frontend callback
    login_resp = {
        "type": "message",
        "command": "COMMAND_LOGIN_RESP",
        "data": {"status": "success", "client_id": client_id, "logType": logType},
        "timeStamp": int(time.time() * 1000)
    }
    await manager.send_personal_message(login_resp, client_id)
    
    logging.info(f"WebSocket connected: {client_id}, logType: {logType}")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                
                # Process and echo message
                response = {
                    "type": message_data.get("type", "message"),
                    "data": message_data.get("data", message_data),
                    "command": message_data.get("command"),
                    "timeStamp": int(time.time() * 1000)
                }
                
                await manager.send_personal_message(response, client_id)
                
            except json.JSONDecodeError:
                error_resp = {
                    "type": "error",
                    "data": "Invalid JSON format",
                    "timeStamp": int(time.time() * 1000)
                }
                await manager.send_personal_message(error_resp, client_id)
                
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected: {client_id}")
        manager.disconnect(client_id)
        
        # Send close message to match frontend behavior
        close_msg = {
            "type": "close",
            "data": "socket已断开连接",
            "timeStamp": int(time.time() * 1000)
        }


@router.get("/message/count", response_model=MessageCountResponse)
async def get_message_count():
    """
    REST endpoint to get remaining message count
    Matches frontend: messageSocketMsg.remainingCount
    """
    # TODO: Implement actual count logic from database
    return MessageCountResponse(remainingCount=0)


@router.post("/message/count", response_model=MessageCountResponse)
async def update_message_count(count: int = Query(default=0)):
    """
    REST endpoint to update remaining message count
    Matches frontend: setStore({name:'remainingCount',content:data})
    """
    # TODO: Implement actual update logic with database persistence
    return MessageCountResponse(remainingCount=count)
