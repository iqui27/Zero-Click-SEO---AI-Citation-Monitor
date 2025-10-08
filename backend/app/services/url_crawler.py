"""
URL Crawler Service

Crawls URLs to extract metadata (title, meta tags, Open Graph, AI-ready structures).
"""

from typing import Optional, Dict, Any, List
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.orm import Session
import re
from urllib.parse import urlparse

from app.models.models import UrlMetadata
from app.services.normalization import normalize_domain


def check_special_files(domain: str, timeout: int = 3) -> Dict[str, Any]:
    """
    Check for special files like llms.txt, ai.txt, robots.txt, etc.
    
    Returns dict with:
        - llms_txt: content if exists
        - ai_txt: content if exists
        - robots_txt: content if exists
    """
    special_files = {
        "llms_txt": None,
        "ai_txt": None,
        "robots_txt": None,
    }
    
    base_url = f"https://{domain}"
    files_to_check = [
        ("llms_txt", f"{base_url}/llms.txt"),
        ("llms_txt", f"{base_url}/.well-known/llms.txt"),
        ("ai_txt", f"{base_url}/ai.txt"),
        ("ai_txt", f"{base_url}/.well-known/ai.txt"),
        ("robots_txt", f"{base_url}/robots.txt"),
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SEOAnalyzerBot/1.0; +https://seoanalyzer.com/bot)"
    }
    
    for key, file_url in files_to_check:
        if special_files[key]:  # Skip if already found
            continue
            
        try:
            response = requests.get(file_url, timeout=timeout, headers=headers, allow_redirects=True)
            if response.status_code == 200:
                content = response.text[:10000]  # Limit to 10KB
                special_files[key] = content
        except:
            pass
    
    return special_files


