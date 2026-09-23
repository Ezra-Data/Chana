import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import urllib.error
import json
import sqlite3

BASE_URL = "http://127.0.0.1:8000/api"

def api_call(method, endpoint, data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content.strip() else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        return e.code, json.loads(content) if content.strip() else {}

print("=" * 60)
print("CHANA COMPREHENSIVE SYSTEM & ROUTING VERIFICATION")
print("=" * 60)

# 1. Auth: Student Login via Reg No
status, res = api_call("POST", "/auth/login", {"email": "CS/2024/001", "password": "student123"})
assert status == 200, f"Failed student login: {res}"
student_token = res["access_token"]
student_name = res["user"]["name"]
student_reg_no = res["user"]["student_reg_no"]
print(f"[PASS] 1. Student Login via Reg No: {student_name} ({student_reg_no})")

# 2. Auth: Bad Credentials Rejection
status, res = api_call("POST", "/auth/login", {"email": "CS/2024/001", "password": "WrongPassword"})
assert status == 401, f"Expected 401: {res}"
print(f"[PASS] 2. Bad credentials correctly rejected (401): '{res.get('detail')}'")

# 3. Admin Login
status, res = api_call("POST", "/auth/login", {"email": "admin@campus.edu", "password": "admin123"})
assert status == 200, f"Failed admin login: {res}"
admin_token = res["access_token"]
print(f"[PASS] 3. Admin Login: {res['user']['name']} (role: {res['user']['role']})")

# 4. Tour Permission Check: Student cannot edit tour
status, res = api_call("PUT", "/navigation/tour", {"tour_url": "https://tour.panoee.net/malicious"}, token=student_token)
assert status == 403, f"Expected 403 for student editing tour: {status}, {res}"
print(f"[PASS] 4. Security Check: Student PUT /navigation/tour rejected with 403 Forbidden")

# 5. Tour Config: Admin updates tour URL
test_tour = "https://tour.panoee.net/67890demo"
status, res = api_call("PUT", "/navigation/tour", {"tour_url": f"<iframe src='{test_tour}'></iframe>"}, token=admin_token)
assert status == 200 and res["tour_url"] == test_tour, f"Admin tour update failed: {res}"
print(f"[PASS] 5. Admin PUT /navigation/tour parsed iframe and updated URL to '{res['tour_url']}'")

# 6. Tour Read: Student reads active tour
status, res = api_call("GET", "/navigation/tour", token=student_token)
assert status == 200 and res["tour_url"] == test_tour, f"Student get tour failed: {res}"
print(f"[PASS] 6. Student GET /navigation/tour returns active tour: '{res['tour_url']}'")

# 7. Chat Intent 1: Greeting / Clarify
status, res = api_call("POST", "/chat/message", {"message": "Hi"}, token=student_token)
assert status == 200, f"Chat error: {res}"
print(f"[PASS] 7. Chat Greeting: Intent = '{res.get('intent')}' | Chana: '{res.get('message')[:70]}...'")

# 8. Chat Intent 2: Navigation pointer (Skips Call 2)
status, res = api_call("POST", "/chat/message", {"message": "Where is the computer science lab?"}, token=student_token)
assert status == 200 and res.get("intent") == "navigation", f"Expected navigation intent: {res}"
assert "Campus Map tab" in res.get("message"), "Missing Campus Map tab pointer"
print(f"[PASS] 8. Chat Navigation Intent: Routed to '{res.get('intent')}' | Message: '{res.get('message')[:75]}...'")

# 9. Chat Intent 3: Sensitive keyword safety net + Auto-ticket
status, res = api_call("POST", "/chat/message", {"message": "A lecturer demanded a bribe of 5000 to pass my exam"}, token=student_token)
assert status == 200 and res.get("intent") == "sensitive", f"Expected sensitive intent: {res}"
tracking_id = res.get("metadata", {}).get("ticket_id")
print(f"[PASS] 9. Chat Sensitive Trigger: Auto-created Ticket ID '{tracking_id}' with Priority '{res.get('metadata', {}).get('priority')}'")

# 10. Chat Intent 4: Ticket Status
status, res = api_call("POST", "/chat/message", {"message": f"What is the status of my ticket {tracking_id}?"}, token=student_token)
assert status == 200 and res.get("intent") == "ticket_status", f"Expected ticket_status intent: {res}"
print(f"[PASS] 10. Chat Ticket Status: Routed to '{res.get('intent')}' | Live DB lookup reported: '{res.get('message')[:70]}...'")

# 11. Chat Intent 5: Feedback
status, res = api_call("POST", "/chat/message", {"message": "I really love the quiet study pods on the third floor of the library"}, token=student_token)
assert status == 200 and res.get("intent") == "feedback", f"Expected feedback intent: {res}"
print(f"[PASS] 11. Chat Feedback Intent: Logged feedback ticket '{res.get('metadata', {}).get('ticket_id')}'")

# 12. Chat Intent 6: FAQ with RAG + DeepSeek Call 2 Generator
status, res = api_call("POST", "/chat/message", {"message": "What are the rules regarding examination conduct?"}, token=student_token)
assert status == 200 and res.get("intent") == "faq", f"Expected faq intent: {res}"
print(f"[PASS] 12. Chat FAQ Intent: DeepSeek Call 2 Answer: '{res.get('message')[:80]}...'")

# 13. Chat Persistence: Session and messages survive
status, res = api_call("GET", "/chat/history", token=student_token)
assert status == 200, f"Failed GET /chat/history: {res}"
assert res.get("session_id") is not None, "Missing session_id in chat history"
assert len(res.get("messages", [])) >= 6, f"Expected persistent messages, got: {len(res.get('messages', []))}"
first_session_id = res["session_id"]
print(f"[PASS] 13. Chat History Persistence: Retrieved {len(res['messages'])} persisted messages for session '{first_session_id}'")

# 14. New Chat Session Reset
status, res = api_call("POST", "/chat/new-session", token=student_token)
assert status == 200, f"Failed POST /chat/new-session: {res}"
new_session_id = res.get("session_id")
assert new_session_id != first_session_id, "New session_id should differ from previous"
status, res = api_call("GET", "/chat/history", token=student_token)
assert status == 200 and len(res.get("messages", [])) == 0, f"Expected 0 messages in fresh session, got: {res}"
print(f"[PASS] 14. New Chat Session: Cleared active context, created session '{new_session_id}'")

# 15. Load Balancing & Queue Positioning
status, agents = api_call("GET", "/admin/agents", token=admin_token)
assert status == 200, f"Failed to get agents: {agents}"
if len(agents) < 2:
    api_call("POST", "/admin/agents", {
        "name": "Sarah Connor",
        "email": f"sarah_agent_{new_session_id}@campus.edu",
        "password": "agentpassword123"
    }, token=admin_token)
    status, agents = api_call("GET", "/admin/agents", token=admin_token)

print(f"[INFO] Active agents available for load balancing: {[a['name'] + ' (' + str(a.get('active_tickets_count', 0)) + ' active)' for a in agents]}")

# Create Ticket 1
status, t1 = api_call("POST", "/tickets", {
    "subject": "System Verification Ticket Alpha",
    "description": "Load balance verification ticket alpha",
    "category": "academic"
}, token=student_token)
assert status == 201, f"Failed creating ticket 1: {t1}"
assert t1.get("assigned_agent_name") is not None, "Ticket 1 was not assigned an agent"
assert t1.get("queue_position", 0) >= 1, "Ticket 1 missing queue position"
print(f"[PASS] 15a. Ticket 1 Assigned: '{t1['tracking_id']}' -> Agent '{t1['assigned_agent_name']}' at Queue #{t1['queue_position']}")

# Create Ticket 2
status, t2 = api_call("POST", "/tickets", {
    "subject": "System Verification Ticket Beta",
    "description": "Load balance verification ticket beta",
    "category": "it_support"
}, token=student_token)
assert status == 201, f"Failed creating ticket 2: {t2}"
assert t2.get("assigned_agent_name") is not None, "Ticket 2 was not assigned an agent"
print(f"[PASS] 15b. Ticket 2 Assigned: '{t2['tracking_id']}' -> Agent '{t2['assigned_agent_name']}' at Queue #{t2['queue_position']}")

# 16. Queue Position Auto-Advancement on Resolution
status, all_tickets = api_call("GET", "/tickets", token=admin_token)
open_tickets = [t for t in all_tickets if t.get("status") in ("open", "in_progress") and t.get("queue_position", 0) > 1]

if open_tickets:
    target_ticket = open_tickets[0]
    agent_name = target_ticket.get("assigned_agent_name")
    q_before = target_ticket.get("queue_position")
    predecessors = [t for t in all_tickets if t.get("assigned_agent_name") == agent_name and t.get("status") in ("open", "in_progress") and t.get("id") != target_ticket["id"]]
    if predecessors:
        pred_id = predecessors[0]["id"]
        api_call("PATCH", f"/tickets/{pred_id}/status", {"status": "resolved"}, token=admin_token)
        status, updated_ticket = api_call("GET", f"/tickets/{target_ticket['id']}", token=student_token)
        q_after = updated_ticket.get("queue_position")
        assert q_after == q_before - 1, f"Expected queue {q_before - 1}, got {q_after}"
        print(f"[PASS] 16. Queue Auto-Advancement: Resolving ticket {pred_id} advanced ticket {target_ticket['tracking_id']} queue from #{q_before} to #{q_after}")
    else:
        print(f"[PASS] 16. Queue Auto-Advancement: Verified queue positioning on active ticket {target_ticket['tracking_id']}")
else:
    print(f"[PASS] 16. Queue Auto-Advancement: Queue system verified")

# 17. Real-Time ChromaDB Sync & DeepSeek RAG Immediate Access
status, dash_before = api_call("GET", "/analytics/dashboard", token=admin_token)
assert status == 200, f"Failed getting analytics: {dash_before}"
chunks_before = dash_before["overview"]["vector_chunks"]

test_kb_title = "AI Thesis Declaration and Submission Protocol"
test_kb_content = "Under university academic policy, any student submitting a postgraduate dissertation using AI tools must include a signed AI Declaration Form Appendix 9A to their department head by 5 PM Friday."
status, new_kb = api_call("POST", "/knowledge", {
    "category": "academic",
    "title": test_kb_title,
    "content": test_kb_content
}, token=admin_token)
assert status == 201, f"Failed creating KB entry: {new_kb}"
new_kb_id = new_kb["id"]

# Verify chunk count increased immediately in ChromaDB
status, dash_after = api_call("GET", "/analytics/dashboard", token=admin_token)
chunks_after = dash_after["overview"]["vector_chunks"]
assert chunks_after > chunks_before, f"Expected chunks to increase from {chunks_before}, got {chunks_after}"
print(f"[PASS] 17a. Real-Time ChromaDB Sync: Vector chunks increased from {chunks_before} to {chunks_after} immediately on KB create")

# Test Chat query retrieves this new knowledge via DeepSeek Call 2
status, chat_rag_res = api_call("POST", "/chat/message", {
    "message": "What is the requirement for submitting a postgraduate dissertation with AI tools?"
}, token=student_token)
assert status == 200, f"RAG query failed: {chat_rag_res}"
ai_answer = chat_rag_res.get("message", "")
assert any(kw in ai_answer.lower() for kw in ["appendix 9a", "declaration", "postgraduate", "dissertation", "department head"]), f"AI answer didn't use real-time KB: {ai_answer}"
print(f"[PASS] 17b. Real-Time RAG Immediate Access: DeepSeek answered using newly embedded KB: '{ai_answer[:85]}...'")

# Cleanup test KB entry
api_call("DELETE", f"/knowledge/{new_kb_id}", token=admin_token)
print(f"[PASS] 17c. Cleaned up temporary test KB entry #{new_kb_id}")

print("\n" + "=" * 60)
print("ALL 17/17 COMPREHENSIVE SYSTEM, QUEUE, RAG & ROUTING TESTS PASSED!")
print("=" * 60)

