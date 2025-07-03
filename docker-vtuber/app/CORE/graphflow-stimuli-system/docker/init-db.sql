-- Initial database schema for GraphFlow External Stimuli System

-- Create schema
CREATE SCHEMA IF NOT EXISTS graphflow;

-- Set search path
SET search_path TO graphflow, public;

-- Create tables
CREATE TABLE IF NOT EXISTS stimuli_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stimuli_id VARCHAR(255) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'medium',
    decision VARCHAR(50),
    confidence DECIMAL(3,2),
    processing_time_ms INTEGER,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS processing_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stimuli_id VARCHAR(255) REFERENCES stimuli_log(stimuli_id),
    decision_type VARCHAR(50) NOT NULL,
    reasoning TEXT,
    confidence DECIMAL(3,2),
    context_factors JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS execution_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stimuli_id VARCHAR(255) REFERENCES stimuli_log(stimuli_id),
    execution_path VARCHAR(50) NOT NULL,
    system1_response JSONB,
    system2_response JSONB,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    permissions JSONB DEFAULT '{"read": true, "write": true}',
    rate_limit INTEGER DEFAULT 60,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS metrics_snapshot (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,2) NOT NULL,
    labels JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_stimuli_log_status ON stimuli_log(status);
CREATE INDEX idx_stimuli_log_created_at ON stimuli_log(created_at);
CREATE INDEX idx_stimuli_log_source ON stimuli_log(source);
CREATE INDEX idx_stimuli_log_category ON stimuli_log(category);
CREATE INDEX idx_processing_decisions_stimuli_id ON processing_decisions(stimuli_id);
CREATE INDEX idx_execution_results_stimuli_id ON execution_results(stimuli_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_metrics_snapshot_name_timestamp ON metrics_snapshot(metric_name, timestamp);

-- Create views
CREATE OR REPLACE VIEW stimuli_processing_summary AS
SELECT 
    sl.stimuli_id,
    sl.content,
    sl.source,
    sl.category,
    sl.priority,
    sl.decision,
    sl.confidence,
    sl.processing_time_ms,
    sl.status,
    sl.created_at,
    pd.reasoning as decision_reasoning,
    er.execution_path,
    er.success as execution_success,
    er.execution_time_ms
FROM stimuli_log sl
LEFT JOIN processing_decisions pd ON sl.stimuli_id = pd.stimuli_id
LEFT JOIN execution_results er ON sl.stimuli_id = er.stimuli_id;

CREATE OR REPLACE VIEW processing_metrics AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as total_stimuli,
    AVG(processing_time_ms) as avg_processing_time_ms,
    MAX(processing_time_ms) as max_processing_time_ms,
    MIN(processing_time_ms) as min_processing_time_ms,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count
FROM stimuli_log
GROUP BY DATE_TRUNC('hour', created_at);

-- Insert default API key for testing (hash of 'test_api_key_123')
INSERT INTO api_keys (key_hash, name, permissions, rate_limit, is_active)
VALUES (
    '$2b$12$KIXxPfnK3Z9Z0Z0Z0Z0Z0Z', -- This is a placeholder hash
    'Test API Key',
    '{"read": true, "write": true}',
    100,
    true
) ON CONFLICT DO NOTHING;

-- Create functions
CREATE OR REPLACE FUNCTION update_last_used_at()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE api_keys 
    SET last_used_at = CURRENT_TIMESTAMP 
    WHERE key_hash = NEW.key_hash;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA graphflow TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA graphflow TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA graphflow TO postgres;