def crawl_url(url: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Crawl a single URL and extract metadata.
    
    Returns dict with:
        - status: "success" | "error"
        - http_status_code: int
        - title, meta_description, meta_keywords, meta_robots
        - og_tags: dict
        - has_structured_data, has_faq_schema, has_lists, has_tables
        - error_message (if error)
    """
    result = {
        "status": "error",
        "http_status_code": None,
        "title": None,
        "meta_description": None,
        "meta_keywords": None,
        "meta_robots": None,
        "og_tags": {},
        "has_structured_data": False,
        "has_faq_schema": False,
        "has_lists": False,
        "has_tables": False,
        "error_message": None,
    }
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SEOAnalyzerBot/1.0; +https://seoanalyzer.com/bot)"
        }
        
        response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        result["http_status_code"] = response.status_code
        
        if response.status_code != 200:
            result["error_message"] = f"HTTP {response.status_code}"
            return result
        
        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Extract title
        title_tag = soup.find("title")
        if title_tag:
            result["title"] = title_tag.get_text(strip=True)[:500]
        
        # Extract meta tags
        meta_description = soup.find("meta", attrs={"name": "description"})
        if meta_description:
            result["meta_description"] = meta_description.get("content", "")[:1000]
        
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords:
            result["meta_keywords"] = meta_keywords.get("content", "")[:500]
        
        meta_robots = soup.find("meta", attrs={"name": "robots"})
        if meta_robots:
            result["meta_robots"] = meta_robots.get("content", "")[:200]
        
        # Extract Open Graph tags
        og_tags = {}
        for meta in soup.find_all("meta", property=re.compile(r"^og:")):
            prop = meta.get("property")
            content = meta.get("content")
            if prop and content:
                og_tags[prop] = content[:500]
        result["og_tags"] = og_tags
        
        # Detect AI-ready structures
        
        # Structured data (JSON-LD, Microdata)
        json_ld = soup.find_all("script", type="application/ld+json")
        result["has_structured_data"] = len(json_ld) > 0
        
        # FAQ Schema
        if json_ld:
            for script in json_ld:
                if "FAQPage" in script.string or "Question" in script.string:
                    result["has_faq_schema"] = True
                    break
        
        # Lists (ul, ol with multiple items)
        lists = soup.find_all(["ul", "ol"])
        for lst in lists:
            items = lst.find_all("li")
            if len(items) >= 3:  # At least 3 items to be considered a meaningful list
                result["has_lists"] = True
                break
        
        # Tables
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) >= 2:  # At least header + 1 row
                result["has_tables"] = True
                break
        
        result["status"] = "success"
        
    except requests.Timeout:
        result["error_message"] = "Timeout"
    except requests.RequestException as e:
        result["error_message"] = f"Request error: {str(e)[:200]}"
    except Exception as e:
        result["error_message"] = f"Parse error: {str(e)[:200]}"
    
    return result


def crawl_and_save_url(db: Session, url: str) -> UrlMetadata:
    """
    Crawl a URL and save/update metadata in database.
    
    Returns the UrlMetadata object.
    """
    parsed_url = urlparse(url)
    domain = normalize_domain(parsed_url.netloc)
    
    # Check if already exists
    existing = db.query(UrlMetadata).filter(UrlMetadata.url == url).first()
    
    # Crawl URL
    crawl_result = crawl_url(url)
    
    # Check for special files (only if this is the first URL for this domain)
    special_files = {"llms_txt": None, "ai_txt": None, "robots_txt": None}
    domain_urls = db.query(UrlMetadata).filter(UrlMetadata.domain == domain).count()
    if domain_urls == 0 or (existing and not existing.llms_txt and not existing.ai_txt):
        special_files = check_special_files(domain)
    
    if existing:
        # Update existing
        existing.domain = domain
        existing.title = crawl_result["title"]
        existing.meta_description = crawl_result["meta_description"]
        existing.meta_keywords = crawl_result["meta_keywords"]
        existing.meta_robots = crawl_result["meta_robots"]
        existing.og_tags = crawl_result["og_tags"]
        existing.has_structured_data = crawl_result["has_structured_data"]
        existing.has_faq_schema = crawl_result["has_faq_schema"]
        existing.has_lists = crawl_result["has_lists"]
        existing.has_tables = crawl_result["has_tables"]
        existing.status = crawl_result["status"]
        existing.error_message = crawl_result["error_message"]
        existing.http_status_code = crawl_result["http_status_code"]
        existing.crawled_at = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
        
        # Update special files if found (and if columns exist)
        try:
            if special_files["llms_txt"]:
                existing.llms_txt = special_files["llms_txt"]
            if special_files["ai_txt"]:
                existing.ai_txt = special_files["ai_txt"]
            if special_files["robots_txt"]:
                existing.robots_txt_full = special_files["robots_txt"]
        except AttributeError:
            pass  # Columns don't exist yet
        
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        metadata = UrlMetadata(
            url=url,
            domain=domain,
            title=crawl_result["title"],
            meta_description=crawl_result["meta_description"],
            meta_keywords=crawl_result["meta_keywords"],
            meta_robots=crawl_result["meta_robots"],
            og_tags=crawl_result["og_tags"],
            has_structured_data=crawl_result["has_structured_data"],
            has_faq_schema=crawl_result["has_faq_schema"],
            has_lists=crawl_result["has_lists"],
            has_tables=crawl_result["has_tables"],
            status=crawl_result["status"],
            error_message=crawl_result["error_message"],
            http_status_code=crawl_result["http_status_code"],
            crawled_at=datetime.utcnow(),
        )
        
        # Add special files if columns exist
        try:
            metadata.llms_txt = special_files["llms_txt"]
            metadata.ai_txt = special_files["ai_txt"]
            metadata.robots_txt_full = special_files["robots_txt"]
        except AttributeError:
            pass  # Columns don't exist yet
        
        db.add(metadata)
        db.commit()
        db.refresh(metadata)
        return metadata


def crawl_urls_batch(db: Session, urls: List[str], max_urls: int = 50) -> Dict[str, Any]:
    """
    Crawl multiple URLs in batch.
    
    Returns summary with success/error counts.
    """
    urls = urls[:max_urls]  # Limit batch size
    
    results = {
        "total": len(urls),
        "success": 0,
        "error": 0,
        "skipped": 0,
        "urls_processed": []
    }
    
    for url in urls:
        try:
            metadata = crawl_and_save_url(db, url)
            
            if metadata.status == "success":
                results["success"] += 1
            else:
                results["error"] += 1
            
            results["urls_processed"].append({
                "url": url,
                "status": metadata.status,
                "error": metadata.error_message
            })
            
        except Exception as e:
            results["error"] += 1
            results["urls_processed"].append({
                "url": url,
                "status": "error",
                "error": str(e)[:200]
            })
    
    return results
