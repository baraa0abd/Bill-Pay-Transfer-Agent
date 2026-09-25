import re
import unicodedata

_TRANSLATE = str.maketrans('أإآٱىةؤئ٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', 'اااايهوي01234567890123456789')


def normalize(text):
    text = unicodedata.normalize('NFKC', text).translate(_TRANSLATE)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
    text = re.sub('[\u064b-\u0652\u0670\u0640]', '', text)
    return ' '.join(text.lower().split())
