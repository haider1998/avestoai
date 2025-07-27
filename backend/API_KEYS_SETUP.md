# 🔑 API Keys Setup Guide

## Required API Keys for AvestoAI Backend

### 1. ElevenLabs API Key (Voice Features)
**Purpose**: Text-to-Speech and Voice Conversations

**How to get it:**
1. Go to [ElevenLabs](https://elevenlabs.io/)
2. Sign up for an account
3. Navigate to your profile settings
4. Copy your API key

**Where to add it:**
- Replace `sk-dummy-elevenlabs-api-key-replace-with-real-key` in your `.env` file
- Or set environment variable: `ELEVENLABS_API_KEY=your_real_key_here`

### 2. OpenAI API Key (Speech-to-Text)
**Purpose**: Whisper Speech-to-Text for voice input

**How to get it:**
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up/login to your account
3. Go to API Keys section
4. Create a new API key

**Where to add it:**
- Replace `sk-dummy-openai-api-key-for-whisper-stt` in your `.env` file
- Or set environment variable: `OPENAI_API_KEY=your_real_key_here`

### 3. Google Cloud Service Account (Already Configured ✅)
**Purpose**: Vertex AI (Gemini), Firestore, and other GCP services

**Status**: ✅ Already configured with `credentials/avestoai-466417-1e5f06659c0e.json`

## Quick Setup Commands

```bash
# 1. Run the setup script (creates .env with dummy keys)
./setup_dev.sh

# 2. Edit the .env file to add your real API keys
nano .env

# 3. Update these lines with your real keys:
ELEVENLABS_API_KEY=your_real_elevenlabs_key_here
OPENAI_API_KEY=your_real_openai_key_here

# 4. Run the application
./run_dev.sh
```

## Environment Variables Summary

```bash
# Google Cloud (Already configured)
GOOGLE_CLOUD_PROJECT=avestoai-466417
GOOGLE_APPLICATION_CREDENTIALS=./credentials/avestoai-466417-1e5f06659c0e.json

# ElevenLabs (Replace with real key)
ELEVENLABS_API_KEY=your_real_elevenlabs_key_here
ELEVENLABS_DEFAULT_VOICE=21m00Tcm4TlvDq8ikWAM

# OpenAI (Replace with real key)
OPENAI_API_KEY=your_real_openai_key_here

# Fi MCP (Already configured)
FI_MCP_BASE_URL=https://fi-mcp-dev-172306289913.asia-south1.run.app

# Feature Flags
ENABLE_VOICE_CONVERSATIONS=true
```

## Testing Voice Features

Once you add the real API keys, you can test:

```bash
# Test TTS endpoint
curl -X POST http://localhost:8080/api/v1/voice/text-to-speech \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is AvestoAI speaking!", "voice_id": "21m00Tcm4TlvDq8ikWAM"}'

# Test available voices
curl http://localhost:8080/api/v1/voice/voices
```

## Cost Considerations

- **ElevenLabs**: Pay per character for TTS (~$0.30 per 1K characters)
- **OpenAI Whisper**: Pay per minute for STT (~$0.006 per minute)
- **Google Vertex AI**: Pay per request for Gemini models

## Security Notes

- ⚠️ Never commit real API keys to version control
- 🔒 Use environment variables or secret management
- 🛡️ Rotate keys regularly
- 📊 Monitor usage to avoid unexpected charges

---

