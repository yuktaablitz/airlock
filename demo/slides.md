# Airlock: slide content for Adobe Express

Numbers come from `runs/agent_bench.md`, `runs/results_v3.md` and `runs/stats_v3.md`. Visual style: match the dashboard, which is
near-black, amber (#FFB020) signal, hazard stripes, Space Grotesk and JetBrains Mono.

## 1 · Title
**AIR/LOCK: an inbound firewall for AI agents**
A decision model checks everything an agent reads, before it acts.
Yuktaa · Drexathon · Apex Predator · github.com/yuktaablitz/airlock · PR nace-ai/intern#4

## 2 · The problem: agents act on what they read
- Agents now pay invoices, settle claims, trade, update medication lists and buy things in games.
- Anyone who can write text the agent reads can steer it: a PDF, a web page, a ticket, a game guide, a screenshot.
- Intern guards tool **calls**. Nothing checked what a tool **returned**.
- *Visual: the 8 scenario cards (screenshot of the dashboard's Scenarios tab).*

## 3 · Live demo (dashboard → Scenarios)
1. Finance: the invoice's hidden "bank change" → without Airlock the agent **pays the attacker's account**; with Airlock it pays the real one.
2. Coding: the README's hidden comment → without Airlock the agent **runs `curl | bash`**; with Airlock it runs `pip install`.
3. Gaming: **the Adobe-made game guide image** with faint text → NDI reads it → Drex cuts two sentences → the agent buys the $2.99 kit, not the $99.99 pack.

## 4 · How it works
Tool output → **NDI** (what a human sees vs what the agent reads) → chunks → **one Drex request** (a calibrated probability
per chunk) → cut → **refine** (Drex re-scores sentences, so only the attacker's sentences go) → agent.
Ships three ways: an Intern `tool_result` extension, a `/screen` API, and an upstream PR.

## 5 · Evaluation 1: does the agent still work? (AgentDojo-style, 8 industries)
| | Task done, no attack | Task done under attack | Attack lands |
|---|---|---|---|
| No defense | 85% | 57% | 30% |
| LLM guard | 85% | **0%** | 10% |
| **Airlock** | 85% | **85%** | **0%** |
Success is read from the agent's tool calls, with no LLM judge. Ablation: cutting whole chunks drops "task done under attack" to 40%. Sentence-level refinement is what keeps the agent useful.

## 6 · Evaluation 2: is the decision trustworthy?
- F1 **0.971** vs 0.898 for the LLM guard (McNemar p = 7×10⁻⁷). False alarms on unseen benign commands: **3% vs 83%**.
- **Calibrated: ECE 0.008.** When Drex says 0.85, 87.5% of those chunks are attacks, so thresholds mean something.
- p95 latency **416 ms vs 2.7 s**. Probabilities only, so the guard has no output channel to hijack.
- *Visual: the reliability diagram (runs/calibration_v3.png).*

## 7 · Engineering judgment
- We caught our own leakage: the first headline was inflated. We rebuilt the splits (no shared documents or sentences), wrote a fresh holdout, and replaced the numbers.
- The data, not taste, chose the default: the LLM cascade added no accuracy (p = 1) and 5× the false alarms, so Drex alone ships.
- Honest limits: static attacks only (adaptive attackers, Nasr et al. 2025), a small agent benchmark with wide CIs, and a placeholder Drex price.

## 8 · Built with
Drex · NDI · Intern (extension + PR #4) · DeepInfra (Qwen3.8-27B) · Keenable (real web pages) · **Adobe Firefly / Express / Photoshop (red-team image corpus + this deck)**
