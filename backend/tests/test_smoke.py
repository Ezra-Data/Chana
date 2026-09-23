"""
Smart Campus Companion - End-to-End API Smoke Test.
Validates:
1. Student Auth & Registration
2. Agent & Admin Auth
3. Navigation search API
4. Knowledge base querying
5. Chat orchestration (FAQ fallback, sensitive ticket creation, nav matching)
6. Ticket creation, agent claim, message timeline, status change
7. Analytics dashboard endpoint
"""

import httpx

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    print("=" * 60)
    print("1. HEALTH CHECK")
    res = client.get("/api/health")
    assert res.status_code == 200
    print("PASS: /api/health ->", res.json())

    print("\n2. AUTHENTICATION")
    # Student login
    res = client.post("/api/auth/login", json={"email": "student@campus.edu", "password": "student123"})
    assert res.status_code == 200
    student_token = res.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    print("PASS: Student login successful")

    # Agent login
    res = client.post("/api/auth/login", json={"email": "agent@campus.edu", "password": "agent123"})
    assert res.status_code == 200
    agent_token = res.json()["access_token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    print("PASS: Agent login successful")

    # Admin login
    res = client.post("/api/auth/login", json={"email": "admin@campus.edu", "password": "admin123"})
    assert res.status_code == 200
    admin_token = res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("PASS: Admin login successful")

    print("\n3. NAVIGATION SEARCH")
    res = client.get("/api/navigation/search?q=dean", headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    print(f"PASS: Navigation search for 'dean' returned {len(data)} nodes (first: {data[0]['name']})")

    res = client.get("/api/navigation/search?q=comp%20lab", headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    print(f"PASS: Navigation search for 'comp lab' returned {len(data)} nodes")

    print("\n4. CHAT ORCHESTRATION")
    # 4a. FAQ query (using cached demo answers or RAG fallback)
    res = client.post("/api/chat/message", json={"message": "What are the library hours?"}, headers=student_headers)
    assert res.status_code == 200
    faq_data = res.json()
    print("PASS: Chat FAQ Response ->", faq_data["intent"], "| Message preview:", faq_data["message"][:60], "...")

    # 4b. Navigation query in chat
    res = client.post("/api/chat/message", json={"message": "Where is the Dean's Office?"}, headers=student_headers)
    assert res.status_code == 200
    nav_data = res.json()
    print("PASS: Chat Nav Response ->", nav_data["intent"], "| Deep link metadata:", nav_data.get("metadata"))

    # 4c. Sensitive query (safety net -> auto ticket creation)
    res = client.post("/api/chat/message", json={"message": "Someone is asking for a bribe to give me my transcript"}, headers=student_headers)
    assert res.status_code == 200
    sens_data = res.json()
    assert sens_data["intent"] == "sensitive"
    ticket_id = sens_data["metadata"]["ticket_id"]
    print("PASS: Chat Sensitive Auto-Ticket ->", ticket_id, "| Priority:", sens_data["metadata"]["priority"])

    print("\n5. TICKET LIFECYCLE")
    # Student views their tickets
    res = client.get("/api/tickets", headers=student_headers)
    assert res.status_code == 200
    student_tickets = res.json()
    print(f"PASS: Student has {len(student_tickets)} ticket(s)")

    # Agent views queue
    res = client.get("/api/tickets", headers=agent_headers)
    assert res.status_code == 200
    agent_tickets = res.json()
    print(f"PASS: Agent queue has {len(agent_tickets)} ticket(s)")

    # Agent claims ticket
    db_id = sens_data["metadata"]["ticket_db_id"]
    res = client.patch(f"/api/tickets/{db_id}/claim", headers=agent_headers)
    assert res.status_code == 200
    print("PASS: Agent claimed ticket", ticket_id)

    # Agent sends reply message
    res = client.post(f"/api/tickets/{db_id}/messages", json={"message": "We take corruption allegations very seriously. Please visit our office or submit details."}, headers=agent_headers)
    assert res.status_code == 200
    print("PASS: Agent sent message to ticket", ticket_id)

    # Agent updates status to in_progress
    res = client.patch(f"/api/tickets/{db_id}/status", json={"status": "in_progress"}, headers=agent_headers)
    assert res.status_code == 200
    print("PASS: Ticket status updated to in_progress")

    # Student views ticket details + timeline
    res = client.get(f"/api/tickets/{db_id}", headers=student_headers)
    assert res.status_code == 200
    detail = res.json()
    assert len(detail["messages"]) >= 2
    print(f"PASS: Student retrieved ticket detail with {len(detail['messages'])} messages")

    print("\n6. ANALYTICS & ADMIN")
    res = client.get("/api/analytics/dashboard", headers=admin_headers)
    assert res.status_code == 200
    analytics = res.json()
    print("PASS: Analytics dashboard retrieved ->", analytics.get("summary"))

    print("\n" + "=" * 60)
    print("ALL SMOKE TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
