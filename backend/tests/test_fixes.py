import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import urllib.error
import json

def post(url, data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

print("=== [1] BACKEND HEALTH ===")
with urllib.request.urlopen('http://127.0.0.1:8000/api/health') as r:
    print("Health Status:", json.loads(r.read().decode('utf-8')))

print("\n=== [2] STUDENT LOGIN VIA REGISTRATION NUMBER ===")
code, res = post('http://127.0.0.1:8000/api/auth/login', {'email': 'CS/2024/001', 'password': 'student123'})
print(f"Status Code: {code}")
print(f"User: {res.get('user', {}).get('name')} | Reg No: {res.get('user', {}).get('student_reg_no')}")

print("\n=== [3] WRONG CREDENTIALS REJECTION ===")
code, res = post('http://127.0.0.1:8000/api/auth/login', {'email': 'CS/2024/001', 'password': 'WrongPassword123!'})
print(f"Status Code: {code}")
print(f"Detail Message: {res.get('detail')}")

print("\n=== [4] CHATBOT GREETING ON 'Hi' ===")
token = post('http://127.0.0.1:8000/api/auth/login', {'email': 'student@campus.edu', 'password': 'student123'})[1]['access_token']
code, chat_res = post('http://127.0.0.1:8000/api/chat/message', {'message': 'Hi'}, token=token)
print(f"Status Code: {code}")
print(f"Intent: {chat_res.get('intent')}")
print(f"Chana Reply: {chat_res.get('message')}")

print("\n=== [5] AMBIGUOUS QUERY CLARIFICATION ===")
code, clarify_res = post('http://127.0.0.1:8000/api/chat/message', {'message': 'Can you help me with that thing?'}, token=token)
print(f"Intent: {clarify_res.get('intent')}")
print(f"Chana Clarification Prompt:\n{clarify_res.get('message')}")

print("\n=== [6] TICKETS DATABASE STATE ===")
import sqlite3
conn = sqlite3.connect('campus_companion.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM tickets')
print(f"Live tickets in DB: {cur.fetchone()[0]}")
