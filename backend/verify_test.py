import requests, sys

BASE = "http://127.0.0.1:8000"
passed = 0; failed = 0

def check(cond, msg):
    global passed, failed
    if cond:
        print("  PASS:", msg); passed += 1
    else:
        print("  FAIL:", msg); failed += 1; sys.exit(1)

print("\n=== Chana - Full System Verification ===\n")

r = requests.post(BASE + "/api/auth/login", json={"email": "student@campus.edu", "password": "wrong"})
check(r.status_code == 401, "Invalid login -> 401")

r = requests.post(BASE + "/api/auth/login", json={"email": "student@campus.edu", "password": "student123"})
check(r.status_code == 200, "Student login -> 200")
sh = {"Authorization": "Bearer " + r.json()["access_token"]}

r = requests.post(BASE + "/api/auth/login", json={"email": "agent@campus.edu", "password": "agent123"})
check(r.status_code == 200, "Agent login -> 200")
ah = {"Authorization": "Bearer " + r.json()["access_token"]}

r = requests.post(BASE + "/api/auth/login", json={"email": "admin@campus.edu", "password": "admin123"})
check(r.status_code == 200, "Admin login -> 200")
admh = {"Authorization": "Bearer " + r.json()["access_token"]}

r = requests.post(BASE + "/api/chat/message", json={"message": "Where is the library?"}, headers=sh)
check(r.status_code == 200, "Chat message -> 200")
sid = r.json()["session_id"]

r = requests.get(BASE + "/api/chat/sessions", headers=sh)
check(r.status_code == 200, "GET /chat/sessions -> 200")
sessions = r.json()
check(len(sessions) > 0, "At least 1 chat session exists")
check("preview" in sessions[0], "Session has preview field: " + str(sessions[0].get("preview", "")))

r = requests.get(BASE + "/api/chat/sessions/" + str(sid) + "/messages", headers=sh)
check(r.status_code == 200, "GET /chat/sessions/{id}/messages -> " + str(len(r.json())) + " messages")

r = requests.post(BASE + "/api/tickets", json={"category": "facilities", "subject": "Key lost", "description": "Lost room key"}, headers=sh)
check(r.status_code == 201, "Create ticket -> 201 (" + r.json().get("tracking_id","") + ")")
tid = r.json()["id"]

r = requests.get(BASE + "/api/tickets", headers=ah)
check(r.status_code == 200, "Agent GET /tickets -> " + str(len(r.json())) + " tickets")
claimable = [t for t in r.json() if not t.get("assigned_agent_id") and t.get("status") == "open"]
check(len(claimable) >= 1, "Claimable tickets visible: " + str(len(claimable)))

r = requests.patch(BASE + "/api/tickets/" + str(tid) + "/claim", headers=ah)
check(r.status_code == 200, "Claim ticket -> status=" + str(r.json().get("status")))

r = requests.patch(BASE + "/api/tickets/" + str(tid) + "/status", json={"status": "resolved"}, headers=ah)
check(r.status_code == 200, "Resolve ticket -> status=" + str(r.json().get("status")))

r = requests.post(BASE + "/api/tickets/" + str(tid) + "/rate", json={"rating": 5, "comment": "Great support!"}, headers=sh)
check(r.status_code == 200, "Rate ticket -> " + str(r.json().get("rating")) + "/5")
check(r.json().get("rating") == 5, "Rating value is 5")
check(r.json().get("rating_comment") == "Great support!", "Rating comment saved")

r = requests.get(BASE + "/api/analytics/dashboard", headers=admh)
check(r.status_code == 200, "GET /analytics/dashboard -> 200")
ov = r.json()["overview"]
check(ov["total_students"] >= 1, "total_students=" + str(ov["total_students"]))
check(ov["total_agents"] >= 1, "total_agents=" + str(ov["total_agents"]))
check(ov["total_tickets"] >= 1, "total_tickets=" + str(ov["total_tickets"]))
check(ov["total_kb_entries"] >= 1, "total_kb_entries=" + str(ov["total_kb_entries"]))
check(ov["vector_chunks"] >= 1, "vector_chunks=" + str(ov["vector_chunks"]))
check(ov["average_rating"] is not None, "average_rating=" + str(ov["average_rating"]))

r = requests.get(BASE + "/api/admin/agents", headers=admh)
check(r.status_code == 200, "GET /admin/agents -> 200")
agents = r.json()
check(len(agents) >= 1, "Agents listed: " + str(len(agents)))
for a in agents:
    check("average_rating" in a, a["name"] + " has average_rating=" + str(a.get("average_rating")))
    check("ratings_count" in a, a["name"] + " has ratings_count=" + str(a.get("ratings_count")))
    check("active_tickets_count" in a, a["name"] + " has active_tickets_count=" + str(a.get("active_tickets_count")))

r = requests.get(BASE + "/api/knowledge", headers=admh)
check(r.status_code == 200, "GET /knowledge -> " + str(len(r.json())) + " entries")

print("\n================================================")
print(" ALL", passed, "TESTS PASSED - SYSTEM FUNCTIONAL")
print("================================================\n")
