# Autonomous Agent with Postgres Database

An autonomous AI agent specialized in VTuber management and interaction, now configured to use **PostgreSQL** instead of PGLite for better performance, persistence, and scalability.

## 🚀 Key Features

- **Autonomous VTuber Management**: Continuously enhances VTuber experiences through strategic prompts
- **PostgreSQL Database**: Persistent, scalable data storage for all interactions and learning
- **SCB Space Management**: Maintains coherent virtual environments
- **Continuous Learning**: Conducts research and updates knowledge base autonomously
- **Contextual Awareness**: Maintains context across interaction iterations
- **Docker Integration**: Easy deployment with container orchestration

## 📊 Why PostgreSQL over PGLite?

| Feature | PGLite | PostgreSQL |
|---------|---------|------------|
| **Storage** | Single SQLite file | Persistent volumes |
| **Performance** | Limited by SQLite | Optimized for concurrent access |
| **Scalability** | Single process | Multi-user, network accessible |
| **Backup** | Manual file copy | Built-in pg_dump/restore |
| **Extensions** | None | pgvector, full ecosystem |
| **Concurrent Access** | Read-only concurrent | Full ACID transactions |

## 🏗️ Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  Autonomous Agent   │    │   PostgreSQL DB     │    │   VTuber System     │
│                     │    │                     │    │                     │
│ • Autonomous Loop   │────│ • Messages Table    │    │ • NeuroSync API     │
│ • Context Building  │    │ • Facts Table       │    │ • Emotional State   │
│ • Learning Patterns │    │ • Entities Table    │    │ • Response Gen      │
│ • Decision Making   │    │ • Relationships     │    │ • Speech Synthesis  │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
cd autonomous-starter
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

```bash
# 1. Copy environment template
cp environment.example .env

# 2. Edit your API keys and configuration
nano .env

# 3. Start PostgreSQL
npm run docker:postgres

# 4. Start autonomous agent
npm run docker:up

# 5. Verify everything is working
npm run docker:logs
```

### Option 3: Migration from PGLite

```bash
# For existing PGLite users
npm run migrate-to-postgres
```

## ⚙️ Configuration

### Required Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/autonomous_agent
POSTGRES_URL=postgresql://postgres:postgres@localhost:5433/autonomous_agent

# VTuber Integration
VTUBER_ENDPOINT_URL=http://localhost:5001/process_text

# AI Provider (at least one required)
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
GROQ_API_KEY=gsk_your-groq-api-key-here

# Autonomous Agent Settings
AUTONOMOUS_LOOP_INTERVAL=30000
AGENT_NAME=Autoliza
```

### Optional Configuration

```bash
# Social Media Integrations
DISCORD_APPLICATION_ID=your-discord-app-id
DISCORD_API_TOKEN=your-discord-bot-token
TWITTER_USERNAME=your-twitter-username
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Logging
LOG_LEVEL=info
DB_LOGGING=false
```

## 🛠️ Development

### Available Scripts

```bash
# Start services
npm run docker:up              # Start all services
npm run docker:postgres        # Start PostgreSQL only
npm run docker:down           # Stop all services

# Monitoring
npm run docker:logs           # View autonomous agent logs
npm run docker:postgres-logs  # View PostgreSQL logs

# Database access
npm run docker:psql          # Connect to PostgreSQL directly

# Development
npm run dev                  # Development mode with hot reload
npm run build               # Build the application
npm run lint                # Lint the code
```

### Container Management

```bash
# Check container status
docker-compose ps

# Restart services
docker-compose restart autonomous-agent
docker-compose restart postgres

# View real-time logs
docker-compose logs -f

# Access database shell
docker exec -it autonomous-postgres psql -U postgres -d autonomous_agent
```

## 📁 Project Structure

```
autonomous-starter/
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Multi-stage autonomous agent image
├── README.md                   # This file
├── setup.sh                    # Automated setup script
├── environment.example         # Environment template
├── package.json               # Dependencies and scripts
├── scripts/
│   └── migrate-to-postgres.js # Migration helper script
└── src/
    ├── index.ts               # Main character configuration
    ├── plugin-auto/           # Autonomous behavior plugin
    └── plugin-bootstrap/      # Core actions and providers
        ├── actions/           # VTuber interaction actions
        ├── evaluators/        # Decision-making logic
        ├── providers/         # Context providers
        └── services/          # Background services
