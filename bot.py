# bot.py
import asyncio
from playwright.async_api import async_playwright
from fastapi import FastAPI
import uvicorn
import os
import threading

# === Config ===
NOVNC_URL = os.getenv("NOVNC_URL", "https://gdv9fx-6080.csb.app/vnc.html")
PASSWORD = os.getenv("PASSWORD", "DzD@987654321")
HEALTH_PORT = int(os.getenv("PORT", 10000))

# === FastAPI health server ===
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}


def start_api():
    """Run FastAPI health server in background thread"""
    uvicorn.run(app, host="0.0.0.0", port=HEALTH_PORT, log_level="warning")


# === Bot Core ===
async def run_bot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        # ---------- Helpers ----------
        async def wait_and_click(selector, timeout=5000):
            try:
                await page.wait_for_selector(selector, timeout=timeout)
                await page.click(selector)
                return True
            except:
                return False

        async def connect_vnc():
            """Ensure NoVNC connection"""
            while True:
                print("[INFO] Opening NoVNC page...")
                await page.goto(NOVNC_URL)

                # Click Connect
                await wait_and_click("text=Connect", timeout=10000)

                # Handle password
                try:
                    await page.fill("input[type='password']", PASSWORD, timeout=5000)
                    await page.click("text=Send Password")
                except:
                    pass

                # Success check: Firefox visible
                try:
                    await page.wait_for_selector("text=Firefox", timeout=20000)
                    print("[INFO] Connected to NoVNC desktop")
                    return
                except:
                    print("[WARN] Connect failed, retrying...")
                    await asyncio.sleep(5)

        async def restart_vm():
            """Restart VM from terminal"""
            print("[WARN] VM appears stopped → restarting...")
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

            print("[INFO] VM restarting, waiting 90s...")
            await asyncio.sleep(90)
            print("[INFO] VM restart complete")

        async def refresh_tabs():
            """Cycle through tabs and refresh"""
            print("[INFO] Starting refresh cycle...")
            tab_count = 0

            for i in range(10):  # assume max 10 tabs
                await page.keyboard.press("F5")
                tab_count += 1
                print(f"[INFO] Refreshed tab {i+1}")
                await asyncio.sleep(3)

                # Switch to next tab
                await page.keyboard.down("Control")
                await page.keyboard.press("PageDown")
                await page.keyboard.up("Control")
                await asyncio.sleep(1)

            print(f"[INFO] Refreshed {tab_count} tabs. Sleeping 5 minutes...")
            await asyncio.sleep(300)

        # ---------- Main Loop ----------
        while True:
            try:
                await connect_vnc()
                await refresh_tabs()
            except Exception as e:
                print(f"[ERROR] {e}")

                # Try workspace/VM recovery
                if await page.query_selector("text=Reload Window"):
                    print("[WARN] Disconnected popup → Reloading")
                    await page.click("text=Reload Window")
                elif await page.query_selector("text=Try Again"):
                    print("[WARN] Error page → Try Again")
                    await page.click("text=Try Again")
                elif await page.query_selector("text=HOPINGBOYZ"):
                    await restart_vm()

                await asyncio.sleep(5)


if __name__ == "__main__":
    # Start API server in background thread
    threading.Thread(target=start_api, daemon=True).start()

    # Start bot loop
    asyncio.run(run_bot())
