import asyncio
import os
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        if not os.path.exists(creds_path):
            logger.warning(f"GOOGLE_APPLICATION_CREDENTIALS is set to '{creds_path}', but the file does not exist. Cloud Run attached Service Account will be used if deployed.")
        else:
            logger.info(f"Using GOOGLE_APPLICATION_CREDENTIALS at '{creds_path}'")
    else:
        logger.info("GOOGLE_APPLICATION_CREDENTIALS not set. Using default credentials (e.g. Cloud Run attached Service Account).")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() == "true"
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "{{YOUR_PROJECT_ID}}")

if not MOCK_MODE:
    from google.cloud.speech_v2 import SpeechAsyncClient
    from google.cloud.speech_v2.types import cloud_speech
    
    # Initialize GCP Client
    try:
        speech_client = SpeechAsyncClient()
    except Exception as e:
        logger.error(f"Failed to initialize Speech client: {e}")
        speech_client = None
else:
    speech_client = None

# Unified server route to serve frontend
@app.get("/")
async def get_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"error": "index.html not found"}

class CaptionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Viewer connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Viewer disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                self.disconnect(connection)

caption_manager = CaptionManager()

@app.websocket("/caption-receiver")
async def caption_receiver(websocket: WebSocket):
    await caption_manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from viewers, but we need to keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        caption_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Caption receiver error: {e}")
        caption_manager.disconnect(websocket)

async def process_mock_audio(queue: asyncio.Queue):
    while True:
        data = await queue.get()
        if data is None: # Sentinel value to stop
            break
        # Simulate processing time
        await asyncio.sleep(0.1)
        payload = json.dumps({
            "is_final": True,
            "transcript": f"[MOCK] Received audio chunk of size {len(data)} bytes"
        })
        await caption_manager.broadcast(payload)

async def process_gcp_audio(queue: asyncio.Queue):
    if not speech_client:
        logger.error("Speech client is not initialized. Cannot process GCP audio.")
        return

    logger.info("Initializing gRPC stream generator for STT V2")

    async def request_generator():
        # First request must be the config
        config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                audio_channel_count=1,
            ),
            language_codes=["en-US"],
            model="latest_long",
        )
        
        streaming_config = cloud_speech.StreamingRecognitionConfig(
            config=config,
            streaming_features=cloud_speech.StreamingRecognitionFeatures(
                interim_results=True
            )
        )
        
        logger.debug("Yielding initial streaming config request")
        yield cloud_speech.StreamingRecognizeRequest(
            recognizer=f"projects/{GCP_PROJECT_ID}/locations/global/recognizers/_",
            streaming_config=streaming_config,
        )

        chunk_count = 0
        while True:
            data = await queue.get()
            if data is None:
                logger.info("Received sentinel value, closing gRPC audio stream")
                break
            chunk_count += 1
            if chunk_count % 50 == 0:
                logger.debug(f"Yielded {chunk_count} audio chunks to GCP")
            yield cloud_speech.StreamingRecognizeRequest(audio=data)

    try:
        logger.info("Starting streaming_recognize call to GCP")
        requests = request_generator()
        responses = await speech_client.streaming_recognize(requests=requests)
        
        async for response in responses:
            logger.debug(f"Received response from GCP with {len(response.results)} results")
            for result in response.results:
                if result.alternatives:
                    transcript = result.alternatives[0].transcript
                    is_final = result.is_final
                    
                    logger.info(f"Transcript received: final={is_final}, text='{transcript}'")
                    
                    payload = json.dumps({
                        "is_final": is_final,
                        "transcript": transcript
                    })
                    await caption_manager.broadcast(payload)
                    
        logger.info("GCP streaming_recognize completed normally")
    except Exception as e:
        logger.error(f"GCP Streaming error: {e}", exc_info=True)

@app.websocket("/stream-audio")
async def stream_audio(websocket: WebSocket):
    logger.info("Audio source connecting to /stream-audio")
    await websocket.accept()
    logger.info("Audio source connected")
    
    audio_queue = asyncio.Queue()
    
    # Start background processing task
    if MOCK_MODE:
        logger.info("Starting background audio processing in MOCK_MODE")
        process_task = asyncio.create_task(process_mock_audio(audio_queue))
    else:
        logger.info("Starting background audio processing with GCP STT V2")
        process_task = asyncio.create_task(process_gcp_audio(audio_queue))

    try:
        while True:
            # Receive binary data from phone mic
            data = await websocket.receive_bytes()
            await audio_queue.put(data)
    except WebSocketDisconnect:
        logger.info("Audio source disconnected normally")
    except Exception as e:
        logger.error(f"Audio stream error: {e}")
    finally:
        # Stop processing
        logger.info("Signaling background task to stop")
        await audio_queue.put(None)
        await process_task
        logger.info("Audio stream endpoint cleanup complete")