```

## 🎯 Autonomous Agent Features

### VTuber Integration

- **Strategic Prompting**: Sends contextually aware prompts to VTuber system
- **Emotional State Management**: Tracks and updates VTuber emotional states
- **Response Analysis**: Learns from VTuber responses to improve future interactions
- **Timing Optimization**: Configurable autonomous loop intervals

### Learning Capabilities

- **Contextual Memory**: Stores all interactions in PostgreSQL for long-term learning
- **Pattern Recognition**: Identifies successful interaction patterns
- **Knowledge Building**: Continuously updates its understanding
- **Strategic Planning**: Makes decisions based on accumulated knowledge

### Database Operations

The autonomous agent automatically:
- Stores all VTuber interactions in the `messages` table
- Builds fact relationships in the `facts` table
- Maintains entity relationships for context building
- Tracks performance metrics for continuous improvement

## 🔍 Monitoring and Debugging

### Health Checks

```bash
# Check service status
docker-compose ps

# Test database connectivity
docker exec autonomous-postgres pg_isready -U postgres

# Verify agent health (if health endpoint exists)
curl http://localhost:3001/health
```

### Database Monitoring

```sql
-- View recent VTuber interactions
SELECT content->>'text', created_at 
FROM messages 
WHERE content->>'source' = 'vtuber' 
ORDER BY created_at DESC 
LIMIT 10;

-- Check autonomous agent learning
SELECT content->>'text', content->>'type' 
FROM facts 
WHERE content->>'category' = 'vtuber_management';

-- Monitor agent entities
SELECT id, names, metadata 
FROM entities 
WHERE agent_id = 'autoliza';
```

### Log Analysis

```bash
# Real-time autonomous agent logs
docker-compose logs -f autonomous-agent

# Search for specific patterns
docker-compose logs autonomous-agent | grep "VTuber"
docker-compose logs autonomous-agent | grep "ERROR"

# Database logs
docker-compose logs postgres
```

## 🚨 Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check if ports are in use
   lsof -i :5433  # PostgreSQL
   lsof -i :3001  # Autonomous Agent
   ```

2. **Database Connection Failed**
   ```bash
   # Restart PostgreSQL
   docker-compose restart postgres
   
   # Check PostgreSQL logs
   docker-compose logs postgres
   ```

3. **Missing API Keys**
   ```bash
   # Verify environment variables
   docker exec autonomous-agent printenv | grep API_KEY
   ```

4. **VTuber Connection Issues**
   ```bash
   # Check VTuber endpoint
   curl http://localhost:5001/process_text
   
   # Verify network connectivity
   docker network ls
   docker network inspect docker-vt_default
   ```

### Reset Everything

```bash
# Complete reset
docker-compose down
docker volume rm autonomous-postgres-data
./setup.sh
```

## 💾 Data Management

### Backup Database

```bash
# Create backup
docker exec autonomous-postgres pg_dump -U postgres autonomous_agent > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup script
docker exec autonomous-postgres pg_dump -U postgres -c autonomous_agent | gzip > "backup_$(date +%Y%m%d_%H%M%S).sql.gz"
```

### Restore Database

```bash
# Restore from backup
docker exec -i autonomous-postgres psql -U postgres autonomous_agent < backup.sql

# From compressed backup
gunzip -c backup.sql.gz | docker exec -i autonomous-postgres psql -U postgres autonomous_agent
```

### Migration from PGLite

If you have existing PGLite data:

```bash
# Run migration script
npm run migrate-to-postgres

# Manual backup of PGLite
cp -r elizadb backup/pglite_backup_$(date +%Y%m%d)
```

## 🔗 Integration with VTuber System

The autonomous agent integrates with your VTuber system through:

1. **HTTP API**: Sends prompts to `VTUBER_ENDPOINT_URL`
2. **Contextual Data**: Includes autonomous context in requests
3. **Response Learning**: Stores VTuber responses for future decision-making
4. **Timing Coordination**: Respects VTuber system timing constraints

### Example VTuber Request

```json
{
  "text": "Hello everyone! I'm excited to share what I've been learning today!",
  "autonomous_context": {
    "next_cycle_seconds": 30,
    "agent_name": "Autoliza",
    "cycle_type": "autonomous_decision",
    "timestamp": 1704067200000
  }
}
```

## 📈 Performance Optimization

### Database Optimization

```sql
-- Index for better query performance
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_facts_category ON facts((content->>'category'));
CREATE INDEX idx_entities_agent_id ON entities(agent_id);
```

### Container Resources

