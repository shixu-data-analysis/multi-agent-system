# Multi-Agent AI News Pipeline (v2)

This project implements a hybrid AI news pipeline that automates the process of fetching, filtering, tagging, and storing AI-related articles from RSS feeds. It leverages the `google-adk` library to orchestrate multiple AI agents and tools.

## Workflow

The pipeline executes in three distinct phases:

### Phase 1: Fetch & Dedup
**Agents:** Orchestrator (using FunctionTools)
1.  **Fetch:** The pipeline accepts a list of RSS feed URLs.
2.  **Deduplicate:** It fetches articles from these feeds and uses a deduplication tool to remove duplicate entries based on content and metadata.
3.  **Output:** A list of unique, raw articles.

### Phase 2: Filter & Tag
**Agents:** SequentialAgent (Filter Agent → Tagging Agent)
**Concurrency:** Articles are processed concurrently (configurable limit) to optimize performance.

For each article:
1.  **Filter Agent:** Analyzes the article content to determine if it is related to Artificial Intelligence.
    *   If **Not AI**: The article is discarded.
    *   If **AI**: The article proceeds to the next step.
2.  **Tagging Agent:** Generates relevant tags for the AI article.

**Output:** A list of filtered, AI-focused articles with generated tags.

### Phase 3: Storage
**Agents:** Orchestrator (using FunctionTools)
1.  **Store:** The processed articles are passed to a storage tool (e.g., saving to a database or file).
2.  **Output:** Confirmation of stored articles.

## Architecture

*   **Hybrid Approach:** Combines `FunctionTools` for utility tasks (fetching, storage) with `SequentialAgent` for complex cognitive tasks (filtering, tagging).
*   **Orchestrator:** Coordinates high-level phases and tool usage.
*   **Concurrency:** Uses `asyncio` to process multiple articles in parallel during the computationally intensive Filter & Tag phase.
*   **Resilience:** Implements retry logic for API calls.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables:**
    Ensure you have a `.env` file configured with the necessary API keys (e.g., `GOOGLE_API_KEY`).

## Usage

To run the pipeline with the default feed configuration:

```bash
python main.py
```

You can modify the `feeds` list in `main.py` to customize the sources.
