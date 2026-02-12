# Gemini AI Mode Configuration

## Two AI Modes Available

### 1. **Hybrid Mode (Default)** - Cost-Effective ✅
```env
ALWAYS_USE_GEMINI=false
```

**How it works:**
- Tries fast regex patterns first (FREE, instant)
- Uses Gemini AI only when regex fails (~10-20% of messages)
- Best for production with many users

**Advantages:**
- 💰 Lower cost (only pays for difficult cases)
- ⚡ Faster for common phrases
- ✅ Still handles complex cases with AI

**Use case:** Production bot with 100+ users

---

### 2. **Always AI Mode** - Maximum Understanding 🤖
```env
ALWAYS_USE_GEMINI=true
```

**How it works:**
- Uses Gemini AI for EVERY voice message
- Regex is only used if Gemini fails (rare)
- Shows "🤖 AI analyzing..." for all messages

**Advantages:**
- 🎯 Best accuracy for complex/ambiguous phrases
- 🌐 Better mixed language understanding (Uzbek + Russian)
- 🧠 Learns from slang and context better
- 💬 More natural language understanding

**Disadvantages:**
- 💸 Higher cost (Gemini API call for every message)
- ⏱️ Slightly slower response time

**Use case:** Personal bot, testing, or when accuracy > cost

---

## Cost Comparison

Assuming 1000 messages per day:

| Mode | Gemini Calls | Estimated Cost* |
|------|-------------|----------------|
| Hybrid (default) | ~150/day | $0.15/day |
| Always AI | ~1000/day | $1.00/day |

*Based on Gemini Pro pricing (~$0.001 per request)

---

## How to Switch Modes

### Enable Always AI Mode:
1. Edit `.env` file
2. Change: `ALWAYS_USE_GEMINI=true`
3. Restart bot

### Return to Hybrid Mode:
1. Edit `.env` file  
2. Change: `ALWAYS_USE_GEMINI=false`
3. Restart bot

---

## When to Use Each Mode

### Use **Hybrid Mode** (default) if:
- You have many users (100+)
- Cost is a concern
- Most messages use standard phrases
- You're in production

### Use **Always AI Mode** if:
- You have few users (<50)
- Accuracy is critical
- Users speak very informally/mixed languages
- Testing new slang/patterns
- Personal/family bot

---

## Performance Examples

### Hybrid Mode:
```
"bir soatdan keyin" → Regex ⚡ (instant, free)
"ertaga soat 3 da" → Regex ⚡ (instant, free)
"keyinchalik tushlikda" → Gemini 🤖 (2s, $0.001)
```

### Always AI Mode:
```
"bir soatdan keyin" → Gemini 🤖 (2s, $0.001)
"ertaga soat 3 da" → Gemini 🤖 (2s, $0.001)
"keyinchalik tushlikda" → Gemini 🤖 (2s, $0.001)
```

---

## Monitoring Usage

Check bot logs to see which mode is being used:

**Hybrid Mode:**
```
INFO - Parsed relative time: task='...' (regex)
INFO - Regex parsing failed, trying Gemini AI as fallback...
INFO - Gemini successfully parsed: ...
```

**Always AI Mode:**
```
INFO - Using Gemini AI for parsing (ALWAYS_USE_GEMINI=true)
INFO - Gemini parsed: ...
```

---

## Recommendation

**Start with Hybrid Mode** (default). Only switch to Always AI if you notice:
- Too many parsing failures
- Users complaining about understanding
- Heavy use of informal/slang speech
- Mixed language conversations

You can always switch back and forth as needed!
