# AI/ML Intelligence Scraper

Search AI/ML models, research papers, and trending papers from HuggingFace Hub and arXiv -- structured, filterable, and ready for analysis. No API key required.

## What does it do?

AI/ML Intelligence Scraper pulls structured data from HuggingFace Hub and arXiv, the two largest open sources for machine learning models and AI research. You provide search filters and it returns clean, structured data.

**Use cases:**

- **ML engineering** -- find models by task, framework, and popularity for integration into your pipeline
- **Research tracking** -- monitor new papers in specific AI subfields (NLP, computer vision, robotics, etc.)
- **Competitive intelligence** -- track trending models and papers to understand where the industry is moving
- **Investment research** -- identify emerging AI capabilities and technology trends from publication patterns
- **Content creation** -- aggregate trending AI research for newsletters, reports, and media coverage
- **Academic research** -- search arXiv by author, category, date range, and keyword

## Features

- **3 modes:** search models (HuggingFace), search papers (arXiv), trending papers (HuggingFace Daily Papers)
- **No API key required** -- all data sources are public
- **No proxies needed** -- direct API access to public academic and ML infrastructure
- **Model search filters:** keyword, pipeline task (25 tasks), ML framework (14 libraries), sort by downloads/likes/trending
- **Paper search filters:** keyword, arXiv category (13 AI/ML categories), author name, date range (YYYY-MM-DD), sort by relevance/date
- **Trending papers** with HuggingFace community upvotes, AI-generated summaries, and AI keywords
- **Automatic pagination** through results (up to 10,000 records)
- **Rate limiting** built in (0.5-second interval between requests)
- **Retry logic** with exponential backoff on failures
- **State persistence** -- survives Apify actor migrations mid-run

## What data does it extract?

### Models (HuggingFace Hub)

| Field | Description |
|-------|-------------|
| `type` | Always `"model"` |
| `modelId` | Full model ID (e.g. `meta-llama/Llama-3.1-8B`) |
| `author` | Model author/organization |
| `modelName` | Model name without author prefix |
| `pipelineTag` | Task type (text-generation, image-classification, etc.) |
| `library` | ML framework (transformers, diffusers, pytorch, etc.) |
| `downloads` | Recent download count |
| `downloadsAllTime` | All-time download count |
| `likes` | Community likes |
| `trending` | Trending score |
| `tags` | All model tags |
| `lastModified` | Last update timestamp |
| `createdAt` | Creation timestamp |
| `private` | Whether the model is private |
| `gated` | Whether the model requires access approval |
| `url` | Direct link to HuggingFace model page |

### Papers (arXiv)

| Field | Description |
|-------|-------------|
| `type` | Always `"paper"` |
| `source` | `"arxiv"` |
| `arxivId` | arXiv paper ID (e.g. `2401.12345`) |
| `title` | Paper title |
| `summary` | Paper abstract |
| `authors` | Comma-separated author names |
| `authorList` | Array of author names |
| `publishedDate` | Publication date (ISO format) |
| `updatedDate` | Last updated date (ISO format) |
| `primaryCategory` | Primary arXiv category (e.g. `cs.CL`) |
| `categories` | All categories (comma-separated) |
| `categoryList` | Array of categories |
| `comment` | Author comment (often has page count, conference info) |
| `pdfUrl` | Direct link to PDF |
| `url` | Link to arXiv abstract page |

### Trending Papers (HuggingFace Daily Papers)

| Field | Description |
|-------|-------------|
| `type` | Always `"paper"` |
| `source` | `"huggingface_daily"` |
| `arxivId` | arXiv paper ID |
| `title` | Paper title |
| `summary` | Paper abstract |
| `authors` | Comma-separated author names |
| `authorList` | Array of author names |
| `publishedDate` | Publication date |
| `upvotes` | HuggingFace community upvotes |
| `numComments` | Number of community comments |
| `aiSummary` | AI-generated summary (when available) |
| `aiKeywords` | AI-generated keywords (when available) |
| `submittedBy` | HuggingFace user who submitted the paper |
| `mediaUrl` | Media/thumbnail URL |
| `pdfUrl` | Direct link to PDF |
| `url` | Link to HuggingFace paper page |

---

## Input

Choose a scraping mode and provide your search filters.

### Mode 1: Search Models

