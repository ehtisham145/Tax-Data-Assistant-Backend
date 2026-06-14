import httpx
from bs4 import BeautifulSoup
import logging
import asyncio
import io
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SEMAPHORE = asyncio.Semaphore(3)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ─── E-Numerak's own pages -> data/raw/company_info/ ─────────────────────────
COMPANY_INFO_URLS = {
    "https://e-numerak.com/":               "data/raw/company_info/home.txt",
    "https://e-numerak.com/services":       "data/raw/company_info/services.txt",
    "https://e-numerak.com/peppol":         "data/raw/company_info/peppol.txt",
    "https://e-numerak.com/fta-compliance": "data/raw/company_info/fta_compliance.txt",
    "https://e-numerak.com/contact":        "data/raw/company_info/contact.txt",
    "https://e-numerak.com/about":          "data/raw/company_info/about.txt",
}

# ─── General UAE VAT / e-invoicing pages -> data/raw/uae_tax_knowledge/ ──────
# HTML pages (scraped normally)
UAE_TAX_HTML_URLS = {
    "https://tax.gov.ae/en/taxes/Vat.aspx":
        "data/raw/uae_tax_knowledge/fta_vat_guide.txt",
    "https://tax.gov.ae/en/taxes/vat/guides.references.aspx":
        "data/raw/uae_tax_knowledge/fta_einvoicing_clarifications.txt",
    "https://mof.gov.ae/en/about-ministry/mof-initiatives/einvoicing/":
        "data/raw/uae_tax_knowledge/mof_einvoicing_overview.txt",
}

# PDF sources (need text extraction, not HTML parsing)
UAE_TAX_PDF_URLS = {
    "https://tax.gov.ae/DataFolder/Files/Guides/VAT/Awareness/Get%20to%20know%20your%20Tax%20Obligations.pdf":
        "data/raw/uae_tax_knowledge/fta_vat_awareness_guide.txt",
}


# ─── HTML scraper ─────────────────────────────────────────────────────────────
async def fetch_html_text(client: httpx.AsyncClient, url: str) -> str:
    """Fetch a page and return cleaned visible text."""
    async with SEMAPHORE:
        try:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "head"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            logger.info(f"✅ Scraped HTML: {url}")
            return text

        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP Error for {url}: Status {exc.response.status_code}")
        except httpx.TimeoutException:
            logger.error(f" Timeout Error for {url}")
        except Exception as e:
            logger.error(f"Unexpected Error for {url}: {e}")
    return ""


# ─── PDF scraper ──────────────────────────────────────────────────────────────
async def fetch_pdf_text(client: httpx.AsyncClient, url: str) -> str:
    """Download a PDF and extract its text content."""
    if pdfplumber is None:
        logger.error("pdfplumber not installed — run: pip install pdfplumber")
        return ""

    async with SEMAPHORE:
        try:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()

            with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)

            logger.info(f" Extracted PDF: {url}")
            return text

        except Exception as e:
            logger.error(f" Error extracting PDF {url}: {e}")
    return ""


# ─── Save helper ──────────────────────────────────────────────────────────────
def save_text(content: str, output_path: str, url: str):
    """Save scraped text to its own file, with a source header for traceability."""
    if not content.strip():
        logger.warning(f" No content extracted for {url} — skipping save.")
        return

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    final_content = f"--- Source: {url} ---\n{content}"
    path.write_text(final_content, encoding="utf-8")
    logger.info(f" Saved: {path}")


# ─── Group runners ─────────────────────────────────────────────────────────────
async def scrape_html_group(url_map: dict, client: httpx.AsyncClient):
    tasks = {url: asyncio.create_task(fetch_html_text(client, url)) for url in url_map}
    for url, task in tasks.items():
        text = await task
        save_text(text, url_map[url], url)


async def scrape_pdf_group(url_map: dict, client: httpx.AsyncClient):
    tasks = {url: asyncio.create_task(fetch_pdf_text(client, url)) for url in url_map}
    for url, task in tasks.items():
        text = await task
        save_text(text, url_map[url], url)


# ─── Main entry point ──────────────────────────────────────────────────────────
async def run_full_scrape():
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    async with httpx.AsyncClient(timeout=30, limits=limits, follow_redirects=True) as client:

        logger.info("Scraping E-Numerak company pages...")
        await scrape_html_group(COMPANY_INFO_URLS, client)

        logger.info("Scraping UAE tax knowledge pages (HTML)...")
        await scrape_html_group(UAE_TAX_HTML_URLS, client)

        logger.info("Scraping UAE tax knowledge pages (PDF)...")
        await scrape_pdf_group(UAE_TAX_PDF_URLS, client)

    logger.info("✅ All sources scraped and saved.")


if __name__ == "__main__":
    asyncio.run(run_full_scrape())