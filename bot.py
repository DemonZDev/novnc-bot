import asyncio
import os
import time
from playwright.async_api import async_playwright
from fastapi import FastAPI
import uvicorn

# ================== CONFIG ==================
NOVNC_URL = os.getenv("NOVNC_URL", "https://gdv9fx-6080.csb.app/vnc.html")
PASSWORD = os.getenv("PASSWORD", "DzD@987654321")
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "300"))  # seconds
PORT = int(os.getenv("PORT", "10000"))  # Render assigns a port
# ============================================

app = FastAPI()

@app.get("/health")
def health_check():
    """Render health check endpoint"""
    return {"status": "ok", "time": time.time()}


async def handle_vm_recovery(page):
    """
    If workspace reloads & VM needs restart:
    Run the script → select options → wait until it's alive.
    """
    print("[VM] Attempting recovery sequence...")
    try:
        await page.fill("textarea", "bash <(curl -fsSL https://raw.githubusercontent.com/hopingboyz/vms/main/vm.sh)")
        await page.keyboard.press("Enter")
        await asyncio.sleep(10)

        # Choose option 2 (start a VM)
        await page.keyboard.type("2")
        await page.keyboard.press("Enter")
        await asyncio.sleep(5)

        # Choose option 1 (select VM)
        await page.keyboard.type("1")
        await page.keyboard.press("Enter")

        print("[VM] VM restart command sent, waiting ~90s...")
        await asyncio.sleep(90)
    except Exception as e:
        print(f"[VM] Recovery failed: {e}")


async def connect_and_refresh():
    """
    Main bot loop:
    - Connect to NoVNC
    - Login
    - Refresh Firefox tabs every REFRESH_INTERVAL
    - Handle disconnections & run VM recovery if needed
    """
    while True:  # infinite outer loop → restart-safe
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context()
                page = await context.new_page()

                print(f"[BOT] Connecting to {NOVNC_URL}")
                await page.goto(NOVNC_URL, wait_until="domcontentloaded")

                # Login if required
                if await page.is_visible("input[type='password']"):
                    await page.fill("input[type='password']", PASSWORD)
                    await page.press("input[type='password']", "Enter")
                    print("[BOT] Logged into NoVNC.")

                while True:  # inner loop → tab refresh cycle
                    try:
                        print("[BOT] Running refresh cycle...")
                        tabs = context.pages

                        for i, tab in enumerate(tabs):
                            url = tab.url
                            if "idx.google.com" in url:
                                print(f"[BOT] Refreshing tab {i+1}: {url}")
                                await tab.reload(wait_until="domcontentloaded")
                                await asyncio.sleep(5)

                        print(f"[BOT] Sleeping {REFRESH_INTERVAL}s...")
                        await asyncio.sleep(REFRESH_INTERVAL)

                    except Exception as e:
                        print(f"[BOT] Error during cycle: {e}")
                        if "Disconnected" in str(e) or "reconnect" in str(e).lower():
                            print("[BOT] NoVNC disconnected. Trying reload...")
                            try:
                                await page.click("text=Reload Window")
                            except:
                                try:
                                    await page.click("text=Try Again")
                                    await handle_vm_recovery(page)
                                except:
                                    print("[BOT] Reload failed, forcing reconnect...")
                                    break  # go to outer loop
                            await asyncio.sleep(10)
                        else:
                            raise e

        except Exception as e:
            print(f"[BOT] Fatal error: {e}. Restarting in 30s...")
            await asyncio.sleep(30)


def start_bot():
    loop = asyncio.get_event_loop()
    loop.create_task(connect_and_refresh())
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    start_bot()
