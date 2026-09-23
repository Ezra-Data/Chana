"""
Smart Campus Companion — Live System Verification Test Suite.

Validates 100% real database-backed functionality:
1. End-to-end student self-registration (name, email, reg no, password) + wrong password rejection
2. Real DeepSeek API outbound call with live response
3. Live Knowledge Base re-embedding (adding unique fact -> chatbot answers it immediately)
4. Confidence-based clarifying question on ambiguous query
5. Sensitive issue auto-escalation (Critical) vs Feedback ticket (Low priority)
6. Live Analytics counters incrementing dynamically from real DB
"""

import sys
import os
import time
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def run_live_verification():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    print("=" * 70)
    print("SMART CAMPUS COMPANION - LIVE SYSTEM VERIFICATION")
    print("=" * 70)

    # ─── 0. Health Check ─────────────────────────────────────────
    res = client.get("/api/health")
    assert res.status_code == 200
    health = res.json()
    print(f"\n[0] HEALTH CHECK: {health['status']}")
    print(f"    DeepSeek Configured: {health.get('deepseek_configured')}")
    assert health.get("deepseek_configured") is True, "DeepSeek API key must be configured in .env!"

    # ─── 1. Student Registration & Auth ───────────────────────────
    print("\n[1] STUDENT SELF-REGISTRATION & AUTHENTICATION")
    test_email = f"alice_{int(time.time())}@campus.edu"
    test_reg = f"CS/2024/{int(time.time()) % 1000:03d}"

    # 1a. Register new student
    reg_payload = {
        "name": "Alice Wanjala",
        "email": test_email,
        "student_reg_no": test_reg,
        "password": "SecurePassword123!",
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["student_reg_no"] == test_reg
    assert reg_data["user"]["role"] == "student"
    new_student_token = reg_data["access_token"]
    new_student_headers = {"Authorization": f"Bearer {new_student_token}"}
    print(f"    [PASS] Student registered: {reg_data['user']['name']} ({test_reg})")

    # 1b. Verify wrong password rejected
    wrong_pwd_res = client.post("/api/auth/login", json={"email": test_email, "password": "WrongPassword!"})
    assert wrong_pwd_res.status_code == 401
    print("    [PASS] Wrong password correctly rejected with 401 Unauthorized")

    # 1c. Log in with admin & agent
    admin_res = client.post("/api/auth/login", json={"email": "admin@campus.edu", "password": "admin123"})
    assert admin_res.status_code == 200
    admin_token = admin_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    agent_res = client.post("/api/auth/login", json={"email": "agent@campus.edu", "password": "agent123"})
    assert agent_res.status_code == 200
    agent_token = agent_res.json()["access_token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    print("    [PASS] Admin and Agent authenticated successfully")

    # ─── 2. Real DeepSeek API Outbound Call ───────────────────────
    print("\n[2] REAL DEEPSEEK API CALL & FAQ ANSWER")
    t0 = time.time()
    chat_res = client.post(
        "/api/chat/message",
        json={"message": "What are the rules during university examinations?"},
        headers=new_student_headers,
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    latency = time.time() - t0
    print(f"    [PASS] DeepSeek responded in {latency:.2f}s")
    print(f"    Intent: {chat_data['intent']} | Confidence: {chat_data.get('confidence')}")
    print(f"    Response snippet: \"{chat_data['message'][:100]}...\"")
    assert chat_data.get("is_fallback") is False, "Response should come directly from DeepSeek LLM!"

    # ─── 3. Live Knowledge Base Re-embedding Loop ─────────────────
    print("\n[3] LIVE KNOWLEDGE BASE RE-EMBEDDING LOOP")
    # 3a. Admin adds brand-new unique fact
    secret_code = f"ROBOT-{int(time.time()) % 10000}"
    new_kb_payload = {
        "category": "academic",
        "title": f"Robotics Research Lab Policy {secret_code}",
        "content": f"The Advanced Robotics Laboratory requires security passkey {secret_code} for weekend access. Emergency contact is Prof. Kiprop in Hall 5.",
    }
    kb_create_res = client.post("/api/knowledge", json=new_kb_payload, headers=admin_headers)
    assert kb_create_res.status_code == 201
    created_kb = kb_create_res.json()
    print(f"    [PASS] Admin added new KB Entry: \"{created_kb['title']}\" (ID {created_kb['id']})")

    # 3b. Student asks chatbot about this unique fact within the same session
    time.sleep(1.0)  # Brief pause for ChromaDB indexing
    bot_kb_query = client.post(
        "/api/chat/message",
        json={"message": f"What is the security passkey for the Advanced Robotics Laboratory?"},
        headers=new_student_headers,
    )
    assert bot_kb_query.status_code == 200
    bot_kb_answer = bot_kb_query.json()
    print(f"    Bot Answer: \"{bot_kb_answer['message']}\"")
    assert secret_code in bot_kb_answer["message"], f"Expected secret code '{secret_code}' in bot answer!"
    print(f"    [PASS] Self-improving loop verified! Chatbot answered using newly embedded ChromaDB context.")

    # ─── 4. Ambiguous Query Clarification ─────────────────────────
    print("\n[4] AMBIGUOUS QUERY CLARIFICATION")
    ambig_res = client.post(
        "/api/chat/message",
        json={"message": "Hey, can you help me with that thing?"},
        headers=new_student_headers,
    )
    assert ambig_res.status_code == 200
    ambig_data = ambig_res.json()
    print(f"    Intent: {ambig_data['intent']} | Confidence: {ambig_data.get('confidence')}")
    print(f"    Bot Prompt: \"{ambig_data['message'][:80]}...\"")
    assert ambig_data["intent"] in ["clarify", "unknown"] or "clarify" in ambig_data["message"].lower() or "could you clarify" in ambig_data["message"].lower()
    print("    [PASS] Ambiguous query successfully triggered clarification prompt!")

    # ─── 5. Sensitive Issue Escalation vs Feedback ────────────────
    print("\n[5] SENSITIVE ESCALATION VS. FEEDBACK CATEGORY")
    # 5a. Sensitive bribe complaint -> Critical ticket
    sens_res = client.post(
        "/api/chat/message",
        json={"message": "A staff member is demanding a bribe of 5000 shillings to release my grade transcript"},
        headers=new_student_headers,
    )
    assert sens_res.status_code == 200
    sens_data = sens_res.json()
    assert sens_data["intent"] == "sensitive"
    critical_ticket_id = sens_data["metadata"]["ticket_id"]
    critical_priority = sens_data["metadata"]["priority"]
    assert critical_priority == "critical"
    print(f"    [PASS] Sensitive complaint auto-escalated to CRITICAL ticket: {critical_ticket_id}")

    # 5b. Feedback ticket -> Low priority (skips critical path)
    feedback_payload = {
        "category": "feedback",
        "subject": "Campus Cafeteria Food Quality",
        "description": "The new organic salad bar in Cafeteria B is a wonderful addition, thank you!",
    }
    feedback_res = client.post("/api/tickets", json=feedback_payload, headers=new_student_headers)
    assert feedback_res.status_code == 201
    feedback_data = feedback_res.json()
    assert feedback_data["category"] == "feedback"
    assert feedback_data["priority"] == "low"
    print(f"    [PASS] Feedback ticket created: {feedback_data['tracking_id']} | Priority: {feedback_data['priority'].upper()} (Skipped Critical path)")

    # ─── 6. Live Analytics Counter Increments ─────────────────────
    print("\n[6] LIVE ANALYTICS COUNTER INCREMENTS")
    # 6a. Get baseline counts
    analytics_before = client.get("/api/analytics/dashboard", headers=admin_headers).json()
    baseline_tickets = analytics_before["overview"]["total_tickets"]
    baseline_kb = analytics_before["overview"]["total_kb_entries"]
    print(f"    Baseline Analytics -> Tickets: {baseline_tickets} | KB Entries: {baseline_kb}")

    # 6b. Create 1 new ticket
    client.post(
        "/api/tickets",
        json={"category": "academic", "subject": "Live Test Increment", "description": "Testing dynamic counter"},
        headers=new_student_headers,
    )

    # 6c. Verify increment in analytics
    analytics_after = client.get("/api/analytics/dashboard", headers=admin_headers).json()
    new_tickets = analytics_after["overview"]["total_tickets"]
    new_kb = analytics_after["overview"]["total_kb_entries"]
    print(f"    Updated Analytics  -> Tickets: {new_tickets} | KB Entries: {new_kb}")
    assert new_tickets == baseline_tickets + 1, f"Expected total_tickets to increment by 1 (was {baseline_tickets}, now {new_tickets})"
    print(f"    [PASS] Analytics total_tickets dynamically incremented from real database!")

    print("\n" + "=" * 70)
    print("ALL LIVE SYSTEM VERIFICATIONS PASSED SUCCESSFULLY (100%)!")
    print("=" * 70)


if __name__ == "__main__":
    run_live_verification()
