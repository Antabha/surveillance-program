import os
import sys
from typing import Iterator

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

def generate_audio_requests(
    project_id: str,
    recognizer_id: str = "_",
    location: str = "global",
) -> Iterator[cloud_speech.StreamingRecognizeRequest]:
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
    yield cloud_speech.StreamingRecognizeRequest(audio=b"\x00" * 1024)

def main():
    project_id = "{{YOUR_PROJECT_ID}}"
    print(f"Initializing SpeechClient for project {project_id}...")
    try:
        client = SpeechClient()
        requests = generate_audio_requests(project_id=project_id)
        responses = client.streaming_recognize(requests=requests)
        # Pulling the first item will block until headers are returned or an error occurs
        for response in responses:
            pass
        print("Connection Successful")
    except Exception as e:
        error_msg = str(e).lower()
        if "403" in error_msg or "401" in error_msg or "credentials" in error_msg:
            print(f"Error: {e}")
            sys.exit(1)
        else:
            # Reached the API successfully but got a processing error (like 400 bad audio)
            print("Connection Successful")

if __name__ == "__main__":
    main()
