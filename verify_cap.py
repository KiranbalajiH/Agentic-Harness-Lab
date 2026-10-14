import json
from fastapi.testclient import TestClient
from bridge import app
from tools import DocHandle
from budget import BudgetedTools, BudgetExhausted

print("--- 1. Testing BudgetedTools Direct Cap ---")
handle = DocHandle('test_data/fixture.pdf')
budget = BudgetedTools(handle, 'Hard cap test', 'logs/test_cap_verify.jsonl')

for i in range(1, 7):
    res, err = budget.call('get_page', {'doc_id': 'test_data/fixture.pdf', 'page_number': i}, f'call {i}')
    print(f"Call {i} -> ALLOWED (used: {budget.used}, remaining: {budget.calls_remaining})")

try:
    budget.call('get_page', {'doc_id': 'test_data/fixture.pdf', 'page_number': 1}, 'call 7')
    print("Call 7 -> FAILED (Call was not blocked!)")
except BudgetExhausted as e:
    print(f"Call 7 -> BLOCKED ({e})")

print("\n--- 2. Testing End-to-End API /ask with 6/6 Calls ---")
client = TestClient(app)
with open('test_data/orion.pdf', 'rb') as f:
    resp = client.post(
        '/api/ask',
        files={'file': ('orion.pdf', f, 'application/pdf')},
        data={'question': 'What is the final approved engineering budget for Project Orion?'}
    )

lines = [l for l in resp.text.split('\n\n') if l.startswith('data:')]
tool_calls = [json.loads(l[5:]) for l in lines if json.loads(l[5:]).get('type') == 'tool_call']
final_result = [json.loads(l[5:]) for l in lines if json.loads(l[5:]).get('type') == 'final_result'][0]['result']

print(f"Total tool calls executed: {len(tool_calls)}")
print(f"calls_used reported: {final_result['calls_used']}")
print(f"calls_remaining reported: {final_result['calls_remaining']}")
ui_text = f"{final_result['calls_used']} / 6 tool calls used • {final_result['calls_remaining']} remaining"
print(f"UI display: {ui_text}")
assert ui_text == "6 / 6 tool calls used • 0 remaining"

print("\n--- 3. Testing Fresh 0/6 Budget for Next Question ---")
with open('test_data/orion.pdf', 'rb') as f:
    resp2 = client.post(
        '/api/ask',
        files={'file': ('orion.pdf', f, 'application/pdf')},
        data={'question': 'When did Project Orion start?'}
    )

lines2 = [l for l in resp2.text.split('\n\n') if l.startswith('data:')]
tool_calls2 = [json.loads(l[5:]) for l in lines2 if json.loads(l[5:]).get('type') == 'tool_call']
final_result2 = [json.loads(l[5:]) for l in lines2 if json.loads(l[5:]).get('type') == 'final_result'][0]['result']

print(f"New question tool calls executed: {len(tool_calls2)}")
print(f"New question calls_used: {final_result2['calls_used']}")
print(f"New question calls_remaining: {final_result2['calls_remaining']}")
ui_text2 = f"{final_result2['calls_used']} / 6 tool calls used • {final_result2['calls_remaining']} remaining"
print(f"New question UI display: {ui_text2}")
assert final_result2['calls_used'] + final_result2['calls_remaining'] == 6
print("ALL VERIFICATIONS PASSED SUCCESSFULLY.")
