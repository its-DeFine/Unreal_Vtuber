# 🎥 OBS RTMP Audio Setup Guide for VTuber System

## 📋 **Quick Setup (Recommended)**

### **Method 1: Media Source (Primary)**
1. **Add Source in OBS:**
   - Click `+` in Sources panel
   - Select `Media Source`
   - Name: `VTuber Audio Stream`

2. **Configure Media Source:**
   ```
   Input: rtmp://localhost:1935/live/mystream
   Input Format: (leave blank)
   ☑ Restart when source becomes active
   ☑ Close file when inactive  
   Advanced → ☑ Hardware Decoding
   ```

3. **Audio Settings:**
   - Right-click source → `Advanced Audio Properties`
   - Set monitoring to `Monitor and Output`

### **Method 2: VLC Video Source (Alternative)**
1. **Add Source:**
   - Click `+` in Sources  
   - Select `VLC Video Source`
   - Name: `VTuber RTMP`

2. **Configure VLC Source:**
   ```
   Playlist:
   - Add: rtmp://localhost:1935/live/mystream
   ☑ Loop Playlist
   ☑ Restart playback when source becomes active
   ```

### **Method 3: Browser Source (HLS)**
1. **Add Source:**
   - Click `+` in Sources
   - Select `Browser Source`  
   - Name: `VTuber HLS Stream`

2. **Configure Browser:**
   ```
   URL: http://localhost:8080/live/mystream.m3u8
   Width: 1 (minimal)
   Height: 1 (minimal)
   ☑ Control audio via OBS
   ```

## 🔧 **Troubleshooting**

### **❌ No Audio Heard**
1. **Check RTMP Server:**
   ```bash
   docker logs nginx_rtmp --tail 20
   ```

2. **Verify Connection:**
   ```bash
   # Should show connection attempts
   curl -s http://localhost:8080/stat
   ```

3. **Test Direct Stream:**
   ```bash
   ffplay rtmp://localhost:1935/live/mystream
   ```

### **❌ Source Shows as Inactive**
1. **Verify containers are running:**
   ```bash
   docker ps | grep -E "(nginx|neurosync)"
   ```

2. **Check if VTuber is actually sending audio:**
   ```bash
   docker logs neurosync_s1 | grep -i "streaming\|rtmp\|audio"
   ```

### **❌ Audio Cuts Out**
- Increase `Buffer Size` in Media Source properties
- Try different `Network Buffering` values
- Check `Advanced Audio Properties` → `Sync Offset`

## 🎛️ **Advanced Configuration**

### **Audio Monitoring**
```
OBS Settings → Audio → Advanced:
- Monitoring Device: (your speakers/headphones)
```

### **Audio Mixer Settings**
```
Audio Mixer → VTuber Source → Gear Icon:
- Audio Monitoring: Monitor and Output
- Volume: Adjust as needed
```

### **Network Optimization**
```
OBS Settings → Advanced → Network:
- ☑ Enable network optimizations
- Bind to IP: (leave default)
```

## 🎯 **Testing Your Setup**

### **1. Run Test Script:**
```bash
./test_rtmp_audio.sh
```

### **2. Manual Test:**
```bash
# Start containers
docker-compose -f docker-compose.bridge.yml up nginx-rtmp neurosync -d

# Test VTuber response
curl -X POST http://localhost:5001/process_text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, testing audio streaming"}'
```

### **3. Monitor Logs:**
```bash
# VTuber logs
docker logs neurosync_s1 --tail 50 -f

# RTMP server logs  
docker logs nginx_rtmp --tail 20 -f
```

## 📊 **RTMP Stream Information**

| Setting | Value |
|---------|-------|
| **Protocol** | RTMP |
| **Host** | localhost |
| **Port** | 1935 |
| **Application** | live |
| **Stream Key** | mystream |
| **Full URL** | `rtmp://localhost:1935/live/mystream` |
| **HLS URL** | `http://localhost:8080/live/mystream.m3u8` |
| **Status Page** | `http://localhost:8080/stat` |

## 🔄 **Environment Variables**

You can customize these in your `.env` file:
```bash
AUDIO_MODE=rtmp
RTMP_HOST=nginx-rtmp
RTMP_PORT=1935  
RTMP_STREAM_NAME=mystream
OBS_HOST_IP=nginx-rtmp
```

## 🚨 **Common Issues & Solutions**

| Issue | Solution |
|-------|----------|
| **No audio in OBS** | Check source is set to "Monitor and Output" |
| **Stream disconnects** | Increase buffer size, check container health |
| **Delayed audio** | Reduce network buffering, check sync offset |
| **No connection** | Verify RTMP server is running on port 1935 |
| **Container crashes** | Check logs for errors, restart with `docker-compose up` |

---

🎯 **Need Help?** 
- Run `./test_rtmp_audio.sh` for automated testing
- Check logs with `docker logs nginx_rtmp` and `docker logs neurosync_s1`
- Verify containers with `docker ps` 