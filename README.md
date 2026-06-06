# Waterplan Research Tool

Automated water risk intelligence for industrial locations. Given a list of locations, the tool researches three dimensions per location — **water stress**, **incidents & conflicts**, and **regulations** — using multiple web sources, then validates every claim by fetching and checking the cited URL.

Built with **LangChain**, runs against **OpenAI**, **Anthropic Claude**, or **local Ollama** models interchangeably.

---

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/waterplan-research
cd waterplan-research

pip install -r requirements.txt
playwright install chromium   # downloads Chromium for JS-heavy page fallback

cp .env.example .env
# Edit .env and add your API keys

python3 main.py research "Mexicali, Mexico" "Monterrey, Mexico" "Chandler, Arizona, USA"
```

---

## Setup

### Requirements
- Python 3.11+
- At least one of: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (Ollama requires neither)

### API Keys

Copy `.env.example` to `.env` and fill in your keys:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### SearXNG (optional, recommended for scale)

By default the tool uses DuckDuckGo, which is rate-limited and unsuitable for large batches. SearXNG is a self-hosted metasearch engine that fans queries to Google, DuckDuckGo, and Wikipedia simultaneously — free, unlimited, no API key needed.

```bash
cd searxng
docker compose up -d
cd ..

python3 main.py search-provider   # confirms: SearXNG (localhost:8080, auto-detected)
```

The tool auto-detects SearXNG on `localhost:8080` — no config change needed. Stop it with `docker compose down` from the `searxng/` directory.

### Ollama (optional, fully local)

```bash
brew install ollama
ollama serve          # in a separate terminal
ollama pull llama3.1
python3 main.py research "Mexicali, Mexico" --model llama3.1
```

---

## Usage

```bash
# Research 3 locations with default model (claude-sonnet-4-6)
python3 main.py research "Mexicali, Mexico" "Monterrey, Mexico" "Chandler, Arizona, USA"

# Use a specific model
python3 main.py research "Mexicali, Mexico" --model gpt-5-mini
python3 main.py research "Mexicali, Mexico" --model gpt-4o
python3 main.py research "Mexicali, Mexico" --model claude-haiku-4-5-20251001
python3 main.py research "Mexicali, Mexico" --model llama3.1   # requires Ollama

# Compare all models side-by-side
python3 main.py research "Mexicali, Mexico" --compare-models

# Save output
python3 main.py research "Mexicali, Mexico" --output report.md
python3 main.py research "Mexicali, Mexico" --output report.csv
python3 main.py research "Mexicali, Mexico" --output report.pdf

# Batch from file (one location per line)
python3 main.py research --locations-file locations.txt --concurrency 3

# Skip cache for a fresh run
python3 main.py research "Mexicali, Mexico" --no-cache

# Debug mode (shows agent tool calls)
python3 main.py research "Mexicali, Mexico" --verbose

# Cache info
python3 main.py cache-info

# Show active search provider
python3 main.py search-provider