Search HuggingFace Hub for ML models by keyword, task, and framework.

```json
{
    "mode": "search_models",
    "query": "large language model",
    "sort": "downloads",
    "maxResults": 100
}
```

Filter by pipeline task and framework:

```json
{
    "mode": "search_models",
    "query": "stable diffusion",
    "pipelineTag": "text-to-image",
    "libraryFilter": "diffusers",
    "sort": "likes",
    "maxResults": 50
}
```

### Mode 2: Search Papers

Search arXiv for AI/ML research papers.

```json
{
    "mode": "search_papers",
    "query": "transformer attention mechanism",
    "arxivCategory": "cs.CL",
    "sort": "submittedDate",
    "maxResults": 100
}
```

Search by author and date range:

```json
{
    "mode": "search_papers",
    "author": "Yann LeCun",
    "dateFrom": "2025-01-01",
    "dateTo": "2026-01-01",
    "sort": "submittedDate",
    "maxResults": 50
}
```

### Mode 3: Trending Papers

Get today's trending AI papers from HuggingFace with community engagement data.

```json
{
    "mode": "trending_papers",
    "maxResults": 50
}
```

Filter trending papers by keyword:

```json
{
    "mode": "trending_papers",
    "query": "language model",
    "maxResults": 20
}
```

### Search Filters

**Model filters (Mode 1):**

| Parameter | Description |
|-----------|-------------|
| `query` | Search keyword (required for model search) |
| `pipelineTag` | Filter by task: text-generation, text-classification, image-classification, text-to-image, automatic-speech-recognition, and 20 more |
| `libraryFilter` | Filter by framework: transformers, diffusers, pytorch, tensorflow, jax, onnx, gguf, spacy, keras, sklearn, and more |
| `sort` | Sort by: `downloads`, `likes`, or `trending` |

**Paper filters (Mode 2):**

| Parameter | Description |
|-----------|-------------|
| `query` | Search keyword (searches titles and abstracts) |
| `arxivCategory` | arXiv category: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.RO, cs.IR, cs.MA, stat.ML, cs.SD, eess.AS, cs.HC, cs.CR |
| `author` | Author name |
| `dateFrom` | Filter papers from this date (YYYY-MM-DD) |
| `dateTo` | Filter papers up to this date (YYYY-MM-DD) |
| `sort` | Sort by: `relevance`, `submittedDate`, or `lastUpdatedDate` |

**Trending paper filters (Mode 3):**

| Parameter | Description |
|-----------|-------------|
| `query` | Optional keyword to filter trending papers by title/abstract |

**General settings:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `maxResults` | `100` | Maximum results to return (max 10,000). Free users are limited to 25 per run. |

---

## Output

Results are saved to the default dataset. Download them in JSON, CSV, Excel, or XML format from the Output tab.

### Example: Model output

```json
{
    "type": "model",
    "modelId": "meta-llama/Llama-3.1-8B-Instruct",
    "author": "meta-llama",
    "modelName": "Llama-3.1-8B-Instruct",
    "pipelineTag": "text-generation",
    "library": "transformers",
    "downloads": 12500000,
    "downloadsAllTime": 45000000,
    "likes": 8500,
    "trending": 42,
    "tags": ["transformers", "pytorch", "safetensors", "llama", "text-generation"],
    "lastModified": "2026-01-15T10:30:00.000Z",
    "createdAt": "2025-07-23T00:00:00.000Z",
    "private": false,
    "gated": true,
    "url": "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct"
}
```

### Example: arXiv paper output

```json
{
    "type": "paper",
    "source": "arxiv",
    "arxivId": "2401.12345",
    "title": "Attention Is All You Need: A Retrospective Analysis",
    "summary": "We revisit the transformer architecture and analyze its impact...",
    "authors": "Jane Smith, John Doe, Alice Johnson",
    "authorList": ["Jane Smith", "John Doe", "Alice Johnson"],
    "publishedDate": "2026-01-15T12:00:00Z",
    "updatedDate": "2026-01-20T08:00:00Z",
    "primaryCategory": "cs.CL",
    "categories": "cs.CL, cs.AI, cs.LG",
    "categoryList": ["cs.CL", "cs.AI", "cs.LG"],
    "comment": "15 pages, 8 figures. Accepted at ICML 2026",
    "pdfUrl": "https://arxiv.org/pdf/2401.12345",
    "url": "https://arxiv.org/abs/2401.12345"
}
```

