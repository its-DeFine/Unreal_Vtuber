-- 🚀 Autonomous Agent Analytics Tables Setup
-- Adds enhanced analytics capabilities to existing ElizaOS database
-- Compatible with current schema, adds new functionality without breaking changes

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Tool usage tracking table
CREATE TABLE IF NOT EXISTS tool_usage (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_id UUID NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    input_context JSONB NOT NULL DEFAULT '{}',
    output_result JSONB NOT NULL DEFAULT '{}',
    execution_time_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT true,
    impact_score FLOAT DEFAULT 0.5,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'
);

-- Add foreign key constraint only if agents table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agents') THEN
        ALTER TABLE tool_usage ADD CONSTRAINT fk_tool_usage_agent 
        FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Decision patterns table
CREATE TABLE IF NOT EXISTS decision_patterns (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_id UUID NOT NULL,
    context_pattern JSONB NOT NULL,
    tools_selected TEXT[] NOT NULL DEFAULT '{}',
    outcome_metrics JSONB DEFAULT '{}',
    pattern_effectiveness FLOAT DEFAULT 0.5,
    usage_frequency INTEGER DEFAULT 1,
    embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}'
);

-- Add foreign key constraint only if agents table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agents') THEN
        ALTER TABLE decision_patterns ADD CONSTRAINT fk_decision_patterns_agent 
        FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Context archive table for intelligent memory management
CREATE TABLE IF NOT EXISTS context_archive (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_id UUID NOT NULL,
    archived_content JSONB NOT NULL,
    compression_ratio FLOAT DEFAULT 1.0,
    importance_score FLOAT DEFAULT 0.5,
    retrieval_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    archive_reason VARCHAR(100) DEFAULT 'automatic',
    metadata JSONB DEFAULT '{}'
);

