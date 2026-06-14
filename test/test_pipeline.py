import asyncio
import logging
# Assume is pipeline file ka naam pipeline.py hai
from utils.data_pipeline.pipeline import run_update_pipeline 

# Console logging enable karte hain taake testing saaf dikhe
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_runner():
    print("🎬 Triggering the Production Pipeline Test...")
    
    # Pipeline run karenge
    result = await run_update_pipeline()
    
    print("\n📊 --- PIPELINE RETURN RESULT ---")
    print(result)
    print("---------------------------------\n")

if __name__ == "__main__":
    asyncio.run(test_runner())