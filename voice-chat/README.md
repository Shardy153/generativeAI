# Voice-enabled AI Assistant (Whisper + Azure OpenAI + TTS)

A simple voice chat assistant that:
- Records audio from your microphone
- Transcribes speech to text using Whisper
- Sends the text to Azure OpenAI for a response
- Speaks the response aloud using Coqui TTS

## Prerequisites
- Python 3.10+ recommended
- macOS/Linux/Windows
- Microphone access

## Setup

1) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
```

2) Install system libs (if needed)
- macOS (for PyAudio):
```bash
brew install portaudio
```
- Ubuntu/Debian (for PyAudio and sound):
```bash
sudo apt update && sudo apt install -y portaudio19-dev python3-dev libsndfile1
```

3) Install Python dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4) Configure environment variables
Create a `.env` file in this folder with your Azure OpenAI details:
```dotenv
API_KEY=your_azure_openai_api_key
API_ENDPOINT=https://your-resource-name.openai.azure.com/
```

- The script uses the `AzureOpenAI` client. Ensure your Azure resource is set up and the API version/model deployment you intend to use is available.

## Run
```bash
python voice-chat.py
```

On first run, Whisper and TTS models will download; this may take a few minutes.

## Notes
- The script records ~7 seconds per turn by default. Adjust in `record_audio(seconds)` if desired.
- Audio files are saved to the `recordings/` directory; logs are written to `logs/voice_chat.log`.
- The TTS model used is `tts_models/en/ljspeech/tacotron2-DDC`. You can try alternatives from Coqui `TTS`.

## Troubleshooting
- PyAudio install issues on macOS: ensure `brew install portaudio` then reinstall PyAudio: `pip install --no-binary :all: pyaudio`.
- No audio playback: verify output device and permissions; on macOS check System Settings > Privacy & Security > Microphone.
- Slow startup: first-time model downloads are large. Subsequent runs are faster.
- OpenAI/Azure errors: confirm `API_KEY` and `API_ENDPOINT` in `.env`, network access, and correct deployment names/API version on your Azure resource.
