#!/usr/bin/env node

/**
 * Migration script to help transition from PGLite to Postgres
 * This script:
 * 1. Backs up existing PGLite data if it exists
 * 2. Helps set up Postgres connection
 * 3. Validates the database setup
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('🔄 Autonomous Agent: PGLite to Postgres Migration');
console.log('================================================');

// Configuration
const PGLITE_DB_PATH = path.join(__dirname, '..', 'elizadb');
const BACKUP_DIR = path.join(__dirname, '..', 'backup');
const ENV_FILE = path.join(__dirname, '..', '.env');

async function checkExistingPGLite() {
  console.log('\n1. 🔍 Checking for existing PGLite database...');
  
  if (fs.existsSync(PGLITE_DB_PATH)) {
    console.log('   ✅ Found existing PGLite database at:', PGLITE_DB_PATH);
    
    // Check if it has data
    const files = fs.readdirSync(PGLITE_DB_PATH);
    if (files.length > 0) {
      console.log('   📊 Database contains data - backup recommended');
      return true;
    } else {
      console.log('   📭 Database appears empty');
      return false;
    }
  } else {
    console.log('   ℹ️  No existing PGLite database found');
    return false;
  }
}

async function backupPGLite() {
  console.log('\n2. 💾 Creating backup of PGLite data...');
  
  try {
    // Create backup directory
    if (!fs.existsSync(BACKUP_DIR)) {
      fs.mkdirSync(BACKUP_DIR, { recursive: true });
    }
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = path.join(BACKUP_DIR, `pglite-backup-${timestamp}`);
    
    // Copy the entire elizadb directory
    execSync(`cp -r "${PGLITE_DB_PATH}" "${backupPath}"`, { stdio: 'inherit' });
    
    console.log('   ✅ Backup created at:', backupPath);
    console.log('   💡 You can restore this backup if needed');
    
    return backupPath;
  } catch (error) {
    console.error('   ❌ Backup failed:', error.message);
    throw error;
  }
}

async function createEnvFile() {
  console.log('\n3. ⚙️  Setting up environment configuration...');
  
  const envTemplate = `# =================================
# AUTONOMOUS AGENT CONFIGURATION
# =================================

# Database Configuration - Postgres (instead of PGLite)
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/autonomous_agent
POSTGRES_URL=postgresql://postgres:postgres@localhost:5433/autonomous_agent
DB_TYPE=postgres

# VTuber Integration
VTUBER_ENDPOINT_URL=http://localhost:5001/process_text

# Autonomous Agent Settings
AUTONOMOUS_LOOP_INTERVAL=30000
AGENT_NAME=Autoliza

# =================================
# AI PROVIDER API KEYS (REQUIRED)
# =================================

# OpenAI (Required for most functionality)
OPENAI_API_KEY=your-openai-api-key-here

# Anthropic (Alternative AI provider)
ANTHROPIC_API_KEY=your-anthropic-key-here

# Groq (Fast inference alternative)
GROQ_API_KEY=your-groq-api-key-here

# =================================
# LOGGING AND MONITORING
# =================================

LOG_LEVEL=info
DB_LOGGING=false

# =================================
# DEVELOPMENT SETTINGS
# =================================

NODE_ENV=development
PORT=3001
DEV_MODE=true
`;

  if (fs.existsSync(ENV_FILE)) {
    console.log('   ⚠️  .env file already exists - creating .env.postgres as template');
    fs.writeFileSync(ENV_FILE + '.postgres', envTemplate);
    console.log('   📝 Created .env.postgres template file');
    console.log('   💡 Review and merge settings into your existing .env file');
  } else {
    fs.writeFileSync(ENV_FILE, envTemplate);
    console.log('   ✅ Created .env file with Postgres configuration');
    console.log('   ⚠️  IMPORTANT: Update API keys in .env file before starting');
  }
}

async function validateDockerSetup() {
  console.log('\n4. 🐳 Validating Docker setup...');
  
  try {
    // Check if Docker is running
    execSync('docker --version', { stdio: 'pipe' });
    console.log('   ✅ Docker is installed');
    
    // Check if docker-compose is available
    try {
      execSync('docker-compose --version', { stdio: 'pipe' });
      console.log('   ✅ docker-compose is available');
    } catch {
      try {
        execSync('docker compose version', { stdio: 'pipe' });
        console.log('   ✅ docker compose is available');
      } catch {
        console.log('   ❌ docker-compose not found - please install Docker Compose');
        return false;
      }
    }
    
    return true;
  } catch (error) {
    console.log('   ❌ Docker not found - please install Docker');
    return false;
  }
}

async function showNextSteps() {
  console.log('\n🎯 Next Steps:');
  console.log('================');
  console.log('1. Update your .env file with your API keys');
  console.log('2. Start the Postgres database:');
  console.log('   cd autonomous-starter');
  console.log('   docker-compose up postgres -d');
  console.log('');
  console.log('3. Verify Postgres is running:');
  console.log('   docker-compose logs postgres');
  console.log('');
  console.log('4. Start the autonomous agent:');
  console.log('   docker-compose up autonomous-agent');
  console.log('');
  console.log('5. (Optional) Connect to Postgres directly:');
  console.log('   docker exec -it autonomous-postgres psql -U postgres -d autonomous_agent');
  console.log('');
  console.log('📊 Database Benefits:');
  console.log('- ✅ Persistent data storage');
  console.log('- ✅ Better performance for large datasets');
  console.log('- ✅ Full SQL capabilities');
  console.log('- ✅ Data backup and recovery');
  console.log('- ✅ Concurrent access support');
  console.log('');
  console.log('🔗 VTuber Integration:');
  console.log('The autonomous agent will connect to your VTuber system through');
  console.log('the configured VTUBER_ENDPOINT_URL and store all interactions');
  console.log('in the Postgres database for learning and context building.');
}

async function main() {
  try {
    const hasExistingData = await checkExistingPGLite();
    
    if (hasExistingData) {
      await backupPGLite();
    }
    
    await createEnvFile();
    const dockerOk = await validateDockerSetup();
    
    if (dockerOk) {
      await showNextSteps();
    } else {
      console.log('\n❌ Please install Docker and Docker Compose first');
      console.log('   Visit: https://docs.docker.com/get-docker/');
    }
    
    console.log('\n✅ Migration preparation complete!');
    
  } catch (error) {
    console.error('\n❌ Migration failed:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
} 