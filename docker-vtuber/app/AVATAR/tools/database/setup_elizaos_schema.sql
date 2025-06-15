-- ElizaOS Complete Database Schema Initialization
-- This file creates all required tables for ElizaOS autonomous agent functionality

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
    "metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT "fragment_metadata_check" CHECK (
        CASE 
            WHEN metadata->>'type' = 'fragment' THEN
                metadata ? 'documentId' AND 
                metadata ? 'position'
            ELSE true
        END
    ),
    CONSTRAINT "document_metadata_check" CHECK (
        CASE 
            WHEN metadata->>'type' = 'document' THEN
                metadata ? 'timestamp'
            ELSE true
        END
    )
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
    "dim_3072" vector(3072),
    CONSTRAINT "embedding_source_check" CHECK ("memory_id" IS NOT NULL)
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

CREATE TABLE IF NOT EXISTS "tasks" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "name" text NOT NULL,
    "description" text NOT NULL,
    "room_id" uuid,
    "world_id" uuid,
    "agent_id" uuid NOT NULL,
    "tags" text[],
    "metadata" jsonb,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now()
);

-- Create the missing message_servers table that the autonomous starter needs
CREATE TABLE IF NOT EXISTS "message_servers" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "agentId" uuid NOT NULL,
    "serverId" text NOT NULL,
    "serverName" text,
    "serverType" text NOT NULL,
    "isActive" boolean DEFAULT true NOT NULL,
    "metadata" jsonb DEFAULT '{}'::jsonb,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "updatedAt" timestamptz DEFAULT now() NOT NULL,
    CONSTRAINT "unique_agent_server" UNIQUE("agentId","serverId")
);

-- Add Facts table for autonomous memory archiving
CREATE TABLE IF NOT EXISTS "facts" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
    "type" text NOT NULL,
    "createdAt" timestamptz DEFAULT now() NOT NULL,
    "content" jsonb NOT NULL,
    "entityId" uuid,
    "agentId" uuid,
    "roomId" uuid,
    "worldId" uuid,
    "metadata" jsonb DEFAULT '{}'::jsonb NOT NULL
);

-- Add Memory Archive table for the autonomous memory archiving system
CREATE TABLE IF NOT EXISTS "memory_archive" (
    "id" uuid PRIMARY KEY NOT NULL,
    "original_memory_id" uuid NOT NULL,
    "type" text NOT NULL,
    "content" jsonb NOT NULL,
    "entityId" uuid,
    "agentId" uuid,
    "roomId" uuid,
    "worldId" uuid,
    "metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
    "archived_at" timestamptz DEFAULT now() NOT NULL,
    "original_created_at" timestamptz NOT NULL,
    "importance_score" decimal(5,3) DEFAULT 0.0,
    "access_count" integer DEFAULT 0
);

-- Create Foreign Key Constraints
ALTER TABLE "cache" ADD CONSTRAINT "cache_agentId_agents_id_fk" 
    FOREIGN KEY ("agentId") REFERENCES "public"."agents"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "components" ADD CONSTRAINT "components_entityId_entities_id_fk" 
    FOREIGN KEY ("entityId") REFERENCES "public"."entities"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "components" ADD CONSTRAINT "components_agentId_agents_id_fk" 
    FOREIGN KEY ("agentId") REFERENCES "public"."agents"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "components" ADD CONSTRAINT "components_roomId_rooms_id_fk" 
    FOREIGN KEY ("roomId") REFERENCES "public"."rooms"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "components" ADD CONSTRAINT "components_worldId_worlds_id_fk" 
    FOREIGN KEY ("worldId") REFERENCES "public"."worlds"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "embeddings" ADD CONSTRAINT "embeddings_memory_id_memories_id_fk" 
    FOREIGN KEY ("memory_id") REFERENCES "public"."memories"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "entities" ADD CONSTRAINT "entities_agentId_agents_id_fk" 
    FOREIGN KEY ("agentId") REFERENCES "public"."agents"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "participants" ADD CONSTRAINT "fk_user" 
    FOREIGN KEY ("entityId") REFERENCES "public"."entities"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "relationships" ADD CONSTRAINT "relationships_sourceEntityId_entities_id_fk" 
    FOREIGN KEY ("sourceEntityId") REFERENCES "public"."entities"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "relationships" ADD CONSTRAINT "relationships_targetEntityId_entities_id_fk" 
    FOREIGN KEY ("targetEntityId") REFERENCES "public"."entities"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "relationships" ADD CONSTRAINT "relationships_agentId_agents_id_fk" 
    FOREIGN KEY ("agentId") REFERENCES "public"."agents"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "rooms" ADD CONSTRAINT "rooms_agentId_agents_id_fk" 
    FOREIGN KEY ("agentId") REFERENCES "public"."agents"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "rooms" ADD CONSTRAINT "rooms_worldId_worlds_id_fk" 
    FOREIGN KEY ("worldId") REFERENCES "public"."worlds"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "worlds" ADD CONSTRAINT "worlds_agentId_agents_id_fk" 
    FOREIGN KEY ("agentId") REFERENCES "public"."agents"("id") ON DELETE cascade ON UPDATE no action;

ALTER TABLE "message_servers" ADD CONSTRAINT "message_servers_agentId_agents_id_fk" 
    FOREIGN KEY ("agentId") REFERENCES "public"."agents"("id") ON DELETE cascade ON UPDATE no action;

