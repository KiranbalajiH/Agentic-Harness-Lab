import os
import json
from agent import agent_answer

doc = 'test_data/orion.pdf'
questions = [
    'When did Project Orion start?',
    'When did Project Orion start, when was it released to production, and how many engineers were on the final team?',
    'What is the final approved engineering budget for Project Orion?',
    'What is the CEO salary?',
    'What is the operational owner of Project Orion?',
    'What was the initial engineering budget, what is the final approved budget, and why did the budget change?'
]

for i, q in enumerate(questions, 1):
    print(f'=== Question {i} ===')
    print('Q:', q)
    log_file = f'logs/orion_test_{i}.jsonl'
    if os.path.exists(log_file):
        os.remove(log_file)
    res = agent_answer(q, doc, log_file)
    print('Status:', res.get('status'))
    print('Answer:', res.get('answer'))
    if res.get('conflict_note'):
        print('Conflict Note:', res.get('conflict_note'))
    with open(log_file, 'r', encoding='utf-8') as f:
        calls = [json.loads(l) for l in f if l.strip()]
    print(f'Calls used: {len(calls)} / 6')
    for c in calls:
        print(f"   [{c['call_number']}] {c['tool']}({c['args']}) -> {c.get('result_summary')}")
    print()
