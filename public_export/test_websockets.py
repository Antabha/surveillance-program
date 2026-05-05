import asyncio
import websockets

async def simulate_mic():
    uri = "ws://localhost:8000/stream-audio"
    try:
        async with websockets.connect(uri) as websocket:
            print("Mic connected. Sending chunks...")
            for i in range(5):
                chunk = b'\x00' * 1024 # Dummy 1KB audio chunk
                await websocket.send(chunk)
                await asyncio.sleep(0.5)
            print("Mic finished sending chunks.")
    except Exception as e:
        print(f"Mic connection failed: {e}")

async def simulate_viewer():
    uri = "ws://localhost:8000/caption-receiver"
    try:
        async with websockets.connect(uri) as websocket:
            print("Viewer connected. Waiting for captions...")
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"Viewer received: {message}")
                except asyncio.TimeoutError:
                    print("Viewer timeout - closing connection.")
                    break
    except Exception as e:
        print(f"Viewer connection failed: {e}")

async def main():
    viewer_task = asyncio.create_task(simulate_viewer())
    await asyncio.sleep(1) # Ensure viewer is connected before mic starts
    mic_task = asyncio.create_task(simulate_mic())
    
    await mic_task
    await viewer_task

if __name__ == "__main__":
    asyncio.run(main())
