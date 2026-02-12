# How to Teach AI New Slang

## Overview
The bot uses two methods to understand slang:
1. **Slang Dictionary** - Fast preprocessing that replaces slang with standard forms
2. **Gemini AI Prompt** - AI learns patterns from examples in the prompt

## Method 1: Update Slang Dictionary (Recommended for Common Slang)

Edit `slang_dictionary.py` and add new entries to the dictionaries:

### Adding Time Slang
```python
TIME_SLANG = {
    # Your new slang here
    'kerakli_vaqt': 'bir soatdan keyin',  # Example: any needed time
    'нужное_время': 'через 1 час',        # Example Russian
}
```

### Adding Task Slang
```python
TASK_SLANG = {
    # Your new slang here
    'tel_qil': 'telefon qilish',          # Example: make a call
    'набери': 'позвонить',                # Example Russian
}
```

### Adding Abbreviations
```python
ABBREVIATIONS = {
    'др': 'день рождения',                # birthday
    'tug': 'tug\'ilgan kun',              # birthday in Uzbek
}
```

## Method 2: Update Gemini AI Prompt (For Complex Patterns)

Edit `gemini_parser.py` and add examples to the prompt:

```python
Time parsing rules (including slang & colloquialisms):
- "your_new_slang" = meaning/time
- "новый_сленг" = значение
```

## Examples of What You Can Add

### Uzbek Slang
- **Time**: "keyinchalik" (later), "tezlikda" (quickly), "darrov" (immediately)
- **Tasks**: "gaplash" (talk), "ko'rish" (see/meet), "qayt" (call back)

### Russian Slang  
- **Time**: "попозже" (later), "скоро" (soon), "мигом" (in a flash)
- **Tasks**: "позвони" (call), "напиши" (text), "зайди" (drop by)

### Regional Variations
- Add local dialects from different regions of Uzbekistan
- Add Russian-Uzbek mixed expressions commonly used

## Testing New Slang

1. Add the slang to `slang_dictionary.py`
2. Restart the bot
3. Send a voice message using the new slang
4. Check logs to see if it was normalized correctly

## Logs to Watch

The bot logs slang normalization:
```
INFO - After slang normalization: 'normalized text here'
```

This helps you verify if slang is being recognized.

## Tips

- **Start simple**: Add the most common slang first
- **Test thoroughly**: Send voice messages with new slang to verify
- **Update regularly**: As you discover new patterns, add them
- **Regional focus**: Prioritize slang used in Tashkent, Samarkand, etc.
- **Mixed languages**: Many users mix Uzbek and Russian - add those patterns

## Example Workflow

1. User says: "keyin Ali ga qo'ng'iroq qil"
2. Slang dictionary normalizes: "keyin" → "ikki soatdan keyin"
3. Parser understands: "Call Ali in 2 hours"
4. Reminder created successfully ✅

## Common Uzbek-Russian Mixed Slang

```python
# Users often mix languages
'позвони Aliya ga': 'Aliyaga telefon qil'
'напиши онага': 'onaga xabar yoz'
'встретиться бозорда': 'bozorda uchrashish'
```

Add these to `TASK_SLANG` dictionary for better recognition!
