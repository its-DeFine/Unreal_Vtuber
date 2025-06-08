-- ElizaOS Complete Database Schema Initialization with missing channels table
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

-- Create ElizaOS Core Tables
CREATE TABLE IF NOT EXISTS "agents" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "enabled" boolean DEFAULT true NOT NULL,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "updatedAt" timestamptz DEFAULT now() NOT NULL,
    "name" text,
    "username" text,
    "system" text,
    "bio" jsonb NOT NULL,
    "message_examples" jsonb DEFAULT '[]'::jsonb,
    "post_examples" jsonb DEFAULT '[]'::jsonb,
    "topics" jsonb DEFAULT '[]'::jsonb,
    "adjectives" jsonb DEFAULT '[]'::jsonb,
    "knowledge" jsonb DEFAULT '[]'::jsonb,
    "plugins" jsonb DEFAULT '[]'::jsonb,
    "settings" jsonb DEFAULT '{}'::jsonb,
    "style" jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT "name_unique" UNIQUE("name")
);

-- Create the missing channels table (critical!)
CREATE TABLE IF NOT EXISTS "channels" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "agentId" uuid NOT NULL,
    "serverId" text NOT NULL,
    "serverName" text,
    "channelId" text NOT NULL,
    "channelName" text,
    "channelType" text DEFAULT 'text' NOT NULL,
    "isActive" boolean DEFAULT true NOT NULL,
    "metadata" jsonb DEFAULT '{}'::jsonb,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "updatedAt" timestamptz DEFAULT now() NOT NULL,
    CONSTRAINT "unique_agent_server_channel" UNIQUE("agentId","serverId","channelId")
);

-- Rest of core tables...
CREATE TABLE IF NOT EXISTS "cache" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "key" text NOT NULL,
    "agentId" uuid NOT NULL,
    "value" jsonb NOT NULL,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "expiresAt" timestamptz,
    CONSTRAINT "cache_key_agent_unique" UNIQUE("key","agentId")
);

CREATE TABLE IF NOT EXISTS "entities" (
    "id" uuid PRIMARY KEY NOT NULL,
    "agentId" uuid NOT NULL,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "names" text[] DEFAULT '{}'::text[],
    "metadata" jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT "id_agent_id_unique" UNIQUE("id","agentId")
);

CREATE TABLE IF NOT EXISTS "worlds" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "agentId" uuid NOT NULL,
    "name" text NOT NULL,
    "metadata" jsonb,
    "serverId" text NOT NULL,
    "createdAt" timestamptz DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "rooms" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "agentId" uuid,
    "source" text NOT NULL,
    "type" text NOT NULL,
    "serverId" text,
    "worldId" uuid,
    "name" text,
    "metadata" jsonb,
    "channelId" text,
    "createdAt" timestamptz DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS "memories" (
    "id" uuid PRIMARY KEY NOT NULL,
    "type" text NOT NULL,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "content" jsonb NOT NULL,
    "entityId" uuid,
    "agentId" uuid,
    "roomId" uuid,
    "worldId" uuid,
    "unique" boolean DEFAULT true NOT NULL,
    "metadata" jsonb DEFAULT '{}'::jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS "participants" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "entityId" uuid,
    "roomId" uuid,
    "agentId" uuid,
    "roomState" text
);

CREATE TABLE IF NOT EXISTS "relationships" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "sourceEntityId" uuid NOT NULL,
    "targetEntityId" uuid NOT NULL,
    "agentId" uuid NOT NULL,
    "tags" text[],
    "metadata" jsonb,
    CONSTRAINT "unique_relationship" UNIQUE("sourceEntityId","targetEntityId","agentId")
);

CREATE TABLE IF NOT EXISTS "logs" (
    "id" uuid DEFAULT gen_random_uuid() NOT NULL,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "entityId" uuid NOT NULL,
    "body" jsonb NOT NULL,
    "type" text NOT NULL,
    "roomId" uuid NOT NULL
);

CREATE TABLE IF NOT EXISTS "embeddings" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "memory_id" uuid,
    "created_at" timestamptz DEFAULT now() NOT NULL,
    "dim_384" vector(384),
    "dim_512" vector(512),
    "dim_768" vector(768),
    "dim_1024" vector(1024),
    "dim_1536" vector(1536),
    "dim_3072" vector(3072)
);

