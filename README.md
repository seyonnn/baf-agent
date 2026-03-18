# BAF-Agent: Behavioral Firewall for Exam AI Helper

This project implements a simple **exam AI helper agent** (like the tools students use before exams to generate notes from unit PPTs and past papers) and a **Behavioral Firewall for Autonomous AI Agents (BAF-Agent)** that protects against data exfiltration.

## Idea in One Line

We treat the AI exam helper as an "AI worker" and put a behavioral firewall in front of it, so it cannot silently read and leak private documents (IDs, certificates) when a malicious study file tries to hijack it.

## High-Level Components

- `src/agent/` – Exam helper agent that:
  - Reads files from `data/Study_Materials/`
  - Generates simple study notes

- `src/baf/` – Behavioral firewall wrapper (BAF-Agent) that will:
  - Log agent actions (file reads, HTTP calls)
  - Learn normal behavior (fingerprint)
  - Score risk and adapt the agent's autonomy (allow/throttle/block)

- `src/server/` – Local Flask server that:
  - Simulates an attacker exfiltration endpoint (`/exfil`)
  - Serves simple "lecture pages" used by the agent

- `data/Study_Materials/` – Dummy unit notes, past papers, important questions  
- `data/Personal_Docs/` – Dummy Aadhaar-like IDs, marksheets, certificates  
- `logs/` – Logs of agent actions, firewall decisions, and exfil attempts

## Status

- [ ] Day 1: Project structure + skeleton exam helper agent