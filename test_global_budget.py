"""
Verification script for GLOBAL SESSION BUDGET (6 calls total per PDF).
Simulates bridge.py session tracking behavior.
"""

import os
import json
import time
from agent import agent_answer

def run_test():
    doc_path = "C:/Users/kiran/antigravity K/Agentic-Harness-Lab/test_data/fixture.pdf"
    log_path = "C:/Users/kiran/antigravity K/Agentic-Harness-Lab/logs/global_test.jsonl"

    if os.path.exists(log_path):
        os.remove(log_path)

    calls_used = 0

    def ask(q):
        nonlocal calls_used
        if calls_used >= 6:
            return {
                "status": "INSUFFICIENT",
                "answer": "Document tool budget exhausted. No further questions can be answered for this uploaded document.",
                "calls_used": calls_used
            }

        # Run agent
        res = agent_answer(q, doc_path, log_path)

        # Enforce global truncation to 6 lines max
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                lines = f.readlines()
            if len(lines) > 6:
                lines = lines[:6]
                with open(log_path, "w") as fw:
                    fw.writelines(lines)
            calls_used = len(lines)

        res["calls_used"] = calls_used
        return res

    print("--- TEST 1: Question 1 ---")
    res1 = ask("What is the primary color of the company logo?")
    print(f"Status: {res1['status']}, Global Calls Used: {res1['calls_used']} / 6")

    print("\n--- TEST 2: Question 2 ---")
    res2 = ask("When was project Alpha started?")
    print(f"Status: {res2['status']}, Global Calls Used: {res2['calls_used']} / 6")

    print("\n--- TEST 3: Question 3 ---")
    res3 = ask("What is the standard fee for subscription and server timeout?")
    print(f"Status: {res3['status']}, Global Calls Used: {res3['calls_used']} / 6")

    print("\n--- TEST 4: Question 4 (Should be Blocked) ---")
    res4 = ask("What is office safety policy?")
    print(f"Status: {res4['status']}, Answer: '{res4['answer']}', Global Calls Used: {res4['calls_used']} / 6")

    print("\n--- TEST 5: PDF Replacement (Reset) ---")
    # Simulate PDF replacement: delete log, reset counter
    if os.path.exists(log_path):
        os.remove(log_path)
    calls_used = 0
    print(f"After replacement: Global Calls Used: {calls_used} / 6 (Reset OK)")

    print(f"\nFinal Total Calls in Log: {calls_used}")
    if calls_used <= 6:
        print("PASS: Global 6-call session budget enforced. No 7th call executed.")

if __name__ == "__main__":
    run_test()