# List supported models
python3 main.py models
```

---

## Live Results

### 20-City Batch — 2026-06-06

Run: `python3 main.py research --locations-file locations.txt --concurrency 3 --model gpt-5-mini`

| Location | Sources | Pass Rate | Latency |
|---|---|---|---|
| Mexicali, Mexico | 2 | **100%** | 150s |
| Monterrey, Mexico | 6 | **100%** | 133s |
| Chandler, Arizona, USA | 6 | **100%** | 116s |
| Phoenix, Arizona, USA | 5 | **100%** | 112s |
| Las Vegas, Nevada, USA | 7 | **100%** | 126s |
| Tucson, Arizona, USA | 6 | **100%** | 133s |
| Riyadh, Saudi Arabia | 4 | **100%** | 166s |
| Cape Town, South Africa | 5 | **100%** | 197s |
| Chennai, India | 4 | **100%** | 286s |
| Bangalore, India | 5 | **100%** | 224s |
| São Paulo, Brazil | 4 | **100%** | 264s |
| Lima, Peru | 5 | **100%** | 178s |
| Cairo, Egypt | 4 | **100%** | 227s |
| Beijing, China | 6 | **100%** | 135s |
| Melbourne, Australia | 6 | **100%** | 127s |
| Karachi, Pakistan | 6 | **100%** | 157s |
| Tehran, Iran | 6 | **100%** | 136s |
| Istanbul, Turkey | 4 | **100%** | 274s |
| Denver, Colorado, USA | 6 | **100%** | 190s |
| Santiago, Chile | 6 | **100%** | 167s |

**20/20 locations · 103 validated sources · 100% pass rate · ~175s avg per location**

Wall time: ~20 minutes for all 20 at concurrency 3.

### Single-Model Comparison — Mexicali, Mexico — 2026-06-05

Run: `python3 main.py research "Mexicali, Mexico" --compare-models`

| Model | Pass Rate | Relevance | Sources | Latency | Cost | Score |
|---|---|---|---|---|---|---|
| `gpt-4o-mini` | **100%** | 6.1/10 | 9 | 70s | **$0.0003** | **76.8** |
| `claude-sonnet-4-6` | **100%** | 6.4/10 | 8 | 193s | $0.0964 | 74.4 |
| `claude-haiku-4-5-20251001` | **100%** | 5.8/10 | 6 | **52s** | $0.0050 | 72.1 |
| `gpt-4o` | **100%** | 6.0/10 | 6 | 83s | $0.0045 | 70.0 |

**All 4 models achieved 100% validation pass rate** — every source excerpt was verified against the live URL.

**Key findings (claude-sonnet-4-6):**

> **💧 Water Stress:** Mexicali faces extreme water stress driven by near-total dependence on the Colorado River and an aquifer declared overexploited by CONAGUA.
>
> **⚠️ Incidents & Conflicts:** In 2020, **76.1% of residents voted to reject a $1.4B Constellation Brands brewery** (Corona, Modelo) over water fears. In 2024–2025, farmers staged protests over unpaid compensation under Colorado River water transfer agreements.
>
> **📋 Regulations:** Industrial users operate under Mexico's National Water Law (LAN). A new General Water Law enacted in late 2025 tightens CONAGUA oversight and requires all in-progress concession procedures to realign.

**Sample validated source:**
```
✅ MATCH FOUND  (similarity: 98.0%)
Title: Mexican city rejects plans for giant US-owned brewery amid water concerns
URL:   https://www.theguardian.com/world/2020/mar/23/mexico-brewery-mexicali-...
Excerpt: "In a weekend plebiscite in the city of Mexicali, 76.1% of voters cast
          ballots against the $1.4bn brewery, being built by Constellation Brands
          to brew beer for export - including Corona, Modelo ..."
```

---

## Architecture

### Why LangChain?

**Provider abstraction.** LangChain's `BaseChatModel` interface works identically for Claude, GPT-4, and Ollama. Every provider speaks a different wire protocol (Anthropic's Messages API, OpenAI's Chat Completions API, Ollama's local HTTP endpoint), but `BaseChatModel` normalizes them into one interface. Switching from `gpt-4o` to `claude-sonnet-4-6` to `llama3.1` is one argument change — the agent loop, tools, and prompts are completely untouched.

**Tool calling is automatic.** The `@tool` decorator on each function generates a JSON schema from the Python type annotations and docstring, then passes that schema to the model via the provider's native tool-use mechanism (OpenAI's `function_call`, Anthropic's `tool_use` blocks, etc.). Without LangChain, you'd write this schema by hand for each provider and maintain them in sync. With LangChain, the schema is always derived from the actual function signature — it can't drift.

**LangGraph handles the ReAct loop.** `create_react_agent` from LangGraph wires the think → act → observe cycle into a directed graph with built-in cycle detection, configurable recursion limits, and full message history. Writing this loop from scratch against raw provider APIs means hand-rolling the message accumulation, tool-result injection, and loop termination — and doing it differently for each provider's message format. LangGraph makes this consistent and observable.

**The comparison is meaningful because the conditions are identical.** Because every model runs through the same agent graph, the same tool implementations, the same prompts, and the same validation pipeline, the multi-model comparison table reflects genuine model capability differences — not implementation differences. This would be impossible if each model had its own integration path.

**Streaming, retries, and callbacks come for free.** `ChatOpenAI(max_retries=3)` and `ChatAnthropic(max_retries=3)` both honor the same interface, so retry logic is configured once and applies everywhere. LangChain's callback system provides a uniform hook for logging, tracing, and cost tracking across all providers without provider-specific instrumentation.

### Search Provider (pluggable)

The tool auto-selects the best available provider via a priority chain:

| Priority | Provider | Cost | Scale |
|---|---|---|---|
| 1 | **SearXNG** (self-hosted) | Free, unlimited | Best for 1,000+ locations |
| 2 | **Brave Search API** | 2,000 free/month | Small batches |
| 3 | **Serper.dev** | 2,500 free, $0.001/q | Medium batches |
| 4 | **DuckDuckGo** (default) | Free, rate-limited | Dev/testing only |

**For scale:** start SearXNG locally and it's auto-detected — no config change needed:
```bash
cd searxng && docker compose up -d
python3 main.py search-provider   # confirms SearXNG is active
```

SearXNG is a self-hosted metasearch engine that fans queries to Google, DuckDuckGo, and Wikipedia simultaneously from your own IP, returning aggregated results with no API key or rate limits. If SearXNG's upstream engines are temporarily rate-limited, the tool automatically falls back to the DuckDuckGo client.

### Agent Loop

The agent uses LangGraph's `create_react_agent` with 4 tools, enforcing a strict workflow per location:

```
search_water_risk (×2 queries per dimension)
  → fetch_and_validate (each URL)
    → record_finding (only if excerpt validated)
      → finish_research (only when ≥2 sources per dimension)
