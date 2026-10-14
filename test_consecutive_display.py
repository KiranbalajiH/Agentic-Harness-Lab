import json
from fastapi.testclient import TestClient
from bridge import app

client = TestClient(app)

questions = [
    'When did Project Orion start?',
    'What is the final approved engineering budget for Project Orion?',
    'What is the CEO salary?'
]

for idx, q in enumerate(questions, 1):
    print(f"=== Q{idx}: {q} ===")
    with open('test_data/orion.pdf', 'rb') as f:
        resp = client.post('/api/ask', files={'file': ('orion.pdf', f, 'application/pdf')}, data={'question': q})
    
    assert resp.status_code == 200, f"Status {resp.status_code}"
    
    # 1. At start of question:
    ui_display = "0 / 6 tool calls used • 6 remaining"
    print(f"Start: {ui_display}")
    
    # 2. As events arrive:
    lines = resp.text.strip().split('\n\n')
    for block in lines:
        if not block.startswith('data:'):
            continue
        data = json.loads(block[len('data:'):].strip())
        if data.get('type') == 'tool_call':
            rec = data['record']
            used = rec['calls_used']
            rem = max(0, 6 - used)
            ui_display = f"{used} / 6 tool calls used • {rem} remaining"
            print(f"After call {used}: {ui_display} ({rec['tool']})")
        elif data.get('type') == 'final_result':
            final_res = data['result']
            final_used = final_res['calls_used']
            final_rem = final_res['calls_remaining']
            ui_display = f"{final_used} / 6 tool calls used • {final_rem} remaining"
            print(f"Final Display: {ui_display}")
            print(f"Answer: {final_res['answer']}")
    print()
