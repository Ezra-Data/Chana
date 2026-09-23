"""
Smart Campus Companion - WebSocket Real-Time Integration Test.
Validates:
1. WebSocket authentication via query param token
2. Ping / Pong heartbeat
3. Real-time broadcast on ticket creation, update, and new messages
"""

import asyncio
import json
import httpx
import websockets

BASE_HTTP = "http://127.0.0.1:8000"
BASE_WS = "ws://127.0.0.1:8000/ws"

async def test_websocket_flow():
    http_client = httpx.AsyncClient(base_url=BASE_HTTP, timeout=10.0)

    # 1. Login student & agent
    res = await http_client.post("/api/auth/login", json={"email": "student@campus.edu", "password": "student123"})
    student_token = res.json()["access_token"]

    res = await http_client.post("/api/auth/login", json={"email": "agent@campus.edu", "password": "agent123"})
    agent_token = res.json()["access_token"]

    print("Tokens retrieved for student and agent.")

    # 2. Connect Student WebSocket
    async with websockets.connect(f"{BASE_WS}?token={student_token}") as student_ws:
        print("Student WebSocket connected successfully.")

        # Test Ping/Pong
        await student_ws.send("ping")
        resp = await asyncio.wait_for(student_ws.recv(), timeout=5.0)
        data = json.loads(resp)
        assert data.get("event") == "pong"
        print("PASS: WebSocket Ping -> Pong verified!")

        # 3. Connect Agent WebSocket
        async with websockets.connect(f"{BASE_WS}?token={agent_token}") as agent_ws:
            print("Agent WebSocket connected successfully.")

            # Create ticket via REST API
            ticket_res = await http_client.post(
                "/api/tickets",
                json={
                    "subject": "WS Test Ticket",
                    "description": "Testing real-time broadcast via WebSocket",
                    "category": "academic",
                },
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert ticket_res.status_code == 201
            ticket_data = ticket_res.json()
            ticket_id = ticket_data["id"]
            print(f"Ticket created: ID {ticket_id}, tracking {ticket_data['tracking_id']}")

            # Agent should receive 'ticket:new' broadcast event
            agent_msg = await asyncio.wait_for(agent_ws.recv(), timeout=5.0)
            agent_evt = json.loads(agent_msg)
            print("PASS: Agent received real-time event:", agent_evt.get("event"))
            assert agent_evt.get("event") == "ticket:new"
            assert agent_evt["data"]["ticket_id"] == ticket_id

            # Agent claims ticket
            claim_res = await http_client.patch(
                f"/api/tickets/{ticket_id}/claim",
                headers={"Authorization": f"Bearer {agent_token}"},
            )
            assert claim_res.status_code == 200

            # Student should receive 'ticket:update'
            student_msg = await asyncio.wait_for(student_ws.recv(), timeout=5.0)
            student_evt = json.loads(student_msg)
            print("PASS: Student received real-time claim update:", student_evt.get("event"))
            assert student_evt.get("event") == "ticket:update"

            # Agent sends message
            msg_res = await http_client.post(
                f"/api/tickets/{ticket_id}/messages",
                json={"message": "Hello from agent in real-time test!"},
                headers={"Authorization": f"Bearer {agent_token}"},
            )
            assert msg_res.status_code == 200

            # Student should receive 'ticket:message'
            student_msg2 = await asyncio.wait_for(student_ws.recv(), timeout=5.0)
            student_evt2 = json.loads(student_msg2)
            print("PASS: Student received real-time message:", student_evt2.get("event"), student_evt2["data"]["message"])
            assert student_evt2.get("event") == "ticket:message"

    print("\n" + "=" * 60)
    print("ALL WEBSOCKET TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_websocket_flow())
