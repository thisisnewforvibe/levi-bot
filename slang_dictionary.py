"""
Slang and colloquialism dictionary for Uzbek and Russian languages.
This file can be easily updated with new slang terms as users discover them.
"""

# Time expressions (slang → standard form)
TIME_SLANG = {
    # Uzbek slang
    'keyin': 'ikki soatdan keyin',  # later
    'hoziroq': '5 minutdan keyin',  # right now
    'tezda': '15 minutdan keyin',   # soon/quickly
    'tez': '15 minutdan keyin',     # fast
    'biroz keyin': '30 minutdan keyin',  # a bit later
    'kechqurun': 'bugun soat 18 da',  # in the evening
    'oqshom': 'bugun soat 18 da',     # evening
    'ertalab': 'ertaga soat 8 da',    # in the morning
    'tongda': 'ertaga soat 8 da',     # at dawn
    'tushlikda': 'bugun soat 13 da',  # at lunch
    'peshindan keyin': 'bugun soat 14 da',  # after lunch
    'kechasi': 'bugun soat 22 da',    # at night
    'tungi': 'bugun soat 23 da',      # night time
    'ertangi kun': 'ertaga',          # tomorrow
    'shu kun': 'bugun',               # today
    
    # Russian slang
    'попозже': 'через 2 часа',        # later
    'позже': 'через 2 часа',          # later
    'сейчас': 'через 5 минут',        # now
    'щас': 'через 5 минут',           # now (very informal)
    'быстро': 'через 15 минут',       # quickly
    'немного попозже': 'через 30 минут',  # a bit later
    'вечером': 'сегодня в 18:00',     # in the evening
    'утром': 'завтра в 8:00',         # in the morning
    'днем': 'сегодня в 14:00',        # in the afternoon
    'ночью': 'сегодня в 22:00',       # at night
    'через часик': 'через 1 час',     # in about an hour
    'через полчасика': 'через 30 минут',  # in about half hour
}

# Task/action slang (informal → formal)
TASK_SLANG = {
    # Uzbek slang
    'qo\'ng\'iroq': 'telefon qilish',   # call
    'zvonok': 'telefon qilish',         # call (Russian loanword)
    'xabar': 'xabar yuborish',          # send message
    'yoz': 'xabar yozish',              # write/message
    'chiq': 'chiqish',                  # go out
    'bor': 'borish',                    # go
    'uchrash': 'uchrashish',            # meet
    'ye': 'ovqat yeyish',               # eat
    'uxla': 'uxlash',                   # sleep
    'o\'qi': 'o\'qish',                 # read/study
    'ishlash': 'ishga borish',          # work/go to work
    
    # Russian slang
    'звони': 'позвонить',               # call
    'позвони': 'позвонить',             # call
    'напиши': 'написать сообщение',     # write/message
    'выйди': 'выйти',                   # go out
    'встреться': 'встретиться',         # meet
    'покушай': 'поесть',                # eat
    'поспи': 'поспать',                 # sleep
    'почитай': 'почитать',              # read
}

# Common abbreviations and shortcuts
ABBREVIATIONS = {
    # Uzbek
    'tel': 'telefon',
    'msg': 'xabar',
    'ish': 'ishga borish',
    
    # Russian  
    'тел': 'телефон',
    'смс': 'сообщение',
    'др': 'день рождения',
}

# Colloquial time periods
TIME_PERIODS = {
    # Uzbek
    'haftada': '7 kundan keyin',        # in a week
    'oyda': '30 kundan keyin',          # in a month
    'yakshanba': 'yakshanba kuni',      # Sunday
    
    # Russian
    'на неделе': 'через 7 дней',        # in a week
    'через неделю': 'через 7 дней',     # in a week
    'в воскресенье': 'в воскресенье',   # on Sunday
}


def normalize_slang(text: str) -> str:
    """
    Normalize slang expressions to standard forms.
    
    Args:
        text: Raw text with potential slang
        
    Returns:
        Normalized text with slang replaced by standard forms
    """
    normalized = text.lower()
    
    # Replace time slang
    for slang, standard in TIME_SLANG.items():
        normalized = normalized.replace(slang, standard)
    
    # Replace task slang
    for slang, standard in TASK_SLANG.items():
        normalized = normalized.replace(slang, standard)
    
    # Replace abbreviations
    for abbrev, full in ABBREVIATIONS.items():
        normalized = normalized.replace(abbrev, full)
    
    return normalized


def get_slang_examples() -> str:
    """
    Generate examples of slang usage for AI training.
    
    Returns:
        Formatted string with slang examples
    """
    examples = []
    
    examples.append("# Time Slang Examples:")
    for slang, standard in list(TIME_SLANG.items())[:5]:
        examples.append(f'  "{slang}" → {standard}')
    
    examples.append("\n# Task Slang Examples:")
    for slang, standard in list(TASK_SLANG.items())[:5]:
        examples.append(f'  "{slang}" → {standard}')
    
    return '\n'.join(examples)
