import logging
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}

SCORE_LABELS = [
    (80, "Excellent"),
    (60, "Good"),
    (40, "Needs Work"),
]


def score_label(score: int) -> str:
    for threshold, label in SCORE_LABELS:
        if score >= threshold:
            return label
    return "Poor"


def validate_url(url: str) -> dict:
    if not url or not isinstance(url, str):
        return {"valid": False, "error": "No URL provided."}
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        return {"valid": False, "error": "Malformed URL. Provide a valid domain."}
    if parsed.scheme not in ALLOWED_SCHEMES:
        return {"valid": False, "error": f"Unsupported scheme '{parsed.scheme}'. Use http or https."}
    return {"valid": True, "url": url}


async def fetch_website(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; WebsiteAuditBot/1.0)"
            })
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return {"success": False, "error": "Response is not HTML content."}
            if not response.text.strip():
                return {"success": False, "error": "Empty response body."}
            return {"success": True, "html": response.text, "status": response.status_code, "headers": dict(response.headers)}
    except httpx.TimeoutException:
        return {"success": False, "error": "Request timed out after 10 seconds."}
    except httpx.ConnectError:
        return {"success": False, "error": "Could not connect to the server. Check the URL."}
    except httpx.RemoteProtocolError:
        return {"success": False, "error": "SSL or protocol error."}
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch website: {str(e)}"}


