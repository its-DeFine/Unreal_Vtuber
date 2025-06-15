# Troubleshooting Guide

## Autonomous S3 Container Issues

### Problem: Database Schema Mismatch Error

**Symptoms:**
- Container fails to start with errors like:
  ```
  error: column "agent_id" of relation "server_agents" does not exist
  error: column "server_id" of relation "server_agents" does not exist
  ```
- Container exits with database constraint violations
- Agent registration fails during startup

**Root Cause:**
The application code expects snake_case column names (`agent_id`, `server_id`) but the database table `server_agents` was created with camelCase columns (`agentId`, `serverId`).

**Solution:**
1. **Add missing snake_case columns:**
   ```sql
   ALTER TABLE server_agents ADD COLUMN agent_id uuid;
   ALTER TABLE server_agents ADD COLUMN server_id text;
   ```

2. **Populate the new columns with existing data:**
   ```sql
   UPDATE server_agents SET agent_id = "agentId", server_id = "serverId";
   ```

3. **Set constraints on new columns:**
   ```sql
   ALTER TABLE server_agents ALTER COLUMN agent_id SET NOT NULL;
   ALTER TABLE server_agents ALTER COLUMN server_id SET NOT NULL;
   ```

4. **Create synchronization trigger:**
   ```sql
   CREATE OR REPLACE FUNCTION sync_server_agents_columns()
   RETURNS TRIGGER AS $$
   BEGIN
       IF NEW.agent_id IS NOT NULL THEN NEW."agentId" = NEW.agent_id; END IF;
       IF NEW.server_id IS NOT NULL THEN NEW."serverId" = NEW.server_id; END IF;
       IF NEW."agentId" IS NOT NULL THEN NEW.agent_id = NEW."agentId"; END IF;
       IF NEW."serverId" IS NOT NULL THEN NEW.server_id = NEW."serverId"; END IF;
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER sync_server_agents_trigger
       BEFORE INSERT OR UPDATE ON server_agents
       FOR EACH ROW
       EXECUTE FUNCTION sync_server_agents_columns();
   ```

5. **Make serverType nullable temporarily (if needed):**
   ```sql
   ALTER TABLE server_agents ALTER COLUMN "serverType" DROP NOT NULL;
   ```

**Commands to fix:**
```bash
# Access the database
docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent

# Run the SQL commands above
```

**Verification:**
- Container should start successfully and show "Startup successful!" in logs
- Health check should pass: `curl http://localhost:3100/health`
- API should respond: `curl http://localhost:3100/api/agents`

---

## General Container Issues

### Container Won't Start
1. Check logs: `docker logs <container_name>`
2. Verify dependencies are running (PostgreSQL, Redis)
3. Check port conflicts
4. Verify environment variables are set correctly

### Database Connection Issues
1. Ensure PostgreSQL container is healthy
2. Check database credentials in environment variables
3. Verify database exists and has proper schema
4. Check network connectivity between containers

### Permission Errors
1. Check file ownership and permissions
2. Verify Docker user mappings
3. Check SELinux/AppArmor settings if applicable 