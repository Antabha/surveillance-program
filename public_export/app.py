import os
import argparse
from typing import Iterator

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech


def generate_audio_requests(
    project_id: str,
    recognizer_id: str = "_",
    location: str = "global",
) -> Iterator[cloud_speech.StreamingRecognizeRequest]:
    """Generates StreamingRecognizeRequest objects."""
    # First request must be a StreamingRecognizeRequest with a StreamingRecognitionConfig
    recognizer_path = f"projects/{project_id}/locations/{location}/recognizers/{recognizer_id}"
    
    recognition_config = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        language_codes=["en-US"],
        model="latest_long",
    )
    
    streaming_config = cloud_speech.StreamingRecognitionConfig(
        config=recognition_config,
    )
    
    yield cloud_speech.StreamingRecognizeRequest(
        recognizer=recognizer_path,
        streaming_config=streaming_config,
    )

    # In a real app, you would read audio chunks from a microphone, file, or websocket here.
    # For demonstration, we yield a dummy audio chunk.
    print("Yielding dummy audio chunk for demonstration...")
    # Yield a blank small audio chunk
    dummy_audio = b"\x00" * 1024
    yield cloud_speech.StreamingRecognizeRequest(audio=dummy_audio)

def main():
    parser = argparse.ArgumentParser(description="Speech-to-Text V2 Bidirectional Streaming")
    parser.add_argument("--project_id", type=str, default="{{YOUR_PROJECT_ID}}", help="GCP Project ID")
    args = parser.parse_args()

    print(f"Starting Speech-to-Text V2 streaming for project: {args.project_id}")
    
    client = SpeechClient()
    
    requests = generate_audio_requests(project_id=args.project_id)
    
    try:
        responses = client.streaming_recognize(requests=requests)
        
        for response in responses:
            for result in response.results:
                if result.alternatives:
                    print(f"Transcript: {result.alternatives[0].transcript}")
    except Exception as e:
        print(f"Error during streaming: {e}")

if __name__ == "__main__":
    main()