### Example: Trending paper output

```json
{
    "type": "paper",
    "source": "huggingface_daily",
    "arxivId": "2401.67890",
    "title": "Scaling Laws for Neural Machine Translation",
    "summary": "We present new scaling laws that predict performance of...",
    "authors": "Alice Researcher, Bob Scientist",
    "authorList": ["Alice Researcher", "Bob Scientist"],
    "publishedDate": "2026-02-14T00:00:00Z",
    "upvotes": 142,
    "numComments": 23,
    "aiSummary": "This paper establishes new scaling laws for NMT systems...",
    "aiKeywords": ["scaling laws", "machine translation", "large language models"],
    "submittedBy": "AkitoP",
    "mediaUrl": "https://cdn-thumbnails.huggingface.co/social-thumbnails/papers/2401.67890.png",
    "pdfUrl": "https://arxiv.org/pdf/2401.67890",
    "url": "https://huggingface.co/papers/2401.67890"
}
```

---

## Cost

This actor uses **pay-per-event (PPE) pricing**. You pay only for the results you get.

- **$0.50 per 1,000 results** ($0.0005 per result)
- **No proxy costs** -- public APIs, no proxies needed
- **No API key costs** -- all data sources are free
- Free tier: **25 results per run** (no subscription required)

Requests to HuggingFace and arXiv are fast. A typical run fetching 100 items completes in under a minute.

---

## Technical details

- HuggingFace Hub API (`huggingface.co/api/models`) for model search -- returns JSON, offset pagination, 100 per page
- arXiv API (`export.arxiv.org/api/query`) for paper search -- returns Atom XML, offset pagination, 200 per page
- HuggingFace Daily Papers API (`huggingface.co/api/daily_papers`) for trending papers -- returns JSON, offset pagination
- Client-side date filtering for arXiv papers (arXiv API does not support date range natively)
- Rate limited to 1 request per 0.5 seconds
- Automatic retry with exponential backoff on failures
- Results pushed in batches of 25 for efficiency
- Actor state persisted across migrations
- No proxies, no browser, no cookies -- direct API access

---

## Limitations

- arXiv date filtering is client-side: the API returns results ordered by relevance or date, and papers outside the specified date range are skipped. For large date ranges this is efficient, but for very narrow ranges you may need to increase `maxResults` to get enough matches.
- Maximum pagination depth is 10,000 results per run (arXiv hard limit).
- HuggingFace trending papers are a daily feed -- the total available on any given day is typically 20-50 papers.
- arXiv paper summaries (abstracts) can be long. They are included in full.
- HuggingFace AI summaries and keywords are not available for all daily papers.

---

## FAQ

### Do I need an API key?

No. All three data sources (HuggingFace Hub, arXiv, HuggingFace Daily Papers) are fully public APIs with no authentication required.

### What are arXiv categories?

arXiv organizes papers into categories. The most relevant for AI/ML research:
- **cs.AI** -- Artificial Intelligence (general)
- **cs.LG** -- Machine Learning
- **cs.CL** -- Computation and Language (NLP, LLMs)
- **cs.CV** -- Computer Vision
- **cs.NE** -- Neural and Evolutionary Computing
- **cs.RO** -- Robotics
- **stat.ML** -- Machine Learning (from a statistics perspective)

### What are pipeline tags?

HuggingFace categorizes models by the task they perform. Common examples: `text-generation` (LLMs), `text-to-image` (Stable Diffusion), `text-classification` (sentiment analysis), `automatic-speech-recognition` (Whisper), `feature-extraction` (embeddings).

### Can I combine filters?

Yes. For model search, you can combine keyword + pipeline task + framework. For paper search, you can combine keyword + category + author + date range. All filters are AND-combined.

### How current is the trending papers data?

HuggingFace Daily Papers updates throughout the day. The trending feed reflects papers that the HuggingFace community is currently engaging with.

### Can I use this with the Apify API?

Yes. Call the actor via the Apify API and retrieve results programmatically in JSON, CSV, or other formats. Works with the Apify Python and JavaScript clients.

---

## Feedback

Found a bug or have a feature request? Open an issue on the actor's Issues tab in Apify Console.