def parse_html(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    result = {"url": url}

    title_tag = soup.find("title")
    result["title"] = title_tag.get_text(strip=True) if title_tag else None

    meta_desc = soup.find("meta", attrs={"name": "description"})
    result["meta_description"] = meta_desc.get("content", "").strip() if meta_desc else None

    viewport = soup.find("meta", attrs={"name": "viewport"})
    result["viewport"] = viewport.get("content", "").strip() if viewport else None

    canonical = soup.find("link", rel="canonical")
    result["canonical"] = canonical.get("href", "").strip() if canonical else None

    headings = {}
    for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        headings[tag] = [h.get_text(strip=True) for h in soup.find_all(tag) if h.get_text(strip=True)]
    result["headings"] = headings
    result["h1_count"] = len(headings.get("h1", []))

    images = []
    missing_alt = 0
    for img in soup.find_all("img"):
        src = img.get("src", "").strip()
        alt = img.get("alt", "").strip()
        has_alt = bool(alt)
        if not has_alt:
            missing_alt += 1
        images.append({"src": src, "alt": alt, "has_alt": has_alt})
    result["images"] = images
    result["total_images"] = len(images)
    result["missing_alt_count"] = missing_alt
    result["alt_coverage_percent"] = round(((len(images) - missing_alt) / max(len(images), 1)) * 100, 1)

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href and not href.startswith("#") and not href.startswith("javascript:"):
            links.append({"href": href, "text": a.get_text(strip=True)[:100]})
    result["internal_links"] = [l for l in links if l["href"].startswith("/") or urlparse(l["href"]).netloc == urlparse(url).netloc]
    result["external_links"] = [l for l in links if l not in result["internal_links"]]
    result["total_links"] = len(links)

    scripts = soup.find_all("script")
    result["script_count"] = len(scripts)
    inline_scripts = [s for s in scripts if not s.get("src")]
    result["inline_script_size"] = sum(len(s.get_text(strip=True)) for s in inline_scripts)

    stylesheets = []
    inline_css_size = 0
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href", "")
        if href:
            stylesheets.append(href)
    for style in soup.find_all("style"):
        inline_css_size += len(style.get_text(strip=True))
    result["stylesheet_count"] = len(stylesheets)
    result["inline_css_size"] = inline_css_size

    result["html_size"] = len(html)

    lazy_images = sum(1 for img in soup.find_all("img") if img.get("loading", "").lower() == "lazy")
    result["lazy_loading_images"] = lazy_images

    result["has_lang"] = bool(soup.html and soup.html.get("lang"))
    result["lang"] = soup.html.get("lang") if soup.html else None

    og_tags = {}
    for og in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
        og_tags[og.get("property")] = og.get("content")
    result["og_tags"] = og_tags

    robots = soup.find("meta", attrs={"name": "robots"})
    result["robots"] = robots.get("content", "").strip() if robots else None

    has_https = url.startswith("https://")
    result["has_https"] = has_https

    deprecated_tags = ["center", "font", "marquee", "blink", "tt", "strike", "big"]
    found_deprecated = [tag for tag in deprecated_tags if soup.find(tag)]
    result["deprecated_tags"] = found_deprecated

    aria_attrs = sum(1 for tag in soup.find_all(attrs={re.compile(r"^aria-"): True}))
    result["aria_attributes"] = aria_attrs

    buttons = soup.find_all("button")
    buttons_without_text = sum(1 for b in buttons if not b.get_text(strip=True) and not b.get("aria-label"))
    result["buttons_missing_label"] = buttons_without_text
    result["total_buttons"] = len(buttons)

    form_inputs = soup.find_all(["input", "textarea", "select"])
    inputs_without_label = 0
    for inp in form_inputs:
        inp_id = inp.get("id")
        if inp_id:
            label = soup.find("label", attrs={"for": inp_id})
            if label:
                continue
        if inp.get("type") in ("hidden", "submit", "button", "reset"):
            continue
        if inp.get("aria-label"):
            continue
        inputs_without_label += 1
    result["inputs_without_label"] = inputs_without_label

    return result


def score_on_page_seo(data: dict) -> int:
    score = 100
    if not data.get("title"):
        score -= 20
    elif len(data["title"]) < 30 or len(data["title"]) > 60:
        score -= 10
    if not data.get("meta_description"):
        score -= 15
    elif data["meta_description"] and (len(data["meta_description"]) < 120 or len(data["meta_description"]) > 160):
        score -= 5
    if data.get("h1_count", 0) == 0:
        score -= 15
    elif data.get("h1_count", 0) > 1:
        score -= 5
    if not data.get("canonical"):
        score -= 10
    if not data.get("viewport"):
        score -= 5
    alt_pct = data.get("alt_coverage_percent", 100)
    if alt_pct < 50:
        score -= 15
    elif alt_pct < 80:
        score -= 10
    elif alt_pct < 100:
        score -= 5
    return max(0, score)


def score_performance(data: dict) -> int:
    score = 100
    html_size = data.get("html_size", 0)
    if html_size > 500000:
        score -= 15
    elif html_size > 200000:
        score -= 10
    elif html_size > 100000:
        score -= 5
    img_count = data.get("total_images", 0)
    if img_count > 50:
        score -= 15
    elif img_count > 20:
        score -= 10
    elif img_count > 10:
        score -= 5
    script_count = data.get("script_count", 0)
    if script_count > 30:
        score -= 15
    elif script_count > 15:
        score -= 10
    elif script_count > 8:
        score -= 5
    css_count = data.get("stylesheet_count", 0)
    if css_count > 10:
        score -= 10
    elif css_count > 5:
        score -= 5
    inline_css = data.get("inline_css_size", 0)
    if inline_css > 10000:
        score -= 10
    elif inline_css > 5000:
        score -= 5
    total_resources = img_count + script_count + css_count
    if total_resources > 100:
        score -= 15
    elif total_resources > 50:
        score -= 10
    lazy_pct = (data.get("lazy_loading_images", 0) / max(img_count, 1)) * 100
    if lazy_pct > 50:
        score += 5
    return max(0, min(100, score))


def score_accessibility(data: dict) -> int:
    score = 100
    if data.get("missing_alt_count", 0) > 0:
        missing = data["missing_alt_count"]
        if missing > 10:
            score -= 20
        elif missing > 5:
            score -= 15
        else:
            score -= 10
    headings = data.get("headings", {})
    if headings.get("h1", []):
        h1_text = headings["h1"][0].lower() if headings["h1"] else ""
        if data.get("title", "").lower() and h1_text and h1_text not in data["title"].lower():
            score -= 5
    if not data.get("has_lang"):
        score -= 15
    if not data.get("viewport"):
        score -= 10
    buttons_missing = data.get("buttons_missing_label", 0)
    if buttons_missing > 0:
        score -= min(buttons_missing * 5, 15)
    inputs_missing = data.get("inputs_without_label", 0)
    if inputs_missing > 0:
        score -= min(inputs_missing * 5, 15)
    if data.get("aria_attributes", 0) == 0 and data.get("total_buttons", 0) > 0:
        score -= 5
    return max(0, score)


def score_best_practices(data: dict) -> int:
    score = 100
    if not data.get("has_https"):
        score -= 20
    if data.get("deprecated_tags"):
        score -= min(len(data["deprecated_tags"]) * 5, 15)
    if not data.get("viewport"):
        score -= 10
    if data.get("script_count", 0) > 20:
        score -= 10
    if data.get("og_tags"):
        required = ["og:title", "og:description", "og:image"]
        missing = [t for t in required if t not in data["og_tags"]]
        if missing:
            score -= 5 * len(missing)
    else:
        score -= 10
    if data.get("robots") and "noindex" in data["robots"].lower():
        score -= 10
    return max(0, score)


def generate_issues(data: dict) -> list[str]:
    issues = []
    if not data.get("title"):
        issues.append("Missing <title> tag.")
    elif len(data["title"]) < 30:
        issues.append(f"Title too short ({len(data['title'])} chars, minimum 30).")
    elif len(data["title"]) > 60:
        issues.append(f"Title too long ({len(data['title'])} chars, maximum 60).")
    if not data.get("meta_description"):
        issues.append("Missing meta description.")
    elif data["meta_description"] and len(data["meta_description"]) < 120:
        issues.append(f"Meta description too short ({len(data['meta_description'])} chars, minimum 120).")
    elif data["meta_description"] and len(data["meta_description"]) > 160:
        issues.append(f"Meta description too long ({len(data['meta_description'])} chars, maximum 160).")
    if data.get("h1_count", 0) == 0:
        issues.append("Missing H1 heading.")
    elif data.get("h1_count", 0) > 1:
        issues.append(f"Multiple H1 tags found ({data['h1_count']}). Use exactly one.")
    if not data.get("canonical"):
        issues.append("Missing canonical URL tag.")
    if not data.get("viewport"):
        issues.append("Missing viewport meta tag.")
    if not data.get("has_lang"):
        issues.append("Missing <html lang> attribute.")
    if data.get("missing_alt_count", 0) > 0:
        issues.append(f"{data['missing_alt_count']} images missing alt text.")
    if not data.get("has_https"):
        issues.append("Site is not served over HTTPS.")
    if data.get("deprecated_tags"):
        issues.append(f"Deprecated HTML tags found: {', '.join(data['deprecated_tags'])}.")
    if data.get("buttons_missing_label", 0) > 0:
        issues.append(f"{data['buttons_missing_label']} buttons lack accessible labels.")
    if data.get("inputs_without_label", 0) > 0:
        issues.append(f"{data['inputs_without_label']} form inputs missing labels.")
    if data.get("html_size", 0) > 500000:
        issues.append(f"HTML is very large ({data['html_size'] / 1000:.0f} KB). Consider optimizing.")
    if data.get("script_count", 0) > 30:
        issues.append(f"High script count ({data['script_count']}). Impacts load performance.")
    return issues[:10]


def generate_suggestions(data: dict) -> list[str]:
    suggestions = []
    if not data.get("title"):
        suggestions.append("Add a descriptive <title> tag between 30-60 characters.")
    elif len(data.get("title", "")) < 30 or len(data.get("title", "")) > 60:
        suggestions.append(f"Optimize title length to 30-60 characters (currently {len(data['title'])}).")
    if not data.get("meta_description"):
        suggestions.append("Add a meta description between 120-160 characters.")
    elif data.get("meta_description") and (len(data["meta_description"]) < 120 or len(data["meta_description"]) > 160):
        suggestions.append(f"Adjust meta description length to 120-160 characters (currently {len(data['meta_description'])}).")
    if data.get("h1_count", 0) != 1:
        suggestions.append("Ensure exactly one H1 heading that matches the page topic.")
    if not data.get("canonical"):
        suggestions.append("Add a canonical URL tag to prevent duplicate content issues.")
    if not data.get("viewport"):
        suggestions.append("Add a viewport meta tag for mobile responsiveness.")
    if not data.get("has_lang"):
        suggestions.append("Add a lang attribute to the <html> tag for accessibility and SEO.")
    if data.get("alt_coverage_percent", 100) < 100:
        suggestions.append("Add descriptive alt text to all images for accessibility and SEO.")
    if not data.get("og_tags"):
        suggestions.append("Add Open Graph tags (og:title, og:description, og:image) for social sharing.")
    elif not all(k in (data.get("og_tags") or {}) for k in ["og:title", "og:description"]):
        suggestions.append("Include og:title and og:description for better social previews.")
    if data.get("missing_alt_count", 0) > 0:
        suggestions.append(f"Add alt text to {data['missing_alt_count']} images.")
    if data.get("buttons_missing_label", 0) > 0:
        suggestions.append(f"Add aria-labels or text content to {data['buttons_missing_label']} buttons.")
    if data.get("inputs_without_label", 0) > 0:
        suggestions.append(f"Associate labels with {data['inputs_without_label']} form inputs.")
    if data.get("lazy_loading_images", 0) < data.get("total_images", 0) * 0.3:
        suggestions.append("Implement lazy loading for images below the fold.")
    if data.get("html_size", 0) > 100000:
        suggestions.append(f"Reduce HTML size ({data['html_size'] / 1000:.0f} KB) by minimizing inline CSS/JS.")
    return suggestions[:10]


async def capture_preview(url: str) -> str | None:
    try:
        from playwright.async_api import async_playwright
        from io import BytesIO
        import base64

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page(viewport={"width": 1440, "height": 900})
                await page.goto(url, timeout=10000, wait_until="networkidle")
                image_bytes = await page.screenshot(full_page=False, type="png")
            finally:
                await browser.close()

            return base64.b64encode(image_bytes).decode()
    except Exception as e:
        logger.warning("Screenshot capture failed (non-fatal): %s", e)
        return None


async def run_website_audit(url: str) -> dict:
    validation = validate_url(url)
    if not validation["valid"]:
        return _error_response(url, [validation["error"]])

    target_url = validation["url"]
    fetch_result = await fetch_website(target_url)
    if not fetch_result["success"]:
        return _error_response(target_url, [fetch_result["error"]])

    parsed = parse_html(fetch_result["html"], target_url)

    seo_score = score_on_page_seo(parsed)
    perf_score = score_performance(parsed)
    a11y_score = score_accessibility(parsed)
    bp_score = score_best_practices(parsed)
    overall_seo = round((seo_score + bp_score) / 2)

    issues = generate_issues(parsed)
    suggestions = generate_suggestions(parsed)

    return {
        "url": target_url,
        "scores": {
            "on_page_seo": {"score": seo_score, "label": score_label(seo_score)},
            "performance": {"score": perf_score, "label": score_label(perf_score)},
            "accessibility": {"score": a11y_score, "label": score_label(a11y_score)},
            "seo": {"score": overall_seo, "label": score_label(overall_seo)},
            "best_practices": {"score": bp_score, "label": score_label(bp_score)},
        },
        "issues": issues,
        "suggestions": suggestions,
    }


def _error_response(url: str, errors: list[str]) -> dict:
    return {
        "url": url or "",
        "scores": {
            "on_page_seo": {"score": 0, "label": "Poor"},
            "performance": {"score": 0, "label": "Poor"},
            "accessibility": {"score": 0, "label": "Poor"},
            "seo": {"score": 0, "label": "Poor"},
            "best_practices": {"score": 0, "label": "Poor"},
        },
        "issues": errors if errors else ["Unable to analyze website."],
        "suggestions": ["Verify the URL and try again."],
    }