```

All models — Claude, GPT, and Ollama — use the same agent graph. LangChain's `BaseChatModel` interface handles provider differences transparently.

### Validation Pipeline

Each source URL goes through a 3-tier validation check:

| Tier | Method | Threshold |
|------|--------|-----------|
| 1 | Exact substring match | Any match |
| 2 | `rapidfuzz.partial_ratio` + `token_set_ratio` | ≥ 85% |
| 3 | Both fail | → `FAILED VALIDATION` |

For JS-heavy pages (SPAs, Next.js, Angular), the fetcher automatically escalates from `httpx` to headless Playwright.

---

## Anti-Hallucination Techniques

1. **Forced tool flow**: The only way for the model to output a citation is through `record_finding`, which requires a prior `fetch_and_validate` call. Free-form citation is architecturally impossible.

2. **Verbatim excerpt requirement**: Both the system prompt and `record_finding`'s docstring instruct the model to copy the excerpt EXACTLY from what `search_water_risk` returned. The validator then checks for that exact text in the fetched page. A paraphrased excerpt fails validation.

3. **URL reachability pre-check**: Before any excerpt matching, the fetcher verifies the URL returns a 2xx response. A 404 or timeout immediately produces `[FAILED VALIDATION: URL not reachable]`.

4. **Two-source minimum enforced by tool logic**: `finish_research` returns an error to the model if any dimension has fewer than 2 sources, forcing continued searching. The model cannot "finish" with incomplete evidence.

5. **Independent cross-model judge**: The self-critique step uses the cheapest available model (`gpt-4o-mini` if OpenAI key is set, otherwise `claude-haiku`) as an independent judge — never the same model that did the research. This prevents self-serving quality scores.

6. **Failures surfaced, not swallowed**: Every failure produces a labeled `❌ FAILED VALIDATION` entry in the report. Reports are always produced even if partial, so the human reader sees exactly which claims are verified vs. unverified. No silent drops.

---

## Scalability

**1,000 locations requires no new infrastructure.** The real bottleneck is LLM token rate limits and web fetch latency — not compute. From benchmarks: 20 locations at concurrency 3 completes in ~20 minutes (~175s avg per location), putting 1,000 locations at around 2.5 hours at concurrency 3.

```bash
# Run 1,000 locations from a file, save to CSV
python3 main.py research --locations-file locations.txt --concurrency 3 --output results.csv
```

**Recommended concurrency by model:**
- `gpt-5-mini` (500k TPM): concurrency 3–5
- `gpt-4o-mini` (200k TPM): concurrency 2–3
- `claude-*` models: concurrency 3–5
- Ollama (local): concurrency 1–2 (CPU-bound)

If you need more throughput, run this on a VM (`c5.xlarge` or equivalent at ~$0.17/hr) rather than your laptop. No additional services required.

**Search at scale:** The local SearXNG docker instance works for single-machine batches. If running across multiple machines, deploy SearXNG as a shared service and point all workers at it via `SEARXNG_URL=https://your-searxng-host`. Alternatively, Brave Search API (2,000 free/month) or Serper.dev ($0.001/query) both work via environment variable with no code changes.