-- Create Indexes for Performance
CREATE INDEX IF NOT EXISTS "idx_embedding_memory" ON "embeddings" USING btree ("memory_id");
CREATE INDEX IF NOT EXISTS "idx_memories_type_room" ON "memories" USING btree ("type","roomId");
CREATE INDEX IF NOT EXISTS "idx_participants_user" ON "participants" USING btree ("entityId");
CREATE INDEX IF NOT EXISTS "idx_participants_room" ON "participants" USING btree ("roomId");
CREATE INDEX IF NOT EXISTS "idx_memories_agent" ON "memories" USING btree ("agentId");
CREATE INDEX IF NOT EXISTS "idx_memories_room" ON "memories" USING btree ("roomId");
CREATE INDEX IF NOT EXISTS "idx_facts_agent" ON "facts" USING btree ("agentId");
CREATE INDEX IF NOT EXISTS "idx_facts_type" ON "facts" USING btree ("type");
CREATE INDEX IF NOT EXISTS "idx_memory_archive_agent" ON "memory_archive" USING btree ("agentId");
CREATE INDEX IF NOT EXISTS "idx_memory_archive_importance" ON "memory_archive" USING btree ("importance_score" DESC);
CREATE INDEX IF NOT EXISTS "idx_memory_archive_archived_at" ON "memory_archive" USING btree ("archived_at" DESC);
CREATE INDEX IF NOT EXISTS "idx_message_servers_agent" ON "message_servers" USING btree ("agentId");
CREATE INDEX IF NOT EXISTS "idx_message_servers_active" ON "message_servers" USING btree ("isActive");

-- Insert default data for autonomous agent
DO $$
DECLARE
    agent_uuid uuid;
    world_uuid uuid;
    room_uuid uuid;
    entity_uuid uuid;
    server_uuid uuid;
BEGIN
    -- Create default agent if none exists
    INSERT INTO agents (id, name, username, system, bio, settings, enabled)
    VALUES (
        gen_random_uuid(),
        'Autoliza',
        'autoliza',
        'You are Autoliza, an autonomous AI agent specialized in VTuber management and interaction.',
        '["Autonomous VTuber management agent", "Continuous learning capabilities", "Strategic prompting specialist"]'::jsonb,
        '{
            "AUTONOMOUS_LOOP_INTERVAL": "30000",
            "MEMORY_ARCHIVING_ENABLED": "true",
            "MEMORY_ACTIVE_LIMIT": "200",
            "MEMORY_ARCHIVE_HOURS": "48",
            "MEMORY_IMPORTANCE_THRESHOLD": "0.3"
        }'::jsonb,
        true
    ) ON CONFLICT (name) DO UPDATE SET
        system = EXCLUDED.system,
        bio = EXCLUDED.bio,
        settings = EXCLUDED.settings,
        "updatedAt" = now()
    RETURNING id INTO agent_uuid;

    -- Get the agent ID if it already existed
    IF agent_uuid IS NULL THEN
        SELECT id INTO agent_uuid FROM agents WHERE name = 'Autoliza' LIMIT 1;
    END IF;

    -- Create default entity for the agent
    INSERT INTO entities (id, "agentId", names, metadata)
    VALUES (
        agent_uuid, -- Use same UUID for simplicity
        agent_uuid,
        ARRAY['Autoliza', 'Autonomous Agent', 'VTuber Manager'],
        '{"type": "agent", "role": "autonomous_manager"}'::jsonb
    ) ON CONFLICT (id, "agentId") DO NOTHING;

    -- Create default world
    INSERT INTO worlds (id, "agentId", name, "serverId", metadata)
    VALUES (
        gen_random_uuid(),
        agent_uuid,
        'Autonomous World',
        'autonomous-server',
        '{"type": "autonomous", "purpose": "agent_operations"}'::jsonb
    ) ON CONFLICT DO NOTHING
    RETURNING id INTO world_uuid;

    -- Get the world ID if it already existed
    IF world_uuid IS NULL THEN
        SELECT id INTO world_uuid FROM worlds WHERE "agentId" = agent_uuid LIMIT 1;
    END IF;

    -- Create default room
    INSERT INTO rooms (id, "agentId", source, type, "serverId", "worldId", name, metadata)
    VALUES (
        gen_random_uuid(),
        agent_uuid,
        'autonomous',
        'agent_operations',
        'autonomous-server',
        world_uuid,
        'Autonomous Operations Room',
        '{"type": "autonomous", "purpose": "operations"}'::jsonb
    ) ON CONFLICT DO NOTHING
    RETURNING id INTO room_uuid;

    -- Create default message server entry
    INSERT INTO message_servers ("agentId", "serverId", "serverName", "serverType", "isActive", metadata)
    VALUES (
        agent_uuid,
        'autonomous-server',
        'Autonomous Server',
        'autonomous',
        true,
        '{"type": "autonomous", "purpose": "agent_operations"}'::jsonb
    ) ON CONFLICT ("agentId", "serverId") DO UPDATE SET
        "isActive" = true,
        "updatedAt" = now();

    -- Log successful initialization
    RAISE NOTICE '✅ ElizaOS Database Schema Initialized Successfully!';
    RAISE NOTICE '🤖 Agent: % (ID: %)', 'Autoliza', agent_uuid;
    RAISE NOTICE '🌍 World: % (ID: %)', 'Autonomous World', world_uuid;
    RAISE NOTICE '📋 Tables created: agents, memories, rooms, worlds, message_servers, facts, memory_archive';
    RAISE NOTICE '🔧 Database ready for autonomous agent operations!';

END $$;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO postgres; 