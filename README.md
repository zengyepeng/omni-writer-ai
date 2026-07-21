<p align="center">
  <img src="assets/logo.svg" alt="Omni-Writer AI Logo" width="160" height="160"/>
</p>

<h1 align="center">Omni-Writer AI</h1>

<p align="center">
  <strong>Full-stack industrial AI novel writing engine</strong><br/>
  From one-line inspiration to a published chapter — outline, RAG, negotiation simulation, originality radar, and humanization, all in one pipeline.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-3776AB.svg" alt="Python"/>
  <img src="https://img.shields.io/badge/pipeline-v6.0-green.svg" alt="Version"/>
  <img src="https://img.shields.io/badge/UI-CLI%20%7C%20Web-FF6F00.svg" alt="UI"/>
</p>

<p align="center">
  <strong>👉 中文用户请看：<a href="快速上手.md">3 分钟快速上手指南</a>（小白友好，双击即用）</strong>
</p>

---

## ✨ Features

- **🧠 Outline Planner** — turn a one-line inspiration into a 3-volume book skeleton (with `negotiation` scene tagging)
- **📚 RAG Knowledge Base** — ChromaDB-powered retrieval of hardcore worldbuilding materials
- **🎭 Multi-Agent Negotiator** — simulates faction standoffs / court debates for high-IQ political scenes
- **📡 Originality Radar** — scans for "poison points" (Mary-Sue, plot holes, cliché phrases) and auto-rewrites below 80/100
- **🛡️ Humanizer (Sanitizer)** — 4-step de-AI rewriting to dodge GPTZero-style detectors
- **🖌️ Local Redrawer** — radical paragraph-level rewrite with zero shared verbs/adjectives
- **💾 Chapter Archive** — every generated chapter auto-saved to `data/chapters/`
- **🔄 Auto-Retry** — exponential backoff on all LLM calls (3 retries, up to 4s delay)
- **🔑 Config Safety** — `config.yaml` gitignored; env-var override supported
- **🖥️ Dual Interface** — interactive CLI + Gradio Web console with live pipeline logs

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Omni-Writer AI                         │
├──────────────┬──────────────────────────┬───────────────────┤
│   prompts/   │         engine/          │       data/       │
│  writer      │  llm_router (multi-model)│  global_state.json│
│  planner     │  state_manager (memory)  │  outline.json     │
│  negotiator  │  knowledge_base (Chroma) │  chroma_db/       │
│  radar       │  outline_manager         │                   │
│  sanitizer   │                          │                   │
│  redrawer    │                          │                   │
│  material    │                          │                   │
└──────────────┴──────────────────────────┴───────────────────┘
        │                      │                      │
        └──────────┬───────────┴──────────┬───────────┘
                   ▼                      ▼
            main.py (CLI)          web_ui.py (Gradio)
```

## 🔄 Pipeline

```
Inspiration ─▶ Outline Planning ─▶ RAG Retrieval ─▶ Negotiation Sim
                                                              │
                                                              ▼
                                   Draft Generation ─▶ Originality Radar
                                                              │
                                              (auto-rewrite if score < 80)
                                                              ▼
                                      Humanizer (De-AI) ─▶ State Update ─▶ Output
```

## 🚀 Quick Start

### Windows (easiest)

1. Install [Python 3.10+](https://www.python.org/downloads/) (check "Add Python to PATH")
2. Double-click **`install.bat`** → paste your [DeepSeek API Key](https://platform.deepseek.com/api_keys)
3. Double-click **`start.bat`** → pick Web UI or CLI
4. Want a peek first? Choose **Demo mode** (no API key needed)

### Manual Install

```bash
cd omni-writer-ai
pip install -r requirements.txt
cp config.example.yaml config.yaml  # then edit with your API key
```

Or set environment variables (higher priority):

```bash
export OMNI_WRITER_API_KEY="sk-xxx"
export OMNI_WRITER_BASE_URL="https://api.deepseek.com/v1"
export OMNI_WRITER_EMBEDDING_API_KEY="sk-xxx"
```

> `config.yaml` is in `.gitignore` — your keys will never be committed.
> One DeepSeek key covers both LLM and embedding (use `setup_config.py <key>` to auto-generate).

### Run

```bash
python main.py      # CLI mode
python web_ui.py    # Web console at http://127.0.0.1:7860
python demo_mode.py # Demo mode (no API key needed)
```

On first run, enter a one-line inspiration (e.g. `cyberpunk cultivator who hacks the Heavenly Dao with code`). The system generates the outline, then press `n` to write the next chapter, `r` to redraw a paragraph, `q` to quit.

Open http://127.0.0.1:7860 — use the **Creation Engine** tab to generate the outline, then the **Pipeline** tab to write chapters with live logs and inline redrawing.

## 📂 Project Structure

```
omni-writer-ai/
├── install.bat              # one-click installer (Windows)
├── start.bat                # one-click launcher (Web / CLI / Demo)
├── demo_mode.py             # demo mode (no API key needed)
├── setup_config.py          # interactive config generator
├── config.example.yaml      # API keys template (copy to config.yaml)
├── config.yaml              # your local config (gitignored)
├── requirements.txt
├── main.py                  # CLI entry point
├── web_ui.py                # Gradio web console
├── engine/
│   ├── llm_router.py        # multi-model router + retry
│   ├── state_manager.py     # state machine + chapter archive
│   ├── knowledge_base.py    # ChromaDB RAG engine
│   ├── outline_manager.py   # outline planner & scheduler
│   └── exporter.py          # full-book exporter (TXT/MD)
├── prompts/
│   ├── writer_prompt.py     # core draft generation
│   ├── planner_prompt.py    # outline planning
│   ├── negotiator_prompt.py # multi-agent negotiation
│   ├── radar_prompt.py      # originality radar
│   ├── sanitizer_prompt.py  # humanizer
│   ├── redrawer_prompt.py   # local redraw
│   └── material_prompt.py   # material structuring
└── data/                    # runtime state, chroma db, chapter archives
```

## 🗺️ Roadmap

- [ ] Cross-domain analogy setting generator
- [ ] Style fingerprint extractor (imitate your favorite author)
- [ ] Plot branch selector (choose-your-own-adventure outlining)
- [ ] Short-drama script converter
- [ ] Async / concurrent pipeline (`asyncio` + queue)
- [ ] Character relationship graph (NetworkX / Neo4j)
- [ ] SaaS deployment

## 📄 License

MIT © Omni-Writer AI
