-- Autonomous Agent Statistics & Evolution Migration
-- This migration enables full statistics tracking, conversation storage, and evolution history

-- Ensure all analytics tables exist and are optimized

-- Add indexes for performance on existing tables if they don't exist
CREATE INDEX IF NOT EXISTS idx_tool_usage_timestamp ON tool_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool_name ON tool_usage(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_usage_agent ON tool_usage(agent_id);

CREATE INDEX IF NOT EXISTS idx_decision_patterns_effectiveness ON decision_patterns(effectiveness_score DESC);
CREATE INDEX IF NOT EXISTS idx_decision_patterns_frequency ON decision_patterns(usage_frequency DESC);

-- Add conversation storage table
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(255) PRIMARY KEY,
    iteration INTEGER NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    agents JSONB,
    messages JSONB,
    outcome JSONB,
    tools_triggered JSONB,
    duration FLOAT,
    search_vector tsvector
);

CREATE INDEX IF NOT EXISTS idx_conversations_iteration ON conversations(iteration);
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);
CREATE INDEX IF NOT EXISTS idx_conversations_search ON conversations USING GIN(search_vector);

-- Add evolution tracking table
CREATE TABLE IF NOT EXISTS evolution_history (
    id VARCHAR(255) PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    target_file TEXT,
    modification_type VARCHAR(50),
    expected_improvement FLOAT,
    actual_improvement FLOAT,
    risk_level VARCHAR(20),
    backup_path TEXT,
    status VARCHAR(50),
    performance_impact JSONB,
    rollback_performed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_evolution_history_timestamp ON evolution_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_evolution_history_status ON evolution_history(status);

-- Add statistics summary table for fast queries
CREATE TABLE IF NOT EXISTS statistics_summary (
    date DATE PRIMARY KEY,
    total_cycles INTEGER DEFAULT 0,
    successful_cycles INTEGER DEFAULT 0,
    total_tools_executed INTEGER DEFAULT 0,
    avg_decision_time FLOAT,
    avg_memory_usage FLOAT,
    total_errors INTEGER DEFAULT 0,
    performance_score FLOAT,
    evolution_changes INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create view for tool effectiveness
CREATE OR REPLACE VIEW tool_effectiveness AS
SELECT 
    tool_name,
    COUNT(*) as total_uses,
    AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
    AVG(execution_time) as avg_execution_time,
    COUNT(DISTINCT agent_id) as unique_agents
FROM tool_usage
GROUP BY tool_name;

-- Create view for agent performance
CREATE OR REPLACE VIEW agent_performance AS
SELECT 
    agent_id,
    COUNT(DISTINCT iteration) as total_iterations,
    AVG(decision_quality) as avg_decision_quality,
    COUNT(CASE WHEN outcome = 'success' THEN 1 END) as successful_outcomes,
    COUNT(CASE WHEN outcome = 'failure' THEN 1 END) as failed_outcomes,
    AVG(response_time) as avg_response_time
FROM agent_metrics
GROUP BY agent_id;

-- Add migration tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations (version) VALUES ('001_enable_full_statistics') ON CONFLICT DO NOTHING;