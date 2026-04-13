"""
STOMP WebSocket controller for real-time scheduling solution updates.
This provides WebSocket support for live schedule updates during solving.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import time
import logging

router = APIRouter(prefix="/ws", tags=["WebSocket STOMP"])


class StompConnectionManager:
    """Manages STOMP WebSocket connections and subscriptions"""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # topic -> set of client_ids
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.subscriptions.setdefault("solution", set()).add(client_id)
        logging.info(f"STOMP connected: {client_id}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        for topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)
        logging.info(f"STOMP disconnected: {client_id}")
    
    async def send_to_topic(self, topic: str, message: dict):
        """Send message to all subscribers of a topic"""
        clients = self.subscriptions.get(topic, set())
        message_text = json.dumps(message)
        
        disconnected = []
        for client_id in clients:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_text(message_text)
                except Exception as e:
                    logging.error(f"Error sending to {client_id}: {e}")
                    disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send raw text message to specific client"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)


manager = StompConnectionManager()


@router.websocket("/")
async def stomp_websocket(websocket: WebSocket):
    """
    STOMP WebSocket endpoint for real-time scheduling updates.
    Frontend connects via SockJS to /ws and subscribes to /topic/solution
    """
    client_id = f"client_{id(websocket)}_{int(time.time())}"
    
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive STOMP frames
            data = await websocket.receive_text()
            
            try:
                # Parse STOMP frame
                frame = parse_stomp_frame(data)
                command = frame.get("command", "")
                
                if command == "CONNECT":
                    # Respond with CONNECTED
                    connected_frame = build_stomp_frame("CONNECTED", {
                        "version": "1.1",
                        "heart-beat": "0,0"
                    })
                    await manager.send_personal_message(connected_frame, client_id)
                
                elif command == "SUBSCRIBE":
                    # Extract destination topic
                    destination = frame.get("headers", {}).get("destination", "")
                    if destination.startswith("/topic/"):
                        topic = destination.replace("/topic/", "")
                        manager.subscriptions.setdefault(topic, set()).add(client_id)
                        logging.info(f"Client {client_id} subscribed to {topic}")
                
                elif command == "UNSUBSCRIBE":
                    destination = frame.get("headers", {}).get("destination", "")
                    if destination.startswith("/topic/"):
                        topic = destination.replace("/topic/", "")
                        manager.subscriptions.get(topic, set()).discard(client_id)
                
                elif command == "SEND":
                    # Echo message back (or process as needed)
                    destination = frame.get("headers", {}).get("destination", "")
                    body = frame.get("body", "")
                    if body:
                        await manager.send_personal_message(body, client_id)
                
                elif command == "DISCONNECT":
                    manager.disconnect(client_id)
                    break
                    
            except Exception as e:
                logging.error(f"Error processing STOMP frame: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logging.error(f"STOMP WebSocket error: {e}")
        manager.disconnect(client_id)


def parse_stomp_frame(data: str) -> dict:
    """Parse STOMP frame from text"""
    lines = data.strip().split('\n')
    if not lines:
        return {"command": "", "headers": {}, "body": ""}
    
    command = lines[0].strip()
    headers = {}
    body_start = 0
    
    for i, line in enumerate(lines[1:], 1):
        line = line.strip()
        if line == '':
            body_start = i + 1
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    body = '\n'.join(lines[body_start:]) if body_start < len(lines) else ''
    # Remove trailing null byte if present
    if body.endswith('\x00'):
        body = body[:-1]
    
    return {
        "command": command,
        "headers": headers,
        "body": body.strip()
    }


def build_stomp_frame(command: str, headers: dict = None, body: str = "") -> str:
    """Build STOMP frame as text"""
    lines = [command]
    
    if headers:
        for key, value in headers.items():
            lines.append(f"{key}:{value}")
    
    lines.append('')  # Empty line before body
    
    if body:
        lines.append(body)
    
    lines.append('\x00')  # STOMP frames end with null byte
    
    return '\n'.join(lines)


# Helper function to broadcast solution updates
async def broadcast_solution_update(solution_data: dict):
    """Broadcast solution update to all subscribers of /topic/solution"""
    frame = build_stomp_frame("MESSAGE", {
        "destination": "/topic/solution",
        "content-type": "application/json",
        "subscription": "sub-0"
    }, json.dumps(solution_data))
    
    await manager.send_to_topic("solution", frame)