```yaml
# In docker-compose.yml
services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
  
  autonomous-agent:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

## 📚 Additional Resources

- [ElizaOS Documentation](https://elizaos.github.io/eliza/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [VTuber System Integration Guide](../README.md)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both PostgreSQL and development setup
5. Submit a pull request

## 📄 License

This project is part of the ElizaOS ecosystem. See the main repository for license information.

---

## 🎉 Success Criteria

You'll know the setup is working when:

- ✅ Both containers start without errors
- ✅ PostgreSQL is accessible on port 5433
- ✅ Autonomous agent responds on port 3001
- ✅ Database tables are created automatically
- ✅ VTuber interactions are logged to PostgreSQL
- ✅ Agent demonstrates autonomous learning behavior

**Happy VTuber Management! 🤖🎭**

# 🤖 Autoliza - Autonomous VTuber Management Agent

Autoliza is an advanced autonomous AI agent designed specifically for VTuber management and interaction. She operates continuously to enhance VTuber experiences through strategic prompts, SCB space management, research, and context learning.

## ✨ Key Features

- **Autonomous Operation**: Continuous learning and decision-making loop
- **Memory Archiving**: Intelligent memory management for optimal performance
- **VTuber Integration**: Direct integration with VTuber systems and SCB space control
- **Multi-Provider AI**: Support for multiple AI providers with intelligent fallback
- **Research Capabilities**: Autonomous web research for knowledge expansion
- **Context Management**: Strategic knowledge storage and retrieval

## 🚀 Quick Start

1. **Setup Environment**:
   ```bash
   cp environment.example .env
   # Edit .env with your configuration
   ```

2. **Configure AI Provider** (choose one):
   - OpenAI: Set `OPENAI_API_KEY`
   - Anthropic: Set `ANTHROPIC_API_KEY` 
   - Groq: Set `GROQ_API_KEY`
   - Livepeer: Set `LIVEPEER_API_KEY` and `LIVEPEER_GATEWAY_URL`

3. **Run the Agent**:
   ```bash
   npm start
   ```

## 🧠 AI Provider Configuration

Autoliza supports multiple AI providers with intelligent fallback capabilities:

### Provider Selection

Set your preferred provider in `.env`:
```bash
# Choose your primary AI provider: "openai", "anthropic", "groq", "livepeer"
MODEL_PROVIDER=livepeer
```

### Livepeer Configuration (Decentralized AI)

```bash
# Livepeer Gateway Configuration
LIVEPEER_GATEWAY_URL=https://dream-gateway.livepeer.cloud
LIVEPEER_API_KEY=your-livepeer-api-key-here
LIVEPEER_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
LIVEPEER_LARGE_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
LIVEPEER_SMALL_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
LIVEPEER_TEMPERATURE=0.6
LIVEPEER_MAX_TOKENS=2048
```

### Automatic Fallback

If no provider is explicitly set or the configured provider is unavailable, Autoliza will:
1. Try OpenAI (if `OPENAI_API_KEY` is set)
2. Try Anthropic (if `ANTHROPIC_API_KEY` is set)  
3. Try Groq (if `GROQ_API_KEY` is set)
4. Fallback to Livepeer (always available)

### Benefits of Livepeer

- **Decentralized**: No single point of failure
- **Cost-effective**: Competitive pricing through distributed network
- **Privacy**: Enhanced privacy through decentralized infrastructure
- **Reliability**: Always available as fallback provider
- **Open Source Models**: Access to leading open-source LLMs

## 📊 Database Configuration

Autoliza uses PostgreSQL for robust data persistence:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/autonomous_agent
```

## 🎯 VTuber Integration

Configure VTuber endpoint for direct interaction:

```bash
VTUBER_ENDPOINT_URL=http://localhost:5001/process_text
```

## 🔧 Advanced Configuration

### Memory Archiving
```bash
MEMORY_ARCHIVING_ENABLED=true
MEMORY_ACTIVE_LIMIT=200
MEMORY_ARCHIVE_HOURS=48
MEMORY_IMPORTANCE_THRESHOLD=0.3
```

### Autonomous Agent Settings
```bash
AUTONOMOUS_LOOP_INTERVAL=30000
AGENT_NAME=Autoliza
```

### Optional Integrations
```bash
# Discord
DISCORD_APPLICATION_ID=your-discord-app-id
DISCORD_API_TOKEN=your-discord-bot-token

# Twitter/X
TWITTER_USERNAME=your-twitter-username
TWITTER_PASSWORD=your-twitter-password

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

## 📝 Logging and Monitoring

Monitor Autoliza's operations:

```bash
LOG_LEVEL=info          # debug, info, warn, error
DB_LOGGING=false        # Enable database query logging
```

## 🔄 Usage Examples

### Setting Livepeer as Primary Provider
```bash
MODEL_PROVIDER=livepeer
LIVEPEER_API_KEY=your_api_key_here
# OpenAI not required when using Livepeer
```

### Multi-Provider Setup with Fallback
```bash
MODEL_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
LIVEPEER_API_KEY=your_livepeer_key  # Fallback if OpenAI fails
```

### Livepeer-Only Setup (No API Keys Required)
```bash
MODEL_PROVIDER=livepeer
# Livepeer provides default endpoint and models
```

## 🛠️ Development

```bash
npm run dev     # Development mode with hot reload
npm run build   # Build for production
npm run test    # Run tests
```

## 📚 Learn More

- [ElizaOS Documentation](https://elizaos.github.io/eliza/)
- [Livepeer AI Documentation](https://docs.livepeer.org/)
- [VTuber Integration Guide](./docs/vtuber-integration.md)

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) file for details.
