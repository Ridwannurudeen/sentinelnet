#!/usr/bin/env python3
"""
SentinelNet Live Demo
Run this to see SentinelNet in action against real ERC-8004 agents on Base.
"""
import httpx
import time
import sys

API = "https://sentinelnet.gudman.xyz"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[96m"

def color_verdict(verdict):
    if verdict == "TRUST": return f"{GREEN}{verdict}{RESET}"
    if verdict == "CAUTION": return f"{YELLOW}{verdict}{RESET}"
    return f"{RED}{verdict}{RESET}"

def section(title):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")

def pause():
    time.sleep(1.5)

def main():
    client = httpx.Client(base_url=API, timeout=30)

    # 1. Health check
    section("1. SentinelNet is live on Base Mainnet")
    r = client.get("/api/health").json()
    print(f"  Service: {BOLD}{r['service']}{RESET}")
    print(f"  Version: {r['version']}")
    print(f"  Status:  {GREEN}{r['status']}{RESET}")
    pause()

    # 2. Ecosystem stats
    section("2. Ecosystem overview")
    stats = client.get("/api/stats").json()
    print(f"  Agents scored:      {BOLD}{stats['agents_scored']}{RESET}")
    print(f"  Average trust:      {stats['avg_trust_score']}")
    print(f"  Score range:        {stats['min_trust_score']} - {stats['max_trust_score']}")
    print(f"  Verdicts:")
    print(f"    {GREEN}TRUST{RESET}:   {stats['verdicts']['TRUST']}")
    print(f"    {YELLOW}CAUTION{RESET}: {stats['verdicts']['CAUTION']}")
    print(f"    {RED}REJECT{RESET}:  {stats['verdicts']['REJECT']}")
    print(f"  Sybil flagged:      {RED}{stats['sybil_flagged']}{RESET}")
    print(f"  Contagion affected: {stats.get('contagion_affected', 0)}")
    pause()

    # 3. Query our own agent
    section("3. Query SentinelNet itself (Agent #31253)")
    try:
        score = client.get("/trust/31253").json()
        print(f"  Agent ID:      {BOLD}31253{RESET}")
        print(f"  Wallet:        {DIM}{score['wallet']}{RESET}")
        print(f"  Trust Score:   {BOLD}{score['trust_score']}{RESET}")
        print(f"  Verdict:       {color_verdict(score['verdict'])}")
        print(f"  Breakdown:")
        print(f"    Longevity:        {score['longevity']}/100")
        print(f"    Activity:         {score['activity']}/100")
        print(f"    Counterparty:     {score['counterparty']}/100")
        print(f"    Contract Risk:    {score['contract_risk']}/100")
        print(f"    Agent Identity:   {score['agent_identity']}/100")
        if score.get('explanation'):
            print(f"  Summary: {DIM}{score['explanation']['summary']}{RESET}")
    except Exception:
        print(f"  {DIM}Agent 31253 not yet scored in this sweep cycle{RESET}")
    pause()

    # 4. Batch query
    section("4. Batch trust query (5 agents at once)")
    batch = client.post("/trust/batch", json={"agent_ids": [1, 2, 3, 100, 31253]}).json()
    print(f"  Queried: {batch['queried']}  |  Found: {batch['found']}")
    for aid, data in batch["results"].items():
        if data:
            print(f"  Agent {aid:>5}: score={data['trust_score']:>3}  verdict={color_verdict(data['verdict'])}")
        else:
            print(f"  Agent {aid:>5}: {DIM}not scored{RESET}")
    pause()

    # 5. Threat intelligence
    section("5. Real-time threat intelligence feed")
    threats = client.get("/api/threats?limit=5").json()
    print(f"  Latest threats ({threats['count']} shown):\n")
    for t in threats["threats"]:
        severity_color = RED if t["severity"] == "HIGH" else YELLOW
        print(f"  [{severity_color}{t['severity']}{RESET}] {BOLD}{t['threat_type']}{RESET}")
        print(f"    Agent: {t['agent_id']}  |  {DIM}{t['details'][:80]}{RESET}")
        print()
    pause()

    # 6. Trust gating demo
    section("6. Trust-gated interaction demo")
    test_agents = [1, 2, 3]
    for aid in test_agents:
        try:
            s = client.get(f"/trust/{aid}").json()
            trusted = s["trust_score"] >= 55 and not s.get("sybil_flagged")
            status = f"{GREEN}ALLOWED{RESET}" if trusted else f"{RED}BLOCKED{RESET}"
            print(f"  Agent {aid}: score={s['trust_score']} verdict={color_verdict(s['verdict'])} -> {status}")
        except Exception:
            print(f"  Agent {aid}: {DIM}unscored -> {RED}BLOCKED{RESET}")
    pause()

    # 7. SDK demo
    section("7. SDK integration (Python)")
    print(f"  {DIM}from sentinelnet import SentinelNet{RESET}")
    print(f"  {DIM}sn = SentinelNet(){RESET}")
    print(f"  {DIM}if sn.trust_gate(agent_id=42, min_score=55):{RESET}")
    print(f"  {DIM}    execute_transaction(){RESET}")
    print()
    print(f"  This is a real SDK — install with:")
    print(f"  {CYAN}pip install git+https://github.com/Ridwannurudeen/sentinelnet.git#subdirectory=sdk/python{RESET}")
    pause()

    # 8. Network graph
    section("8. Interactive trust network")
    graph = client.get("/api/graph-data").json()
    print(f"  Nodes (agents): {BOLD}{len(graph['nodes'])}{RESET}")
    print(f"  Edges (interactions): {BOLD}{len(graph['links'])}{RESET}")
    print(f"  View live: {CYAN}{API}/graph{RESET}")
    pause()

    # Summary
    section("SentinelNet — The immune system for the agent economy")
    print(f"  {BOLD}Live dashboard:{RESET}  {CYAN}{API}/dashboard{RESET}")
    print(f"  {BOLD}Trust network:{RESET}   {CYAN}{API}/graph{RESET}")
    print(f"  {BOLD}API docs:{RESET}        {CYAN}{API}/docs{RESET}")
    print(f"  {BOLD}Integration:{RESET}     {CYAN}{API}/docs-guide{RESET}")
    print(f"  {BOLD}GitHub:{RESET}          {CYAN}https://github.com/Ridwannurudeen/sentinelnet{RESET}")
    print()

if __name__ == "__main__":
    main()