---

## Robustness

| Challenge | Solution |
|-----------|----------|
| JS-rendered pages | `httpx` → Playwright headless fallback |
| Bot protection | Realistic User-Agent + headers; graceful degradation to `FAILED VALIDATION` |
| Search engine rate limits | SearXNG auto-falls back to DuckDuckGo client when upstream engines are suspended |
| LLM rate limits (429) | `max_retries=3` on model + 30s retry at location level + staggered concurrent starts |
| Model unavailable | Exception caught, labeled error in output — run continues |
| Validation failure | Source flagged `❌`, research continues for alternatives |
| No data available | Dimension summary set to "Data not available" with confidence 0.0 |

---

## Failure Handling

Every failure mode produces a labeled, structured output rather than crashing:

- `❌ FAILED VALIDATION: URL returned HTTP 404` — URL doesn't exist
- `❌ FAILED VALIDATION: URL not reachable: Connection timeout` — network error
- `❌ FAILED VALIDATION: Page returned empty content` — JS page that Playwright couldn't render
- `❌ FAILED VALIDATION: Excerpt not found in source content (best similarity: 62.3%)` — hallucinated or paraphrased excerpt

---

## Running Tests

```bash
python3 -m pytest tests/ -v
```

14 tests covering: query building, excerpt validation (exact + fuzzy + failure modes), and tool accumulation logic.

---

## Project Structure

```
waterplan-research/
├── main.py                  # CLI entrypoint
├── locations.txt            # Example batch input file
├── searxng/                 # Self-hosted SearXNG (docker compose up -d)
│   ├── docker-compose.yml
│   └── core-config/
│       └── settings.yml
├── waterplan/
│   ├── config.py            # Settings + model factory (get_model())
│   ├── cli.py               # Typer CLI commands
│   ├── models/schemas.py    # All Pydantic data models
│   ├── agent/
│   │   ├── research_agent.py  # LangGraph agent runner
│   │   ├── tools.py           # @tool functions: search, validate, record, finish
│   │   ├── prompts.py         # System prompt
│   │   └── self_critic.py     # Cross-model source quality judge
│   ├── search/
│   │   ├── provider.py        # Auto-selects best available search provider
│   │   ├── searxng_client.py  # SearXNG client with DDG fallback
│   │   ├── ddg_client.py      # DuckDuckGo (free, no API key)
│   │   ├── brave_client.py    # Brave Search API
│   │   ├── serper_client.py   # Serper.dev
│   │   └── query_builder.py   # Dimension-specific query templates
│   ├── validation/
│   │   ├── fetcher.py         # httpx + Playwright fallback fetcher
│   │   └── validator.py       # 3-tier excerpt matching
│   ├── comparison/
│   │   ├── runner.py          # Multi-model parallel comparison
│   │   └── scorer.py          # Weighted quality scoring
│   ├── cache/store.py         # diskcache wrapper with TTL
│   └── output/
│       ├── markdown.py        # Markdown/console renderer
│       ├── csv_writer.py      # CSV export (pandas)
│       └── pdf_generator.py   # PDF via WeasyPrint + Jinja2
└── tests/                   # pytest unit tests
```

---

## Supported Models

| Model | Provider | Notes |
|-------|----------|-------|
| `claude-sonnet-4-6` | Anthropic | Default. Best quality. |
| `claude-haiku-4-5-20251001` | Anthropic | Fastest Claude, cheapest |
| `gpt-5-mini` | OpenAI | 500k TPM Tier 1 — recommended for batches |
| `gpt-4o` | OpenAI | Best OpenAI quality |
| `gpt-4o-mini` | OpenAI | Fast, cheap (200k TPM Tier 1) |
| `llama3.1` | Ollama (local) | Requires `ollama pull llama3.1` |
| `qwen2.5` | Ollama (local) | Requires `ollama pull qwen2.5` |
| `mistral` | Ollama (local) | Requires `ollama pull mistral` |