CREATE TABLE IF NOT EXISTS "components" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "entityId" uuid NOT NULL,
    "agentId" uuid NOT NULL,
    "roomId" uuid NOT NULL,
    "worldId" uuid,
    "sourceEntityId" uuid,
    "type" text NOT NULL,
    "data" jsonb DEFAULT '{}'::jsonb,
    "createdAt" timestamptz DEFAULT now() NOT NULL
);

-- Create Foreign Key Constraints
ALTER TABLE "cache" ADD CONSTRAINT "cache_agentId_agents_id_fk" 
    FOREIGN KEY ("agentId") REFERENCES "public"."agents"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "channels" ADD CONSTRAINT "channels_agentId_agents_id_fk" 
    FOREIGN KEY ("agentId") REFERENCES "public"."agents"("id") ON DELETE cascade ON UPDATE no action;

-- Insert default agent (using the ID from the logs)
INSERT INTO agents (id, name, username, system, bio, settings, enabled)
VALUES (
    'b850bc30-45f8-0041-a00a-83df46d8555d'::uuid,
    'Autoliza',
    'autoliza',
    'You are Autoliza, an autonomous AI agent specialized in VTuber management and interaction.',
    '["Autonomous VTuber management agent", "Continuous learning capabilities", "Strategic prompting specialist"]'::jsonb,
    '{
        "AUTONOMOUS_LOOP_INTERVAL": "30000",
        "MEMORY_ARCHIVING_ENABLED": "true",
        "MEMORY_ACTIVE_LIMIT": "200"
    }'::jsonb,
    true
) ON CONFLICT (name) DO NOTHING;

-- Insert default entity for the agent
INSERT INTO entities (id, "agentId", names, metadata)
VALUES (
    'b850bc30-45f8-0041-a00a-83df46d8555d'::uuid,
    'b850bc30-45f8-0041-a00a-83df46d8555d'::uuid,
    ARRAY['Autoliza', 'Autonomous Agent', 'VTuber Manager'],
    '{"type": "agent", "role": "autonomous_manager"}'::jsonb
) ON CONFLICT (id, "agentId") DO NOTHING;

-- Create default world and room
INSERT INTO worlds (id, "agentId", name, "serverId", metadata)
VALUES (
    '95ec3993-e7e3-4a19-b812-f2bc19cb0e39'::uuid,
    'b850bc30-45f8-0041-a00a-83df46d8555d'::uuid,
    'Autonomous World',
    '00000000-0000-0000-0000-000000000000',
    '{"type": "autonomous", "purpose": "agent_operations"}'::jsonb
) ON CONFLICT DO NOTHING;

INSERT INTO rooms (id, "agentId", source, type, "serverId", "worldId", name, metadata)
VALUES (
    'room-95ec3993-e7e3-4a19-b812-f2bc19cb0e39'::uuid,
    'b850bc30-45f8-0041-a00a-83df46d8555d'::uuid,
    'autonomous',
    'agent_operations',
    '00000000-0000-0000-0000-000000000000',
    '95ec3993-e7e3-4a19-b812-f2bc19cb0e39'::uuid,
    'Autonomous Operations Room',
    '{"type": "autonomous", "purpose": "operations"}'::jsonb
) ON CONFLICT DO NOTHING;

-- Insert default channels for the servers we see in the logs
INSERT INTO channels ("agentId", "serverId", "serverName", "channelId", "channelName", "channelType", "isActive", metadata)
VALUES 
(
    'b850bc30-45f8-0041-a00a-83df46d8555d'::uuid,
    '00000000-0000-0000-0000-000000000000',
    'Default Server',
    'general',
    'General',
    'text',
    true,
    '{"type": "autonomous", "purpose": "default_channel"}'::jsonb
),
(
    'b850bc30-45f8-0041-a00a-83df46d8555d'::uuid,
    '95ec3993-e7e3-4a19-b812-f2bc19cb0e39',
    'Autonomous Server',  
    'autonomous-channel',
    'Autonomous Channel',
    'text',
    true,
    '{"type": "autonomous", "purpose": "agent_operations"}'::jsonb
) ON CONFLICT ("agentId", "serverId", "channelId") DO NOTHING;

-- Create Indexes
CREATE INDEX IF NOT EXISTS "idx_channels_agent" ON "channels" USING btree ("agentId");
CREATE INDEX IF NOT EXISTS "idx_channels_server" ON "channels" USING btree ("serverId");
CREATE INDEX IF NOT EXISTS "idx_channels_active" ON "channels" USING btree ("isActive");

SELECT 'Database schema initialized successfully with channels table!' as result; 