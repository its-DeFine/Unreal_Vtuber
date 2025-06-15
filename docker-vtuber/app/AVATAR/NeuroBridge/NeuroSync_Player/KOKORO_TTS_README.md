# Kokoro TTS Integration for NeuroSync Player

This document provides a quick overview of the Kokoro TTS integration that has been added to the NeuroSync Player system.

## 🎯 What's New

The NeuroSync Player now supports **Kokoro TTS** as a third TTS provider option alongside Local TTS and ElevenLabs. This provides:

- **High-quality local TTS** without external API dependencies
- **Multiple voice options** with natural-sounding speech
- **Low latency** compared to cloud-based services
- **Privacy-focused** - all processing happens locally

## 🚀 Quick Start

1. **Set up your Kokoro TTS server** (see your existing Kokoro server documentation)

2. **Configure NeuroSync Player**:
   ```bash
   export TTS_PROVIDER=kokoro
   export KOKORO_TTS_SERVER_URL=http://localhost:6006
   ```

3. **Run your application** - it will automatically use Kokoro TTS!

4. **Test the integration**:
   ```bash
   python test_kokoro_integration.py
   ```

## 📁 Files Added/Modified

### New Files
- `utils/tts/kokoro_tts.py` - Kokoro TTS implementation
- `test_kokoro_integration.py` - Integration test suite
- `examples/kokoro_tts_example.py` - Usage examples
- `docs/KOKORO_TTS_SETUP.md` - Detailed setup guide
- `KOKORO_TTS_README.md` - This overview file

### Modified Files
- `config.py` - Added TTS provider configuration system
- `utils/tts/tts_bridge.py` - Updated to support multiple TTS providers
- `utils/llm/llm_initialiser.py` - Updated to use new configuration system

## 🎭 Supported Voices

The system includes voice mapping for easy switching:

| Common Name | Kokoro Voice ID | Description |
|-------------|----------------|-------------|
| Sarah | af_sarah | Adult Female |
| Adam | am_adam | Adult Male |
| Emma | bf_emma | British Female |
| George | bm_george | British Male |
| Alice | af_alice | Adult Female |
| Nicole | af_nicole | Adult Female |

## ⚙️ Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `TTS_PROVIDER` | `local` | Set to `kokoro` to use Kokoro TTS |
| `KOKORO_TTS_SERVER_URL` | `http://localhost:6006` | Your Kokoro server URL |
| `KOKORO_DEFAULT_VOICE` | `af_sarah` | Default voice to use |
| `KOKORO_TTS_TIMEOUT` | `30` | Request timeout in seconds |
| `KOKORO_TTS_LANGUAGE` | `en` | Language code |

## 🧪 Testing

Run the test suite to verify everything is working:

```bash
# Set environment
export TTS_PROVIDER=kokoro

# Run tests
python test_kokoro_integration.py
```

The test will:
- ✅ Check configuration is loaded correctly
- ✅ Test connection to your Kokoro server
- ✅ Generate test audio with different voices
- ✅ Verify integration with TTS worker system

## 📚 Examples and Documentation

- **`examples/kokoro_tts_example.py`** - Practical usage examples
- **`docs/KOKORO_TTS_SETUP.md`** - Complete setup guide with troubleshooting
- **`test_kokoro_integration.py`** - Integration test and verification

## 🔄 Backward Compatibility

The integration maintains full backward compatibility:
- Existing ElevenLabs configurations continue to work
- Legacy `USE_LOCAL_AUDIO` parameter is still supported
- No changes needed to existing application code

## 🎵 Usage Examples

### Direct Usage
```python
from utils.tts.kokoro_tts import get_kokoro_audio

audio_bytes = get_kokoro_audio("Hello world!", "Sarah")
with open("output.wav", "wb") as f:
    f.write(audio_bytes)
```

### With TTS Worker System
```python
# Just set the environment variable
export TTS_PROVIDER=kokoro

# Your existing code works automatically!
```

## 🛠️ Troubleshooting

**Common issues and solutions:**

1. **Connection refused** → Check Kokoro server is running
2. **Voice not found** → Use supported voice names (see table above)
3. **Timeout errors** → Increase `KOKORO_TTS_TIMEOUT` value
4. **No audio generated** → Check server logs and test with simple text

For detailed troubleshooting, see `docs/KOKORO_TTS_SETUP.md`.

## 🎉 Integration Benefits

- **Seamless switching** between TTS providers via environment variables
- **Robust error handling** with detailed logging and fallback options
- **Voice mapping system** for easy voice selection
- **Performance monitoring** with request timing and health checks
- **Privacy protection** - no external API calls when using Kokoro

## 📞 Support

1. Run `python test_kokoro_integration.py` to diagnose issues
2. Check the detailed setup guide in `docs/KOKORO_TTS_SETUP.md`
3. Review console logs for detailed error information
4. Verify Kokoro server is accessible and functioning

---

**Ready to use Kokoro TTS?** Set `export TTS_PROVIDER=kokoro` and enjoy high-quality local text-to-speech! 🎙️ 