# iValue PRISM — Agent Context

**iValue PRISM** (Presales Recommendation & Intelligence System) is a native Windows 10/11 desktop application for iValue InfoSolutions, a cybersecurity/IT infrastructure value-added distributor. It automates presales engineering workflows — requirement analysis, product recommendation from a 139-product OEM catalog, licensing guidance, and BOM/BOQ document drafting — using a fully local, offline RAG pipeline (bge-small-en-v1.5 embeddings + Phi-4-mini via Ollama) with a CustomTkinter GUI.

## Hard Constraints (Non-Negotiable)

- **No pricing logic anywhere in outputs.** The system must never generate, estimate, display, or store any price, cost, fee, or monetary value under any circumstance.
- **100% offline-capable.** No component may depend on a remote API, cloud service, or network resource during normal operation.
- **Technology stack is locked.** CustomTkinter / PyInstaller / Ollama / tksheet / NumPy-brute-force / sentence-transformers. Do not propose alternatives.
- **RAG-over-structured-data only.** Never fine-tune for facts. Facts live in retrievable data, not model weights.
- **Human-in-the-loop always.** Every output is a draft for engineer review; nothing is customer-facing without explicit acceptance.

## Model Routing Policy

> **Planning and architecture decisions** → escalate to Opus, do not attempt in a fast model.
> **Implementation of an already-approved task from `docs/implementation-plan.md`** → fast model (Gemini).
> If a fast model hits ambiguity not covered by its task spec, it **must stop** and write an entry in the **Escalation Log** in `docs/implementation-plan.md` rather than improvising or asking the user directly.

## Document Pointers

- `docs/iValue_Presales_Automation_SRS.md` — Full specification (v3.4, authoritative, locked)
- `docs/implementation-plan.md` — Task-by-task execution plan and current status
- `.agents/skills/` — Reusable implementation patterns and reference snippets

**Before starting any task, read the Status Dashboard and Quick Start block at the top of `docs/implementation-plan.md`.**

---
*Skills directory: `.agents/skills/` (workspace-relative)*
