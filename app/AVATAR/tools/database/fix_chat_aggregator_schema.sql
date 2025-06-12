-- 🎯 Chat Aggregator Database Schema Fixes
-- Fixes foreign key constraint issues and adds proper chat aggregation support

-- Add chat aggregator specific tables
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    room_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    author VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    salience_score DECIMAL(5,3) DEFAULT 0.0,
    priority_level VARCHAR(20) DEFAULT 'low',
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraints
    CONSTRAINT fk_chat_messages_agent FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_messages_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

-- Add chat aggregator context updates table
CREATE TABLE IF NOT EXISTS chat_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    room_id UUID NOT NULL,
    context_data JSONB NOT NULL,
    engagement_metrics JSONB DEFAULT '{}',
    attention_state VARCHAR(50) DEFAULT 'casual_monitoring',
    total_messages INTEGER DEFAULT 0,
    high_priority_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraints
    CONSTRAINT fk_chat_contexts_agent FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_contexts_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

-- Add chat aggregator platform status table
CREATE TABLE IF NOT EXISTS platform_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    is_connected BOOLEAN DEFAULT false,
    last_message_at TIMESTAMP WITH TIME ZONE,
    message_count INTEGER DEFAULT 0,
    connection_status VARCHAR(50) DEFAULT 'disconnected',
    metadata JSONB DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraints
    CONSTRAINT fk_platform_status_agent FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    
    -- Unique constraint for agent-platform combination
    CONSTRAINT unique_agent_platform UNIQUE (agent_id, platform)
);

-- Add indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_chat_messages_agent_time ON chat_messages(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_platform ON chat_messages(platform);
CREATE INDEX IF NOT EXISTS idx_chat_messages_salience ON chat_messages(salience_score DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_priority ON chat_messages(priority_level, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_contexts_agent_time ON chat_contexts(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_contexts_attention ON chat_contexts(attention_state);

CREATE INDEX IF NOT EXISTS idx_platform_status_agent ON platform_status(agent_id);
CREATE INDEX IF NOT EXISTS idx_platform_status_platform ON platform_status(platform);
CREATE INDEX IF NOT EXISTS idx_platform_status_updated ON platform_status(updated_at DESC);

-- Create a view for chat aggregator analytics
CREATE OR REPLACE VIEW chat_aggregator_analytics AS
SELECT 
    a.id as agent_id,
    a.name as agent_name,
    COUNT(cm.id) as total_messages,
    COUNT(cm.id) FILTER (WHERE cm.priority_level = 'critical') as critical_messages,
    COUNT(cm.id) FILTER (WHERE cm.priority_level = 'high') as high_priority_messages,
    AVG(cm.salience_score) as avg_salience_score,
    COUNT(DISTINCT cm.platform) as active_platforms,
    MAX(cm.created_at) as last_message_time,
    COUNT(cc.id) as context_updates
FROM agents a
LEFT JOIN chat_messages cm ON a.id = cm.agent_id
LEFT JOIN chat_contexts cc ON a.id = cc.agent_id
GROUP BY a.id, a.name;

-- Insert initial platform status for Autoliza
INSERT INTO platform_status (agent_id, platform, is_connected, connection_status, metadata)
SELECT 
    id,
    platform_name,
    false,
    'ready',
    jsonb_build_object('initialized_at', NOW(), 'mode', 'mock')
FROM agents,
     (VALUES ('twitch'), ('youtube'), ('discord')) AS platforms(platform_name)
WHERE name = 'Autoliza'
ON CONFLICT (agent_id, platform) DO UPDATE SET
    updated_at = NOW(),
    metadata = EXCLUDED.metadata;

-- Update trigger for platform_status
CREATE OR REPLACE FUNCTION update_platform_status_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_status_update_timestamp
    BEFORE UPDATE ON platform_status
    FOR EACH ROW
    EXECUTE FUNCTION update_platform_status_timestamp();

-- Function to get or create a room for chat aggregation
CREATE OR REPLACE FUNCTION get_or_create_chat_room(
    p_agent_id UUID,
    p_agent_name TEXT DEFAULT 'Autoliza'
) RETURNS UUID AS $$
DECLARE
    room_uuid UUID;
BEGIN
    -- Try to find existing room for this agent
    SELECT id INTO room_uuid
    FROM rooms 
    WHERE "agentId" = p_agent_id 
    AND source = 'elizaos'
    LIMIT 1;
    
    -- If no room exists, create one
    IF room_uuid IS NULL THEN
        INSERT INTO rooms (id, "agentId", source, type, name, metadata)
        VALUES (
            p_agent_id, -- Use agent_id as room_id for simplicity
            p_agent_id,
            'elizaos',
            'chat_aggregator',
            p_agent_name || '_chat_room',
            jsonb_build_object('purpose', 'chat_aggregation', 'created_by', 'chat_aggregator_service')
        )
        RETURNING id INTO room_uuid;
    END IF;
    
    RETURN room_uuid;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON chat_messages TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON chat_contexts TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON platform_status TO postgres;
GRANT SELECT ON chat_aggregator_analytics TO postgres;
GRANT EXECUTE ON FUNCTION get_or_create_chat_room(UUID, TEXT) TO postgres;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE '✅ Chat Aggregator Database Schema Setup Complete!';
    RAISE NOTICE '📊 Added tables: chat_messages, chat_contexts, platform_status';
    RAISE NOTICE '🔗 Fixed foreign key constraints for proper memory storage';
    RAISE NOTICE '🎯 ChatAggregatorService can now store contexts properly';
END $$; 