import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.llm import generate_response

app = FastAPI(title="Buttler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

def dummy_callback(*args, **kwargs):
    pass

def auto_confirm_tool(tool_name: str, args: dict, permission: str) -> bool:
    # Auto-resolves tool confirmations in the web UI for now. 
    # Can be updated to parse via WebSockets later.
    return True

@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 1 -  Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_text = message_data.get("text", "")

            # 2 - Generate response using LLM
            reply_generator = generate_response(
                user_text,
                confirm_tool=auto_confirm_tool,
                on_state=dummy_callback,
                on_metrics=dummy_callback,
                on_tool_result=dummy_callback,
                print_metrics=False
            )

            # 3 - Stream response back to client
            for chunk in reply_generator:
                if chunk.strip():
                    await websocket.send_json(
                        {
                            "type": "chunk",
                            "content": chunk + " "
                        }
                    )
                    await asyncio.sleep(0) # Yield control to the event loop so messages are sent immediately

            await websocket.send_json(
                {
                    "type": "done"
                }
            )
    except WebSocketDisconnect:
        print("Client disconnected")