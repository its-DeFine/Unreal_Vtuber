# Local AI Plugin

This plugin provides local AI model capabilities through the ElizaOS platform, supporting text generation, image analysis, speech synthesis, and audio transcription.

## Usage

Add the plugin to your character configuration:

```json
"plugins": ["@elizaos/plugin-local-ai"]
```

## Configuration

The plugin requires these environment variables (can be set in .env file or character settings):

```json
"settings": {
  "USE_LOCAL_AI": true,
  "USE_STUDIOLM_TEXT_MODELS": false,

  "STUDIOLM_SERVER_URL": "http://localhost:1234",
  "STUDIOLM_SMALL_MODEL": "lmstudio-community/deepseek-r1-distill-qwen-1.5b",
  "STUDIOLM_MEDIUM_MODEL": "deepseek-r1-distill-qwen-7b",
  "STUDIOLM_EMBEDDING_MODEL": false
}
```

Or in `.env` file:

```env
# Local AI Configuration
USE_LOCAL_AI=true
USE_STUDIOLM_TEXT_MODELS=false

# StudioLM Configuration
STUDIOLM_SERVER_URL=http://localhost:1234
STUDIOLM_SMALL_MODEL=lmstudio-community/deepseek-r1-distill-qwen-1.5b
STUDIOLM_MEDIUM_MODEL=deepseek-r1-distill-qwen-7b
STUDIOLM_EMBEDDING_MODEL=false
```

### Configuration Options

#### Text Model Source (Choose One)

- `USE_STUDIOLM_TEXT_MODELS`: Enable StudioLM text models

#### StudioLM Settings

- `STUDIOLM_SERVER_URL`: StudioLM API endpoint (default: http://localhost:1234)
- `STUDIOLM_SMALL_MODEL`: Model for lighter tasks
- `STUDIOLM_MEDIUM_MODEL`: Model for standard tasks
- `STUDIOLM_EMBEDDING_MODEL`: Model for embeddings (or false to disable)

## Features

The plugin provides these model classes:

- `TEXT_SMALL`: Fast, efficient text generation using smaller models
- `TEXT_LARGE`: More capable text generation using larger models
- `IMAGE_DESCRIPTION`: Local image analysis using Florence-2 vision model
- `TEXT_TO_SPEECH`: Local text-to-speech synthesis
- `TRANSCRIPTION`: Local audio transcription using Whisper

### Image Analysis

```typescript
const { title, description } = await runtime.useModel(
  ModelType.IMAGE_DESCRIPTION,
  'https://example.com/image.jpg'
);
```

### Text-to-Speech

```typescript
const audioStream = await runtime.useModel(ModelType.TEXT_TO_SPEECH, 'Text to convert to speech');
```

### Audio Transcription

```typescript
const transcription = await runtime.useModel(ModelType.TRANSCRIPTION, audioBuffer);
```

### Text Generation

```typescript
// Using small model
const smallResponse = await runtime.useModel(ModelType.TEXT_SMALL, {
  context: 'Generate a short response',
  stopSequences: [],
});

// Using large model
const largeResponse = await runtime.useModel(ModelType.TEXT_LARGE, {
  context: 'Generate a detailed response',
  stopSequences: [],
});
```

## Model Sources

### 1. StudioLM (LM Studio)

- Local inference server for running various open models
- Supports chat completion API similar to OpenAI
- Configure with `USE_STUDIOLM_TEXT_MODELS=true`
- Supports both small and medium-sized models
- Optional embedding model support

Note: The plugin validates that only one text model source is enabled at a time to prevent conflicts.