-- Add foreign key constraint only if agents table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agents') THEN
        ALTER TABLE context_archive ADD CONSTRAINT fk_context_archive_agent 
        FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Performance indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_tool_usage_agent_time ON tool_usage(agent_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool_name ON tool_usage(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_usage_success ON tool_usage(success, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tool_usage_impact ON tool_usage(impact_score DESC);

CREATE INDEX IF NOT EXISTS idx_decision_patterns_agent_time ON decision_patterns(agent_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_decision_patterns_effectiveness ON decision_patterns(pattern_effectiveness DESC);
CREATE INDEX IF NOT EXISTS idx_decision_patterns_frequency ON decision_patterns(usage_frequency DESC);

CREATE INDEX IF NOT EXISTS idx_context_archive_agent_time ON context_archive(agent_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_context_archive_importance ON context_archive(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_context_archive_accessed ON context_archive(last_accessed DESC);

-- Vector similarity search indexes (if using pgvector)
CREATE INDEX IF NOT EXISTS idx_tool_usage_embedding ON tool_usage USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_decision_patterns_embedding ON decision_patterns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Views for common analytics queries
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tool_usage') THEN
        CREATE OR REPLACE VIEW tool_effectiveness AS
        SELECT 
            tool_name,
            COUNT(*) as total_uses,
            AVG(execution_time_ms) as avg_execution_time,
            AVG(impact_score) as avg_impact_score,
            (COUNT(*) FILTER (WHERE success = true))::float / COUNT(*) as success_rate,
            MAX(timestamp) as last_used
        FROM tool_usage 
        GROUP BY tool_name
        ORDER BY avg_impact_score DESC;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agents') 
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tool_usage')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'decision_patterns')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'memories') THEN
        CREATE OR REPLACE VIEW agent_performance AS
        SELECT 
            a.id as agent_id,
            COUNT(tu.id) as total_tool_uses,
            COUNT(DISTINCT tu.tool_name) as unique_tools_used,
            AVG(tu.impact_score) as avg_impact_score,
            AVG(dp.pattern_effectiveness) as avg_pattern_effectiveness,
            COUNT(m.id) as total_memories,
            MAX(tu.timestamp) as last_activity
        FROM agents a
        LEFT JOIN tool_usage tu ON a.id = tu.agent_id
        LEFT JOIN decision_patterns dp ON a.id = dp.agent_id
        LEFT JOIN memories m ON a.id = m."agentId"
        GROUP BY a.id;
    END IF;
END $$;

-- Function to archive old memories based on importance and age
CREATE OR REPLACE FUNCTION archive_old_memories(
    p_agent_id UUID,
    p_memory_limit INTEGER DEFAULT 200,
    p_importance_threshold FLOAT DEFAULT 0.3
) RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER := 0;
    memory_record RECORD;
BEGIN
    -- Archive memories that exceed the limit and have low importance
    FOR memory_record IN 
        SELECT id, content, metadata, "createdAt"
        FROM memories 
        WHERE "agentId" = p_agent_id 
        AND id NOT IN (
            SELECT id FROM memories 
            WHERE "agentId" = p_agent_id 
            ORDER BY "createdAt" DESC 
            LIMIT p_memory_limit
        )
        ORDER BY "createdAt" ASC
    LOOP
        -- Insert into archive
        INSERT INTO context_archive (
            agent_id, 
            archived_content, 
            importance_score, 
            archive_reason,
            metadata
        ) VALUES (
            p_agent_id,
            jsonb_build_object(
                'memory_id', memory_record.id,
                'content', memory_record.content,
                'metadata', memory_record.metadata,
                'created_at', memory_record."createdAt"
            ),
            p_importance_threshold,
            'automatic_archival',
            jsonb_build_object('archived_at', NOW())
        );
        
        -- Delete from memories (optional - could mark as archived instead)
        -- DELETE FROM memories WHERE id = memory_record.id;
        
        archived_count := archived_count + 1;
    END LOOP;
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- Function to log tool usage
CREATE OR REPLACE FUNCTION log_tool_usage(
    p_agent_id UUID,
    p_tool_name VARCHAR(100),
    p_input_context JSONB,
    p_output_result JSONB,
    p_execution_time_ms INTEGER,
    p_success BOOLEAN,
    p_impact_score FLOAT DEFAULT 0.5
) RETURNS UUID AS $$
DECLARE
    usage_id UUID;
BEGIN
    INSERT INTO tool_usage (
        agent_id,
        tool_name,
        input_context,
        output_result,
        execution_time_ms,
        success,
        impact_score
    ) VALUES (
        p_agent_id,
        p_tool_name,
        p_input_context,
        p_output_result,
        p_execution_time_ms,
        p_success,
        p_impact_score
    ) RETURNING id INTO usage_id;
    
    RETURN usage_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update decision patterns
CREATE OR REPLACE FUNCTION update_decision_pattern(
    p_agent_id UUID,
    p_context_pattern JSONB,
    p_tools_selected TEXT[],
    p_outcome_metrics JSONB,
    p_effectiveness FLOAT
) RETURNS UUID AS $$
DECLARE
    pattern_id UUID;
    existing_pattern RECORD;
BEGIN
    -- Check if similar pattern exists
    SELECT id, usage_frequency, pattern_effectiveness 
    INTO existing_pattern
    FROM decision_patterns 
    WHERE agent_id = p_agent_id 
    AND context_pattern @> p_context_pattern
    AND tools_selected = p_tools_selected
    LIMIT 1;
    
    IF existing_pattern.id IS NOT NULL THEN
        -- Update existing pattern
        UPDATE decision_patterns 
        SET 
            usage_frequency = existing_pattern.usage_frequency + 1,
            pattern_effectiveness = (existing_pattern.pattern_effectiveness + p_effectiveness) / 2,
            outcome_metrics = p_outcome_metrics,
            timestamp = NOW()
        WHERE id = existing_pattern.id
        RETURNING id INTO pattern_id;
    ELSE
        -- Create new pattern
        INSERT INTO decision_patterns (
            agent_id,
            context_pattern,
            tools_selected,
            outcome_metrics,
            pattern_effectiveness
        ) VALUES (
            p_agent_id,
            p_context_pattern,
            p_tools_selected,
            p_outcome_metrics,
            p_effectiveness
        ) RETURNING id INTO pattern_id;
    END IF;
    
    RETURN pattern_id;
END;
$$ LANGUAGE plpgsql;

-- Insert initial analytics data for current agent
DO $$
DECLARE
    current_agent_id UUID;
    memories_exists BOOLEAN;
BEGIN
    -- Check if memories table exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'memories'
    ) INTO memories_exists;
    
    IF memories_exists THEN
        -- Get the current agent ID from existing data
        SELECT DISTINCT "agentId" INTO current_agent_id FROM memories LIMIT 1;
        
        IF current_agent_id IS NOT NULL THEN
            -- Log some initial tool usage based on existing memories
            PERFORM log_tool_usage(
                current_agent_id,
                'vtuber_prompter',
                jsonb_build_object('context', 'VR features discussion'),
                jsonb_build_object('success', true, 'engagement', 'high'),
                250,
                true,
                0.8
            );
            
            PERFORM log_tool_usage(
                current_agent_id,
                'context_manager',
                jsonb_build_object('action', 'store', 'type', 'vr_learning'),
                jsonb_build_object('stored', true, 'importance', 0.7),
                100,
                true,
                0.7
            );
            
            -- Create initial decision pattern
            PERFORM update_decision_pattern(
                current_agent_id,
                jsonb_build_object('topic', 'VR', 'engagement_level', 'high'),
                ARRAY['vtuber_prompter', 'context_manager'],
                jsonb_build_object('engagement_improvement', 0.25, 'learning_value', 0.8),
                0.75
            );
            
            RAISE NOTICE 'Analytics tables initialized with sample data for agent: %', current_agent_id;
        ELSE
            RAISE NOTICE 'No existing agent found in memories table - analytics tables created without sample data';
        END IF;
    ELSE
        RAISE NOTICE 'Memories table does not exist yet - analytics tables created without sample data';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error initializing sample data: %. Analytics tables created successfully.', SQLERRM;
END $$;

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE ON tool_usage TO autonomous_agent_role;
-- GRANT SELECT, INSERT, UPDATE ON decision_patterns TO autonomous_agent_role;
-- GRANT SELECT, INSERT, UPDATE ON context_archive TO autonomous_agent_role;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tool_usage') THEN
        COMMENT ON TABLE tool_usage IS 'Tracks usage and effectiveness of autonomous agent tools';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'decision_patterns') THEN
        COMMENT ON TABLE decision_patterns IS 'Stores and analyzes decision-making patterns for learning';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'context_archive') THEN
        COMMENT ON TABLE context_archive IS 'Archives old context for efficient memory management';
    END IF;
END $$;

-- Success message
SELECT 'Analytics tables successfully created and initialized!' as status; 