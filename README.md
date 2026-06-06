# Waterplan Research Tool

Automated water risk intelligence for industrial locations. Given a list of locations, the tool researches three dimensions per location — **water stress**, **incidents & conflicts**, and **regulations** — using multiple web sources, then validates every claim by fetching and checking the cited URL.

Built with **LangChain**, runs against **OpenAI**, **Anthropic Claude**, or **local Ollama** models interchangeably.

---

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/waterplan-research
cd waterplan-research

pip install -r requirements.txt
playwright install chromium   # for JS-heavy pages

cp .env.example .env
# Edit .env and add your API keys

python3 main.py "Mexicali, Mexico" "Monterrey, Mexico" "Chandler, Arizona, USA"
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

By default the tool uses DuckDuckGo, which is rate-limited and unsuitable for large batches. SearXNG is a self-hosted metasearch engine that fans queries to Google, Bing, DuckDuckGo, and Wikipedia simultaneously — free, unlimited, no API key needed.

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
python3 main.py "Mexicali, Mexico" --model llama3.1
```

---

## Usage

```bash
# Research 3 locations with default model (claude-sonnet-4-6)
python3 main.py "Mexicali, Mexico" "Monterrey, Mexico" "Chandler, Arizona, USA"

# Use a specific model
python3 main.py "Mexicali, Mexico" --model gpt-4o
python3 main.py "Mexicali, Mexico" --model claude-haiku-4-5-20251001
python3 main.py "Mexicali, Mexico" --model llama3.1   # requires Ollama

# Compare all models side-by-side
python3 main.py "Mexicali, Mexico" --compare-models

# Save output
python3 main.py "Mexicali, Mexico" --output report.md
python3 main.py "Mexicali, Mexico" --output report.csv
python3 main.py "Mexicali, Mexico" --output report.pdf

# Batch from file (one location per line)
python3 main.py --locations-file locations.txt --concurrency 5

# Skip cache for a fresh run
python3 main.py "Mexicali, Mexico" --no-cache

# Debug mode (shows agent tool calls)
python3 main.py "Mexicali, Mexico" --verbose

# Cache info
python3 main.py cache-info

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

LangChain provides a single `BaseChatModel` interface that works identically for Claude, GPT-4, and Ollama. The agent loop, tool definitions, and prompts are **provider-agnostic** — only the model instantiation changes (one line in `config.py`). This makes the tool genuinely portable and allows meaningful multi-model comparison.

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
docker run -d -p 8080:8080 searxng/searxng
python3 main.py search-provider   # confirms SearXNG is active
```

SearXNG is a self-hosted metasearch engine: it fans your query out to Google, Bing, DuckDuckGo, and Wikipedia simultaneously from your own IP, returning aggregated JSON with no API key or rate limits.

### Cross-Model Tool Calling Strategy

Not all models support structured tool calling. The agent auto-detects capability at runtime:

1. **Tool calling** (`claude-sonnet`, `claude-haiku`, `gpt-4o`, `gpt-4o-mini`, `llama3.1`): Uses LangChain's `create_tool_calling_agent` — the model receives structured tool schemas and returns structured tool calls.
2. **ReAct fallback** (older Ollama models): Uses `create_react_agent` — text-based Thought/Action/Observation loop with the same tool set. Same validation guarantees, different interaction pattern.

The agent flow for each location:
```
search_water_risk (×2 queries)
  → fetch_and_validate (each URL)
    → record_finding (only if validated)
      × repeat for incidents and regulations
        → finish_research (only if ≥2 sources/dim)
```

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

5. **Independent cross-model judge**: The self-critique step always uses `claude-haiku-4-5-20251001` regardless of which model did the research. This prevents the main model from scoring its own outputs favorably. The judge evaluates relevance, recency, and authority per source.

6. **Failures surfaced, not swallowed**: Every failure produces a labeled `❌ FAILED VALIDATION` entry in the report. Reports are always produced even if partial, so the human reader sees exactly which claims are verified vs. unverified. No silent drops.

---

## Scalability

**1,000 locations requires no new infrastructure.** The real bottleneck is LLM token rate limits and web fetch latency — not compute. A single machine with `--concurrency 20` runs ~1,000 locations in roughly 1 hour, streaming results to CSV as they complete.

```bash
# Run 1,000 locations from a file, 20 in parallel, save to CSV
python3 main.py research --locations-file locations.txt --concurrency 20 --output results.csv
```

If you need more throughput, run this on a VM (`c5.xlarge` or equivalent at ~$0.17/hr) rather than your laptop. No additional services required.

**Search at scale:** The local SearXNG docker instance works for single-machine batches. If running across multiple machines, deploy SearXNG as a shared service and point all workers at it via `SEARXNG_URL=https://your-searxng-host`. Alternatively, Brave Search API (2,000 free/month) or Serper.dev ($0.001/query) both work via environment variable with no code changes.

**Rate limiting built in:** DuckDuckGo client retries with exponential backoff. LLM calls via LangChain handle provider rate limits natively.

---

## Robustness

| Challenge | Solution |
|-----------|----------|
| JS-rendered pages | `httpx` → Playwright headless fallback |
| Bot protection | Realistic User-Agent + headers; graceful degradation to `FAILED VALIDATION` |
| Rate limiting (DDG) | Exponential backoff, 3 retries |
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
├── waterplan/
│   ├── config.py            # Settings + model factory (get_model())
│   ├── cli.py               # Typer CLI commands
│   ├── models/schemas.py    # All Pydantic data models
│   ├── agent/
│   │   ├── research_agent.py  # LangChain agent builder + runner
│   │   ├── tools.py           # @tool functions: search, validate, record, finish
│   │   ├── prompts.py         # System prompt + ReAct prompt template
│   │   └── self_critic.py     # Cross-model source quality judge
│   ├── search/
│   │   ├── ddg_client.py      # DuckDuckGo search (free, no API key)
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
| `gpt-4o` | OpenAI | Best OpenAI quality |
| `gpt-4o-mini` | OpenAI | Fast, cheap OpenAI |
| `llama3.1` | Ollama (local) | Requires `ollama pull llama3.1` |
| `qwen2.5` | Ollama (local) | Requires `ollama pull qwen2.5` |
| `mistral` | Ollama (local) | ReAct fallback mode |
