# bot.py
import asyncio
from playwright.async_api import async_playwright
from fastapi import FastAPI
import uvicorn
import threading

NOVNC_URL = "https://gdv9fx-6080.csb.app/vnc.html"
PASSWORD = "DzD@987654321"

# FastAPI app for healthcheck
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=10000, log_level="warning")

async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        async def connect_vnc():
            while True:
                print("[INFO] Opening NoVNC page...")
                await page.goto(NOVNC_URL)

                try:
                    await page.click("text=Connect", timeout=10000)
                except:
                    pass

                try:
                    await page.fill("input[type='password']", PASSWORD, timeout=5000)
                    await page.click("text=Send Password")
                except:
                    pass

                try:
                    await page.wait_for_selector("text=Firefox", timeout=15000)
                    print("[INFO] Connected successfully.")
                    return
                except:
                    print("[WARN] Failed, retrying...")
                    await asyncio.sleep(5)

        async def restart_vm():
            print("[INFO] Restarting VM via terminal commands...")
            await page.keyboard.type(
                "bash <(curl -fsSL https://raw.githubusercontent.com/hopingboyz/vms/main/vm.sh)"
            )
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)

            await page.keyboard.type("2")
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)

            await page.keyboard.type("1")
            await page.keyboard.press("Enter")

            print("[INFO] VM starting... waiting 90s")
            await asyncio.sleep(90)
            print("[INFO] VM should be ready now.")

        async def refresh_tabs():
            print("[INFO] Starting refresh cycle...")
            tab_count = 0
            for i in range(10):  # assume max 10 tabs
                await page.keyboard.press("F5")
                tab_count += 1
                print(f"[INFO] Refreshed tab {i+1}")
                await asyncio.sleep(3)
                await page.keyboard.down("Control")
                await page.keyboard.press("PageDown")
                await page.keyboard.up("Control")
                await asyncio.sleep(1)

            print(f"[INFO] Refreshed {tab_count} tabs. Sleeping 5 minutes...")
            await asyncio.sleep(300)

        # === Infinite Loop ===
        while True:
            try:
                await connect_vnc()
                await refresh_tabs()
            except Exception as e:
                print(f"[ERROR] {e}")
                try:
                    if await page.query_selector("text=HOPINGBOYZ"):
                        await restart_vm()
                except:
                    pass
                await asyncio.sleep(5)

if __name__ == "__main__":
    # Run API server in a background thread
    threading.Thread(target=run_api, daemon=True).start()

    # Run the bot loop
    asyncio.run(run_bot())
