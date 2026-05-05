import asyncio
import websockets
import json
import time
import wave
import struct
import math
import argparse
import os

# Generate a 16kHz Mono 16-bit dummy sine wave if no file exists
def generate_dummy_wav(filename="test.wav", duration_seconds=5):
    sample_rate = 16000
    frequency = 440.0
    num_samples = int(duration_seconds * sample_rate)
    
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            value = int(32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)
    print(f"Generated dummy audio file: {filename}")

async def send_audio(uri: str, filename: str, chunk_size_ms: int):
    # 16kHz, 16-bit Mono => 16000 * 2 bytes per second
    bytes_per_ms = int((16000 * 2) / 1000)
    chunk_size_bytes = bytes_per_ms * chunk_size_ms
    
    print(f"Connecting to audio endpoint: {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Streaming audio...")
            
            with wave.open(filename, 'rb') as wav_file:
                if wav_file.getnchannels() != 1 or wav_file.getframerate() != 16000:
                    print("WARNING: Audio file is not 16kHz Mono! STT might fail or return garbage.")

                while True:
                    frames = wav_file.readframes(chunk_size_bytes // 2)
                    if not frames:
                        break
                    
                    # Mark time for latency calculation
                    global last_chunk_time
                    last_chunk_time = time.time()
                    
                    await websocket.send(frames)
                    await asyncio.sleep(chunk_size_ms / 1000.0)
                    
            print("Finished sending audio.")
            # Keep connection open slightly longer to receive final captions
            await asyncio.sleep(5)
    except Exception as e:
        print(f"Audio Sender Error: {e}")

async def receive_captions(uri: str):
    print(f"Connecting to caption endpoint: {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print("Caption receiver connected! Waiting for transcripts...\n")
            while True:
                message = await websocket.recv()
                receive_time = time.time()
                
                # Calculate latency from start
                total_latency = receive_time - start_time
                # Calculate latency from last chunk sent
                chunk_latency = receive_time - last_chunk_time if 'last_chunk_time' in globals() else 0
                
                try:
                    data = json.loads(message)
                    is_final = data.get("is_final", False)
                    transcript = data.get("transcript", "")
                    
                    prefix = "[FINAL]" if is_final else "[INTERIM]"
                    print(f"[{total_latency:.2f}s total] [{chunk_latency*1000:.0f}ms round-trip latency] {prefix} {transcript}")
                except json.JSONDecodeError:
                    print(f"[{total_latency:.2f}s total] Raw Message: {message}")
                    
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Caption Receiver Error: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Test Client for STT Streaming")
    parser.add_argument("--host", default="localhost:8000", help="Hostname and port of the server")
    parser.add_argument("--secure", action="store_true", help="Use wss:// instead of ws://")
    parser.add_argument("--file", default="test.wav", help="Path to 16kHz Mono .wav file")
    args = parser.parse_args()

    protocol = "wss" if args.secure else "ws"
    audio_uri = f"{protocol}://{args.host}/stream-audio"
    caption_uri = f"{protocol}://{args.host}/caption-receiver"

    if not os.path.exists(args.file):
        print(f"Audio file '{args.file}' not found. Generating a dummy one...")
        generate_dummy_wav(args.file)

    global start_time
    start_time = time.time()

    # Run both tasks concurrently
    receiver_task = asyncio.create_task(receive_captions(caption_uri))
    sender_task = asyncio.create_task(send_audio(audio_uri, args.file, chunk_size_ms=100))

    await sender_task
    receiver_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
