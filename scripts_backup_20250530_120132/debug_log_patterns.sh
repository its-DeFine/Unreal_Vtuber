#!/bin/bash

# Debug script to analyze log patterns

echo "🔍 ANALYZING LOG PATTERNS"
echo "========================"

LOG_FILE="logs/comprehensive_monitoring/session_20250528_172539/raw/autonomous_raw.log"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "❌ Log file not found: $LOG_FILE"
    exit 1
fi

echo ""
echo "📊 Log file size: $(du -h "$LOG_FILE" | cut -f1)"
echo "📊 Total lines: $(wc -l < "$LOG_FILE")"
echo ""

echo "🔍 Searching for common patterns..."
echo ""

# Check for AutonomousService patterns
echo "1. AutonomousService patterns:"
grep -m 5 "AutonomousService" "$LOG_FILE" 2>/dev/null | head -5 || echo "   No AutonomousService patterns found"
echo ""

# Check for iteration patterns
echo "2. Iteration patterns:"
grep -m 5 -i "iteration" "$LOG_FILE" 2>/dev/null | head -5 || echo "   No iteration patterns found"
echo ""

# Check for sendToVTuber patterns
echo "3. sendToVTuber patterns:"
grep -m 5 "sendToVTuber" "$LOG_FILE" 2>/dev/null | head -5 || echo "   No sendToVTuber patterns found"
echo ""

# Check for VTUBER patterns
echo "4. VTUBER patterns:"
grep -m 5 "VTUBER" "$LOG_FILE" 2>/dev/null | head -5 || echo "   No VTUBER patterns found"
echo ""

# Check for action patterns
echo "5. Action patterns:"
grep -m 5 -i "action" "$LOG_FILE" 2>/dev/null | head -5 || echo "   No action patterns found"
echo ""

# Check for INFO/DEBUG log levels
echo "6. Log level patterns:"
grep -m 5 "INFO" "$LOG_FILE" 2>/dev/null | head -2 || echo "   No INFO patterns found"
grep -m 5 "DEBUG" "$LOG_FILE" 2>/dev/null | head -2 || echo "   No DEBUG patterns found"
echo ""

# Check timestamp format
echo "7. Timestamp patterns:"
head -10 "$LOG_FILE" | grep -oE '\[[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\]' | head -3 || echo "   No standard timestamp patterns found"
echo ""

# Check for any patterns with emojis
echo "8. Emoji patterns:"
grep -m 5 -E "🔄|📤|✅|🎯|🧠|📝|🎤|😊" "$LOG_FILE" 2>/dev/null | head -5 || echo "   No emoji patterns found"
echo ""

# Sample first 20 lines
echo "9. Sample of first 20 lines:"
echo "============================"
head -20 "$LOG_FILE" 2>/dev/null || echo "   Could not read file"
echo ""

# Sample last 20 lines
echo "10. Sample of last 20 lines:"
echo "============================="
tail -20 "$LOG_FILE" 2>/dev/null || echo "   Could not read file" 