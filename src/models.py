"""Pydantic models for AI/ML Intelligence Scraper input validation and output formatting."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator


# --- Input Models ---


class ScrapingMode(str, Enum):
    SEARCH_MODELS = "search_models"
    SEARCH_PAPERS = "search_papers"
    TRENDING_PAPERS = "trending_papers"


class ModelSort(str, Enum):
    DOWNLOADS = "downloads"
    LIKES = "likes"
    TRENDING = "trending"


class PaperSort(str, Enum):
    RELEVANCE = "relevance"
    SUBMITTED_DATE = "submittedDate"
    LAST_UPDATED_DATE = "lastUpdatedDate"


class ScraperInput(BaseModel):
    """Validated scraper input from Apify."""

    mode: ScrapingMode = ScrapingMode.SEARCH_MODELS

    # Search filters
    query: str = ""
    sort: str = "downloads"

    # Model-specific filters
    pipeline_tag: str = ""
    library_filter: str = ""

    # Paper-specific filters
    arxiv_category: str = ""
    author: str = ""
    date_from: str = ""
    date_to: str = ""

    # General settings
    max_results: int = 100

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_date(cls, v: str) -> str:
        v = v.strip()
        if v and not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1:
            return 1
        if v > 10000:
            return 10000
        return v

    @classmethod
    def from_actor_input(cls, raw: dict[str, Any]) -> ScraperInput:
        """Map Apify input schema field names to model field names."""
        return cls(
            mode=raw.get("mode", "search_models"),
            query=raw.get("query", ""),
            sort=raw.get("sort", "downloads"),
            pipeline_tag=raw.get("pipelineTag", ""),
            library_filter=raw.get("libraryFilter", ""),
            arxiv_category=raw.get("arxivCategory", ""),
            author=raw.get("author", ""),
            date_from=raw.get("dateFrom", ""),
            date_to=raw.get("dateTo", ""),
            max_results=raw.get("maxResults", 100),
        )

    def validate_for_mode(self) -> str | None:
        """Return an error message if input is invalid for the selected mode."""
        if self.mode == ScrapingMode.SEARCH_MODELS and not self.query:
            return "A search query is required for 'Search Models' mode."
        if self.mode == ScrapingMode.SEARCH_PAPERS:
            if not self.query and not self.arxiv_category and not self.author:
                return (
                    "At least one filter is required for 'Search Papers' mode: "
                    "query, arXiv category, or author."
                )
        # trending_papers needs no query -- it fetches the daily feed
        return None


# --- Output Formatting ---


def format_model(data: dict[str, Any]) -> dict[str, Any]:
    """Format a HuggingFace model API response into clean output."""
    model_id = data.get("modelId", data.get("id", ""))

    # Extract tags
    tags = data.get("tags", [])

    # Extract library name -- can be in library_name or tags
    library = data.get("library_name", "")
    if not library:
        # Check tags for known libraries
        known_libs = {
            "transformers", "diffusers", "pytorch", "tensorflow", "jax",
            "onnx", "safetensors", "gguf", "spacy", "keras", "sklearn",
            "sentence-transformers", "peft", "adapter-transformers",
        }
        for tag in tags:
            if tag in known_libs:
                library = tag
                break

    return {
        "type": "model",
        "modelId": model_id,
        "author": model_id.split("/")[0] if "/" in model_id else "",
        "modelName": model_id.split("/")[-1] if "/" in model_id else model_id,
        "pipelineTag": data.get("pipeline_tag", ""),
        "library": library,
        "downloads": data.get("downloads", 0),
        "downloadsAllTime": data.get("downloadsAllTime", 0),
        "likes": data.get("likes", 0),
        "trending": data.get("trendingScore", 0),
        "tags": tags,
        "lastModified": data.get("lastModified", ""),
        "createdAt": data.get("createdAt", ""),
        "private": data.get("private", False),
        "gated": data.get("gated", False),
        "url": f"https://huggingface.co/{model_id}",
    }


def format_arxiv_paper(entry: ET.Element) -> dict[str, Any]:
    """Format an arXiv Atom feed entry into clean output.

    arXiv API returns Atom XML. Each entry has namespaced fields.
    """
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    # Extract ID (e.g. http://arxiv.org/abs/2401.12345v1 -> 2401.12345)
    raw_id = _get_text(entry, "atom:id", ns)
    arxiv_id = ""
    if raw_id:
        # Strip version and extract just the ID
        match = re.search(r"(\d{4}\.\d{4,5})", raw_id)
        if match:
            arxiv_id = match.group(1)

    # Extract authors
    authors = []
    for author_elem in entry.findall("atom:author", ns):
        name = _get_text(author_elem, "atom:name", ns)
        if name:
            authors.append(name)

    # Extract categories
    categories = []
    for cat_elem in entry.findall("atom:category", ns):
        term = cat_elem.get("term", "")
        if term:
            categories.append(term)

    # Primary category
    primary_cat_elem = entry.find("arxiv:primary_category", ns)
    primary_category = ""
    if primary_cat_elem is not None:
        primary_category = primary_cat_elem.get("term", "")

    # Extract links
    pdf_link = ""
    abs_link = ""
    for link_elem in entry.findall("atom:link", ns):
        href = link_elem.get("href", "")
        title = link_elem.get("title", "")
        link_type = link_elem.get("type", "")
        if title == "pdf" or href.endswith(".pdf"):
            pdf_link = href
        elif link_type == "text/html" or "/abs/" in href:
            abs_link = href

    # Clean up summary (remove excessive whitespace)
    summary = _get_text(entry, "atom:summary", ns)
    if summary:
        summary = re.sub(r"\s+", " ", summary).strip()

    title = _get_text(entry, "atom:title", ns)
    if title:
        title = re.sub(r"\s+", " ", title).strip()

    # Extract comment (often has page count, conference info)
    comment = _get_text(entry, "arxiv:comment", ns)

    return {
        "type": "paper",
        "source": "arxiv",
        "arxivId": arxiv_id,
        "title": title,
        "summary": summary,
        "authors": ", ".join(authors),
        "authorList": authors,
        "publishedDate": _get_text(entry, "atom:published", ns),
        "updatedDate": _get_text(entry, "atom:updated", ns),
        "primaryCategory": primary_category,
        "categories": ", ".join(categories),
        "categoryList": categories,
        "comment": comment or "",
        "pdfUrl": pdf_link,
        "url": abs_link or f"https://arxiv.org/abs/{arxiv_id}",
    }


def format_hf_paper(data: dict[str, Any]) -> dict[str, Any]:
    """Format a HuggingFace daily paper into clean output."""
    paper = data.get("paper", {}) or {}
    arxiv_id = paper.get("id", "")

    # Authors -- HuggingFace daily papers may have author info
    authors = []
    for author in paper.get("authors", []):
        name = author.get("name", "")
        if name:
            authors.append(name)

    # AI summary and keywords (HuggingFace adds these)
    ai_summary = paper.get("ai_summary", "") or ""
    ai_keywords = paper.get("ai_keywords", []) or []

    # Submitted by user info
    submitted_by = data.get("submittedBy", {}) or {}
    submitter_name = submitted_by.get("fullname", "") or submitted_by.get("user", "")

    return {
        "type": "paper",
        "source": "huggingface_daily",
        "arxivId": arxiv_id,
        "title": paper.get("title", ""),
        "summary": paper.get("summary", ""),
        "authors": ", ".join(authors),
        "authorList": authors,
        "publishedDate": paper.get("publishedAt", ""),
        "upvotes": paper.get("upvotes", data.get("upvotes", 0)),
        "numComments": data.get("numComments", 0),
        "aiSummary": ai_summary,
        "aiKeywords": ai_keywords,
        "submittedBy": submitter_name,
        "mediaUrl": data.get("mediaUrl", ""),
        "pdfUrl": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
        "url": f"https://huggingface.co/papers/{arxiv_id}" if arxiv_id else "",
    }


def _get_text(element: ET.Element, tag: str, ns: dict[str, str]) -> str:
    """Safely extract text from an XML element."""
    child = element.find(tag, ns)
    if child is not None and child.text:
        return child.text.strip()
    return ""
