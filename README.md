# BAF-Agent: Open behavioural Firewall for AI Agents

BAF-Agent is an **open, behaviour-based firewall layer for AI agents**. It sits between an agent and its environment (files, network) and **learns what “normal” looks like**, then **flags and constrains abnormal behaviour** that could lead to data exfiltration or misuse.

We demonstrate BAF-Agent on a realistic **exam-helper agent** (a study assistant that reads unit notes and past papers), but the design is **agent-agnostic** and intended for any agent that can read files or call APIs.

---

## Motivation

AI agents are increasingly able to:

- Read local files and cloud drives  
- Call external APIs and services  
- Perform actions on behalf of users and teams  

This creates a new security gap:

- Agents can **leak personal and sensitive documents** (IDs, marksheets, HR records, legal documents)  
- Prompt-injected content inside files, emails, or web pages can **hijack agent behaviour**  
- Traditional guardrails focus on text safety, not on how an agent **behaves at the system boundary**

BAF-Agent treats agents as **non-human identities** and introduces a lightweight **behavioural firewall** that watches and governs their actions.

---

## Core Concept

BAF-Agent wraps the sensitive operations of an AI agent:

- **File operations** – listing directories, reading files  
- **Network operations** – HTTP requests to internal or external endpoints  

For each operation, BAF-Agent:

1. **Logs** a structured action event (timestamp, session, action type, resource, bytes, categories).  
2. **Builds a behaviour fingerprint** from benign sessions (what paths, how many files, which endpoints).  
3. **Computes a risk view** when behaviour deviates (new folders, personal docs, unknown domains, unusual volume).  
4. **Adjusts autonomy levels** (L2 → L1 → L0) to allow, restrict, or block actions when risk increases.

The long-term goal is a **vendor-neutral, open firewall** that developers can place in front of their agents, independent of specific hardware or cloud stacks.

---

## Current Prototype

At this stage, the repository contains:

### 1. Exam-Helper Agent (Case Study)

Located under `src/agent/`.

- Models an AI exam-helper that reads unit notes, previous papers, and important questions from `data/Study_Materials/`.  
- Generates quick revision notes by aggregating and summarizing these files.  
- Serves as the **primary case study** for demonstrating agent behaviour and exfiltration risk.

### 2. Attacker Exfiltration Server

Located under `src/server/`.

- Simulated exfiltration endpoint that records any data the agent sends to it in `logs/exfil.log`.  
- Provides a simple “lecture notes” endpoint that can later be used to host benign or prompt-injected content.  
- Allows controlled experiments on **agent-driven data exfiltration** without real internet connectivity.

### 3. BAF-Agent Wrapper (Monitor-Only v0)

Located under `src/baf/`.

- Wraps directory listing, file reads, and HTTP POST calls.  
- Logs each action as a CSV row in `logs/actions.log` with fields such as:
  - `timestamp`, `session_id`, `agent_id`  
  - `action_type` (`list_dir`, `read_file`, `http_post`)  
  - `resource` (absolute file path or URL)  
  - `bytes` (approximate payload size)  
  - `path_category` (e.g., `study`, `personal`, `other`)  
  - `domain_category` (e.g., `internal_known`, `external_unknown`, `none`)
- Operates in **monitor-only mode**: it observes and records, but does not yet block or throttle actions.

---

## Design Goals

- **Agent-agnostic:**  
  The firewall logic is not tied to a specific agent; the exam helper is just one reference implementation.

- **Minimal but expressive event schema:**  
  Events capture enough context (session, resource type, size, categories) to support behaviour fingerprinting and future ML-based anomaly detection.

- **Risk-aware autonomy control (planned):**  
  Subsequent versions will compute risk from features such as:
  - Access to sensitive path categories (e.g., `Personal_Docs`)  
  - Calls to unknown or untrusted domains  
  - Sudden spikes in files read per minute or bytes sent  
  and use it to downgrade autonomy (L2/L1/L0) at runtime.

- **Open and developer-friendly:**  
  Designed to be understandable and modifiable by small teams, students, and independent developers building agents or “agents-as-a-service”.

---

## Example Use Cases (Beyond the Exam Helper)

While the prototype focuses on an exam-helper agent, the same firewall pattern can apply to many other agents, for example:

- **Email triage agent**  
  Reading inbox content and drafting replies, but not allowed to bulk-download all attachments or forward entire mailboxes to unknown domains.

- **Ticket-automation agent**  
  Interacting with bug trackers or incident systems, but prevented from reading HR folders or exporting full databases.

- **Internal knowledge-base agent**  
  Searching documentation for employees, while blocked from accessing confidential finance/legal directories or sending them outside the organization.

The intent is to make BAF-Agent a reusable building block for securing **agents-as-a-service** across domains.

---

## Repository Structure

- `src/agent/` – Exam-helper agent implementation (case study).  
- `src/baf/` – BAF-Agent wrapper and logging logic (monitor-only v0).  
- `src/server/` – Local exfiltration and lecture-notes endpoints for controlled experiments.  
- `data/Study_Materials/` – Synthetic study material files.  
- `data/Personal_Docs/` – Synthetic personal documents (IDs, college IDs, marksheets).  
- `logs/` – Action logs (`actions.log`) and exfiltration logs (`exfil.log`).  
- `tools/` – Utility scripts (e.g., dummy data generation).  
- `LAB_LOG.md` – Day-by-day lab notes and implementation diary.

---

## Project Status

- **Completed so far**
  - Project skeleton and data generation for study and personal document folders.  
  - Exam-helper agent integrated with BAF-Agent wrapper for monitored file access.  
  - Local attacker-style exfiltration server and basic system-level threat model.  
  - Monitor-only BAF-Agent v0 logging all sensitive actions.

- **Planned next steps**
  - behaviour fingerprinting from benign sessions.  
  - Risk scoring based on path/domain/volume signals.  
  - Adaptive autonomy control (L2/L1/L0) with allow/restrict/block decisions.  
  - Additional agents and richer policy examples beyond the exam-helper scenario.

---

## Vision

BAF-Agent aims to be a **vendor-neutral, open behavioural firewall** for AI agents.

As agents become a core part of everyday software (agents-as-a-service), users and developers need a way to:

- Observe and audit what agents actually do  
- Detect when agents step outside their intended scope  
- Automatically reduce or revoke their autonomy before sensitive data leaks  

This repository is an evolving prototype toward that vision, starting with a concrete, reproducible exam-helper case study and growing into a general-purpose firewall layer for AI agents.