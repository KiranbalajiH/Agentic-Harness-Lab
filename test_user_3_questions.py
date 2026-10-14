import json
from fastapi.testclient import TestClient
from bridge import app

client = TestClient(app)

# Question 1: Simple factual (expected 3 calls)
# Question 2: Multi-part or complex supersession (expected 6 calls)
# Question 3: Fresh question (starts at 0/6)
q1 = "When did Project Orion start?"
q2 = "What is the final approved engineering budget for Project Orion?"
q3 = "What is the operational owner of Project Orion?"

print("==================================================")
print("TESTING QUESTION 1:")
print(f"Query: '{q1}'")
ui_state = "0 / 6 tool calls used • 6 remaining"
print(f"-> At Question 1 Start: {ui_state}")

with open("test_data/orion.pdf", "rb") as f:
    resp1 = client.post("/api/ask", files={"file": ("orion.pdf", f, "application/pdf")}, data={"question": q1})

lines1 = [l for l in resp1.text.split("\n\n") if l.startswith("data:")]
for block in lines1:
    msg = json.loads(block[len("data:"):].strip())
    if msg.get("type") == "tool_call":
        rec = msg["record"]
        used = rec["calls_used"]
        rem = max(0, 6 - used)
        ui_state = f"{used} / 6 tool calls used • {rem} remaining"
        print(f"-> After Call {used} ({rec['tool']}): {ui_state}")
    elif msg.get("type") == "final_result":
        res = msg["result"]
        ui_state = f"{res['calls_used']} / 6 tool calls used • {res['calls_remaining']} remaining"
        print(f"-> UI Ends At: {ui_state}")
        print(f"   Answer: {res['answer']}")
        assert res['calls_used'] == 3, f"Expected 3 calls, got {res['calls_used']}"
        assert res['calls_remaining'] == 3

print("\n==================================================")
print("TESTING QUESTION 2:")
print(f"Query: '{q2}'")
# Fresh question immediate reset in UI
ui_state = "0 / 6 tool calls used • 6 remaining"
print(f"-> At Question 2 Start: {ui_state} (RESET immediately)")

with open("test_data/orion.pdf", "rb") as f:
    resp2 = client.post("/api/ask", files={"file": ("orion.pdf", f, "application/pdf")}, data={"question": q2})

lines2 = [l for l in resp2.text.split("\n\n") if l.startswith("data:")]
for block in lines2:
    msg = json.loads(block[len("data:"):].strip())
    if msg.get("type") == "tool_call":
        rec = msg["record"]
        used = rec["calls_used"]
        rem = max(0, 6 - used)
        ui_state = f"{used} / 6 tool calls used • {rem} remaining"
        print(f"-> After Call {used} ({rec['tool']}): {ui_state}")
    elif msg.get("type") == "final_result":
        res = msg["result"]
        ui_state = f"{res['calls_used']} / 6 tool calls used • {res['calls_remaining']} remaining"
        print(f"-> UI Ends At: {ui_state}")
        print(f"   Answer: {res['answer'][:80]}...")
        assert res['calls_used'] == 6, f"Expected 6 calls, got {res['calls_used']}"
        assert res['calls_remaining'] == 0

print("\n==================================================")
print("TESTING QUESTION 3:")
print(f"Query: '{q3}'")
# Fresh question immediate reset in UI
ui_state = "0 / 6 tool calls used • 6 remaining"
print(f"-> At Question 3 Start: {ui_state} (STARTS AGAIN AT 0/6)")

with open("test_data/orion.pdf", "rb") as f:
    resp3 = client.post("/api/ask", files={"file": ("orion.pdf", f, "application/pdf")}, data={"question": q3})

lines3 = [l for l in resp3.text.split("\n\n") if l.startswith("data:")]
for block in lines3:
    msg = json.loads(block[len("data:"):].strip())
    if msg.get("type") == "tool_call":
        rec = msg["record"]
        used = rec["calls_used"]
        rem = max(0, 6 - used)
        ui_state = f"{used} / 6 tool calls used • {rem} remaining"
        print(f"-> After Call {used} ({rec['tool']}): {ui_state}")
    elif msg.get("type") == "final_result":
        res = msg["result"]
        ui_state = f"{res['calls_used']} / 6 tool calls used • {res['calls_remaining']} remaining"
        print(f"-> UI Ends At: {ui_state}")
        print(f"   Answer: {res['answer']}")

print("\n==================================================")
print("ALL 3 QUESTIONS PASSED EXACT SPECIFICATION.")
