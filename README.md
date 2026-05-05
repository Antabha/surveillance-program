I developed a serverless acoustic monitoring application designed for real-time environment auditing. 
This project demonstrates how gRPC streaming and Cloud-native AI can be leveraged to monitor and transcribe audio feeds in high-security or restricted environments.

Device Mic (Int16 PCM) -> WSS -> Cloud Run (FastAPI Bridge) -> gRPC -> Google Speech-to-Text -> gRPC -> Cloud Run -> WSS -> Receiver Clients (Live Text)
