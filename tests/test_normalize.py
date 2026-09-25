import pytest
from agent.normalize import normalize

@pytest.mark.parametrize('source,expected', [('أ','ا'),('إ','ا'),('آ','ا'),('ٱ','ا'),('ى','ي'),('ة','ه'),('ؤ','و'),('ئ','ي')]+list(zip('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹','01234567890123456789'))+[('  علي  حسن  ','علي حسن'),('أَحْمَد','احمد'),('عـلي','علي'),('ع\u200dلي','علي'),('ع\u202eلي','علي'),('ع\u2066لي','علي'),('ع\u0670لي','علي'),('ﻻ','لا'),('AHMAD','ahmad'),('\tعلي\nحسن','علي حسن')])
def test_normalize(source,expected):
    assert normalize(source)==expected
    assert normalize(normalize(source))==expected
