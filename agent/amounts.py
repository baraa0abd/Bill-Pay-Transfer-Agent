import re
from dataclasses import dataclass, asdict
from .normalize import normalize

NUMBERS = {'واحد':1,'اثنين':2,'ثلاثه':3,'اربعه':4,'خمسه':5,'سته':6,'سبعه':7,'ثمانيه':8,'تسعه':9,
           'عشره':10,'عشرين':20,'عشرون':20,'ثلاثين':30,'ثلاثون':30,'اربعين':40,'اربعون':40,
           'خمسين':50,'خمسون':50,'ستين':60,'ستون':60,'سبعين':70,'سبعون':70,'ثمانين':80,'ثمانون':80,
           'تسعين':90,'تسعون':90,'ميه':100,'ميت':100,'مئه':100,'مائه':100,'مئتين':200}
SPECIAL = {'الف':1000,'الفين':2000,'مليون':1000000,'مليونين':2000000,'ربع مليون':250000,
           'نص مليون':500000,'نصف مليون':500000,'مليون ونص':1500000}


@dataclass
class Amount:
    value: int | None
    confidence: int
    ambiguous: bool
    reason: str

    def model_dump(self):
        return asdict(self)


def parse_amount(text):
    s = normalize(text or '').strip()
    explicit = bool(re.search(r'\s*(دينار|د\.ع|iqd)$', s))
    s = re.sub(r'\s*(دينار|د\.ع|iqd)$', '', s).strip()
    if s in SPECIAL:
        return Amount(SPECIAL[s], 100, False, 'explicit scale')
    m = re.fullmatch(r'(.+?)\s+(الف|الاف|مليون)', s)
    scale = 1
    if m:
        s = m[1]; scale = 1000 if m[2] in ['الف','الاف'] else 1000000
    value = NUMBERS.get(s)
    if re.fullmatch(r'(?:[1-9]\d*|0|[1-9]\d{0,2}(?:[,٬]\d{3})+)', s):
        value = int(s.replace(',', '').replace('٬', ''))
    if value is None:
        return Amount(None, 0, True, 'unknown or malformed expression')
    value *= scale
    if value <= 0 or value > 1000000000:
        return Amount(None, 0, True, 'amount out of range')
    ambiguous = scale == 1 and not explicit and value < 1000
    return Amount(value, 30 if ambiguous else 100, ambiguous, 'unit required' if ambiguous else 'explicit amount')


def amount_words(value):
    reverse = {1:'واحد',2:'اثنان',3:'ثلاثة',4:'أربعة',5:'خمسة',10:'عشرة',15:'خمسة عشر',20:'عشرون',25:'خمسة وعشرون',30:'ثلاثون',35:'خمسة وثلاثون',40:'أربعون',50:'خمسون',100:'مئة',250:'مئتان وخمسون',500:'خمسمئة'}
    if value == 1000000: return 'مليون دينار'
    if value == 2000000: return 'مليونان دينار'
    if value == 2000: return 'ألفان دينار'
    if value == 1000: return 'ألف دينار'
    if value % 1000 == 0 and value // 1000 in reverse:
        return reverse[value // 1000] + ' ألف دينار'
    if value in reverse: return reverse[value] + ' دينار'
    ones=['صفر','واحد','اثنان','ثلاثة','أربعة','خمسة','ستة','سبعة','ثمانية','تسعة']
    tens=['','عشرة','عشرون','ثلاثون','أربعون','خمسون','ستون','سبعون','ثمانون','تسعون']
    def words(n):
        if n < 10: return ones[n]
        if n == 10: return 'عشرة'
        if n == 11: return 'أحد عشر'
        if n == 12: return 'اثنا عشر'
        if n < 20: return ones[n-10]+' عشر'
        if n < 100: return (ones[n%10]+' و' if n%10 else '')+tens[n//10]
        if n < 1000:
            hundreds=['','مئة','مئتان','ثلاثمئة','أربعمئة','خمسمئة','ستمئة','سبعمئة','ثمانمئة','تسعمئة']
            return hundreds[n//100]+(' و'+words(n%100) if n%100 else '')
        for scale,label in [(1000000,'مليون'),(1000,'ألف')]:
            if n >= scale:
                return words(n//scale)+' '+label+(' و'+words(n%scale) if n%scale else '')
    return words(value)+' دينار'
