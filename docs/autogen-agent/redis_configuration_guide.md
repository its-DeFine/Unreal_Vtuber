# Redis Configuration Guide for SCB

## Recommended Redis Configuration

### 1. Enable Persistence in Docker Compose

```yaml
# docker-compose.neurobridge.yml
redis:
  image: redis:7-alpine
  container_name: neurobridge_redis
  command: >
    redis-server
    --appendonly yes
    --appendfsync everysec
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
  volumes:
    - redis_data:/data
  ports:
    - "6379:6379"
  networks:
    - agent_network

volumes:
  redis_data:
    driver: local
```

### 2. Redis Configuration Explained

#### Persistence Options
- `--appendonly yes`: Enable append-only file (AOF) persistence
- `--appendfsync everysec`: Sync to disk every second (balanced performance)

#### Memory Management
- `--maxmemory 256mb`: Limit Redis memory usage
- `--maxmemory-policy allkeys-lru`: Evict least recently used keys when full

### 3. Advanced Configuration for Production

Create `redis.conf`:
```conf
# Persistence
appendonly yes
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Memory
maxmemory 512mb
maxmemory-policy allkeys-lru

# Performance
tcp-backlog 511
timeout 300
tcp-keepalive 300

# Security
protected-mode yes
requirepass your_secure_password_here

# Logging
loglevel notice
logfile /data/redis.log

# Slow queries
slowlog-log-slower-than 10000
slowlog-max-len 128

# Client limits
maxclients 10000
```

### 4. Monitoring Redis Health

Add monitoring endpoint to your application:

```python
@app.get("/api/redis/health")
async def redis_health():
    """Check Redis health and memory usage"""
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL"))
        
        # Basic health check
        r.ping()
        
        # Memory info
        info = r.info("memory")
        
        return {
            "status": "healthy",
            "memory": {
                "used": info["used_memory_human"],
                "peak": info["used_memory_peak_human"],
                "fragmentation": info["mem_fragmentation_ratio"]
            },
            "keys": r.dbsize()
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503
```

### 5. Redis Cluster for High Availability

For production scale:

```yaml
# docker-compose.redis-cluster.yml
redis-master:
  image: redis:7-alpine
  command: redis-server --appendonly yes
  
redis-replica-1:
  image: redis:7-alpine
  command: redis-server --slaveof redis-master 6379
  
redis-replica-2:
  image: redis:7-alpine
  command: redis-server --slaveof redis-master 6379
  
redis-sentinel-1:
  image: redis:7-alpine
  command: redis-sentinel /etc/redis-sentinel/sentinel.conf
  volumes:
    - ./sentinel.conf:/etc/redis-sentinel/sentinel.conf
```

### 6. Best Practices

1. **Use TTL for all keys**
   ```python
   redis.setex("scb:state:12345", 3600, data)  # 1 hour TTL
   ```

2. **Implement key namespacing**
   ```
   scb:s1:display:latest
   scb:s2:analysis:latest
   scb:stimuli:active:{id}
   ```

3. **Monitor memory usage**
   - Set up alerts when memory > 80%
   - Implement automatic cleanup jobs

4. **Use Redis Streams for event sourcing**
   ```python
   # Better than pub/sub for guaranteed delivery
   redis.xadd("scb:events", {"action": "update", "data": json.dumps(state)})
   ```

### 7. Migration Path

#### Phase 1: Current + Persistence
- Add persistence configuration
- Monitor memory usage
- Implement TTL

#### Phase 2: Optimization
- Use Redis Streams instead of pub/sub
- Implement key expiration policies
- Add monitoring dashboards

#### Phase 3: Scale Out
- Redis Sentinel for HA
- Read replicas for S1 agents
- Consider Redis Enterprise

### 8. Emergency Procedures

#### If Redis runs out of memory:
```bash
# Check memory usage
redis-cli INFO memory

# Find large keys
redis-cli --bigkeys

# Flush old data (careful!)
redis-cli FLUSHDB

# Emergency cleanup script
redis-cli EVAL "
  local keys = redis.call('keys', 'scb:*')
  for i=1,#keys,5000 do
    redis.call('del', unpack(keys, i, math.min(i+4999, #keys)))
  end
  return #keys
" 0
```

## Summary

Redis remains the best choice for SCB because:
1. **Sub-millisecond latency** for S1 agents
2. **Simple and reliable** for current use case
3. **Can scale** with proper configuration
4. **Clear upgrade path** as system grows

The key is to:
- Enable persistence for reliability
- Use TTL to prevent memory bloat
- Monitor usage proactively
- Plan for future scale