import httpx
from bs4 import BeautifulSoup
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger=logging.getLogger(__name__)
import os

PORTAL_DATA_PATH = "data/portal_data.txt"
# ─── Pages to scrape ─────────────────────────────────────────────────────────
URLS = [
    "https://e-numerak.com/",
    "https://e-numerak.com/services",
    "https://e-numerak.com/peppol",
    "https://e-numerak.com/fta-compliance",
    "https://e-numerak.com/contact",
    "https://e-numerak.com/about",
    
]

SEMAPHORE = asyncio.Semaphore(3) # 

"""The main purpose of Adding Headers is that when we send request to website
for fetching data sometimes they block by considering us bots so when add
headers they dont block us and consider it that request is coming from 
authorized source"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ─── Scraper ─────────────────────────────────────────────────────────────────
async def fetch_and_parse(client: httpx.AsyncClient, url: str)->str:
    """Scrap All Pages and return Clearn Combined txt"""
    """Sends requests using httpx: It creates a smart client that acts like a web browser, allowing your Python script to send requests (like GET or POST) to any website or API.
    Sets a 30-second time limit: The timeout=30 acts like a stopwatch.
    If the server you are trying to reach is down, extremely slow, or doesn't respond within 30 seconds, your code won't stay stuck forever. 
    It will automatically stop waiting and raise a TimeoutException."""
    async with SEMAPHORE:
            try:
                response = await client.get(url,headers=HEADERS)

                response.raise_for_status() # If Error Occurs It will Handle it

                """This Line actually Enable you scrap important data from HTML
                File this does scrap text from HTML"""
                soup = BeautifulSoup(response.text,"html.parser")

                #Remove Unwanted Tags
                for tag in soup(["script", "style", "nav", "footer", "head"]):
                    tag.decompose()

                #Extract clean text
                text=soup.get_text(separator="\n",strip=True)
                logger.info(f"✅ Successfully Scraped: {url}")
                return f"--- Source: {url} ---\n{text}"

            except httpx.HTTPStatusError as exc:
                logger.error(f"❌ HTTP Error for {url}: Status {exc.response.status_code}")
            except httpx.TimeoutException:
                logger.error(f"⏱️ Timeout Error for {url}: Server took too long to respond.")
            except Exception as e:
                logger.error(f"💥 Unexpected Error for {url}: {e}")

    return "" # If fail return nothig

def load_portal_data() -> str:
    """Load static portal_data.txt content."""
    try:
        with open(PORTAL_DATA_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info("✅ portal_data.txt loaded successfully.")
        return content
    except FileNotFoundError:
        logger.warning("⚠️ portal_data.txt not found — skipping.")
        return ""

async def scrap_website()->str:
    """Scrap Every Single Pages Fastly"""
    limits=httpx.Limits(max_keepalive_connections=5,max_connections=10)
    """max_keepalive_connections=5: Kaam khatam hone ke baad, yeh background mein 5 khaali connections ko zinda (open) rakhta 
    hai taake agli requests bina time zaya kiye foran unhe reuse kar sakein."""

    async with httpx.AsyncClient(timeout=30,limits=limits) as client:
        """Now Send Request on every single URL combined form"""
        """This function is used when we want to do a work in background"""
        # 'asyncio.create_task' se saari URLs par ek sath kaam shuru ho jata hai
        task = [asyncio.create_task(fetch_and_parse(client,url))for url in URLS]

        #This will wait until all the task will end
        results=await asyncio.gather(*task)

        #Just Getting the cleaned from the result and removing null values
        clean_results = [r for r in results if r]
        scraped_text = "\n\n".join(clean_results)
        portal_text = load_portal_data()

    final_text = scraped_text + "\n\n=== HELP & GUIDE ===\n\n" + portal_text

    logger.info(f"📄 Total characters ready for ingestion: {len(final_text)}")
    return final_text



# if __name__ == "__main__":
#     async def test():
#         print("🚀 Starting scraper test...")
#         result = await scrap_website()
#         print(f"✅ Total characters scraped: {len(result)}")
#         print("\n--- First 500 characters preview ---")
#         print(result)

#     asyncio.run(test())
         

         