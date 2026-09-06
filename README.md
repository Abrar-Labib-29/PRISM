# iValue PRISM — Presales Recommendation & Intelligence System

[![Platform: Windows 10/11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![UI: CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet)](https://github.com/TomSchimansky/CustomTkinter)
[![Inference: Ollama Local](https://img.shields.io/badge/LLM-Phi--4--mini%20(Local)-0EA5E9)](https://ollama.com)
[![Embeddings: bge-small-en-v1.5](https://img.shields.io/badge/Embeddings-bge--small--en--v1.5-10B981)](https://huggingface.co/BAAI/bge-small-en-v1.5)
[![License: Internal / Proprietary](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)

**iValue PRISM** (Presales Recommendation & Intelligence System) is a native, offline-capable Windows 10/11 desktop application engineered to streamline and standardize presales workflows at **iValue InfoSolutions**. 

It analyzes customer technical requirements and RFP excerpts, matches them against a curated catalog of 139 OEM enterprise cybersecurity and networking solutions using hybrid vector retrieval, generates factually grounded recommendations with dataset citations via a local neural model (Phi-4-mini), and automatically drafts structured Bill of Materials (BOM) and Bill of Quantities (BOQ) documents.

---

## 🌟 Key Features

- **🚀 100% Offline & Free:** Executes completely on localhost with zero external cloud API dependencies, zero request fees, and complete data confidentiality.
- **⚡ High-Speed Hybrid Retrieval:** Blends dense semantic vector embeddings (`bge-small-en-v1.5`, 384 dimensions) with exact keyword and sub-domain metadata filters using a brute-force NumPy cosine similarity matrix (<1ms retrieval latency).
- **🧠 Grounded Local AI Reasoning:** Uses Microsoft `Phi-4-mini` (3.8B Q4_K_M) served locally through Ollama to synthesize recommendations strictly grounded in internal product data.
- **🛡️ Deterministic Safety Guardrails:**
  - **Zero Pricing Rule:** Automated regex filtering catches and removes any mention of monetary pricing or commercial rates per corporate sales policy.
  - **Hallucination Verification:** Validates every claimed product and feature against catalog records.
  - **Repetition Loop Detection:** Automatically truncates n-gram generation loops.
- **🎨 Modern Windows Native GUI:** Crafted with CustomTkinter adhering to official iValue branding (*Deep Purple → Midnight Navy → Radiant Sky Blue → Pure White*), 60 FPS non-blocking background threading, token streaming, and dark/light mode toggle.
- **📊 Automated BOM / BOQ Export:**
  - Generates `.xlsx` Bill of Materials via `openpyxl`.
  - Generates `.docx` technical proposal documents via `python-docx` with blank pricing columns for Sales completion.
  - Direct shell integration (`os.startfile` and Windows Explorer highlighting).

---

## 🏗️ Architecture Overview

```
+-------------------------------------------------------------------------+
|                  iValue PRISM CustomTkinter GUI (Main Thread)           |
|  - Requirement Textbox & RFP Document Uploader (.pdf, .docx, .txt)      |
|  - Real-Time Token Streaming Display & 3-Stage Progress Indicator      |
|  - Recommendation Cards, Decision Toolbar & BOM/BOQ Exporter           |
+------------------------------------+------------------------------------+
                                     | Event Queue (queue.Queue)
                                     v
+-------------------------------------------------------------------------+
|                    Worker Thread (Background Daemon)                    |
|  1. Document Parser: Ingests & extracts text from RFP documents         |
|  2. Query Embedder: bge-small-en-v1.5 (384-d vector with query prefix)  |
|  3. Hybrid Retriever: NumPy Cosine Sim + Sub_Domain metadata filter     |
|  4. Context Builder: Assembles structured Markdown prompt (<1200 toks)  |
|  5. Inference Engine: Streams Phi-4-mini ChatML via local Ollama SSE    |
|  6. Validator: Enforces price stripping & catalog fact verification     |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                             Local Data Store                            |
|  - data/raw/iValue_Solution_Recommendation_Dataset.xlsx (Master)        |
|  - data/embeddings.npy (Pre-computed 139 product vectors)               |
|  - data/metadata.pkl (Fast-lookup product metadata)                     |
|  - data/composite_products.json (Natural-language product documents)    |
+-------------------------------------------------------------------------+
```

---

## 📂 Repository Structure

```
PRISM/
├── assets/
│   ├── branding/
│   │   ├── ivalue_prism_logo.png     # Master brand asset
│   │   ├── ivalue_prism_logo.jpg     # High-res crystalline refraction render
│   │   └── ivalue_prism.ico          # Multi-resolution Windows app icon
│   └── icons/                        # UI action icons
├── data/
│   ├── raw/
│   │   └── iValue_Solution_Recommendation_Dataset.xlsx  # Master catalog
│   ├── composite_products.json       # Synthesized product descriptions
│   ├── domain_taxonomy.json          # 33 Sub-domain taxonomy mapping
│   ├── embeddings.npy                # 139 × 384 pre-computed vector index
│   └── metadata.pkl                  # Fast-lookup metadata table
├── docs/
│   ├── iValue_Presales_Automation_SRS.md   # Complete Software Requirements Spec (v3.3)
│   ├── iValue_Presales_Automation_SRS.pdf  # Compiled PDF specification
│   └── benchmarks/                         # Phase 0 hardware & quality test logs
├── scripts/
│   ├── build_composite_embeddings.py # Re-computes embeddings on dataset update
│   └── validate_dataset_integrity.py # Validates schema & referential integrity
├── src/
│   ├── core/                         # Retrieval, Ollama client, exporters, validators
│   ├── ui/                           # CustomTkinter application, cards, modals, themes
│   └── utils/                        # Logging, system diagnostics, configuration
├── tests/                            # Automated test suite (unit, integration, stress)
├── themes/
│   └── ivalue_prism.json             # CustomTkinter iValue brand theme
└── Modelfile.presales                # Ollama model definition with optimal runtime params
```

---

## 💻 Hardware & System Requirements

- **Operating System:** Windows 10 (version 1909+) or Windows 11 (64-bit).
- **Processor:** Intel Core i5 10th Gen (4 cores / 8 threads) or equivalent.
- **Memory:** 8 GB DDR4 RAM (System uses ~4.8–5.8 GB total system RAM during active inference).
- **Disk Space:** ~5 GB free space (accommodates Ollama Phi-4-mini weights and embedding cache).
- **GPU:** Not required; 100% CPU-optimized inference.

---

## 🚀 Getting Started

### 1. Prerequisites
1. Ensure Python 3.10+ is installed:
   ```powershell
   python --version
   ```
2. Install and launch [Ollama](https://ollama.com/download/windows):
   ```powershell
   ollama --version
   ollama pull phi4-mini
   ```

### 2. Setup Environment
```powershell
# Clone the repository
git clone https://github.com/abrar-labib-29/PRISM.git
cd PRISM

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install customtkinter darkdetect pillow ollama sentence-transformers numpy pandas pdfplumber python-docx openpyxl pyinstaller
```

### 3. Launch Application
```powershell
python main.py
```

---

## 📄 License & Attribution

Designed and developed for **iValue InfoSolutions Pvt Ltd**. All OEM catalogs, product metadata, and internal workflows are proprietary.
