import pytest
from data.seed import load_seed
from agent.resolvers import resolve_contact,resolve_biller

@pytest.fixture
def seeded(engine):
    load_seed(engine)
    return engine

@pytest.mark.parametrize('query,status,ids', [('أحمد','many',{1,2,3}),('احمد','many',{1,2,3}),('احمد علي','one',{1}),('أَحْمَد علي','one',{1}),('احمد الموصلي','one',{2}),('أبو أحمد','one',{3}),('خالو','one',{8}),('سامر','none',set()),('', 'none',set()),('حسين','many',{4,5}),('حسن','many',{4,5}),('فاطمة','one',{9}),('عباس','one',{10}),('حيدر','one',{16}),('كاظم','one',{17}),('باسم','one',{18}),('سارة','one',{20}),('عدنان','one',{22}),('نبيل','one',{23}),('ضياء','one',{24})])
def test_contacts(seeded,query,status,ids):
    result=resolve_contact(seeded,1,query)
    assert result['status']==status
    assert ids <= {x['id'] for x in result['candidates']}

@pytest.mark.parametrize('query,ids', [('الكهرباء',{1,2}),('كهربا',{1,2}),('الوطنية',{1}),('المولدة',{2}),('مولده',{2}),('النت',{6}),('انترنت',{6}),('اشحن آسيا',{3}),('رصيد زين',{4}),('شحن كورك',{5}),('رصيد',{3,4,5}),('الماء',{7})])
def test_billers(seeded,query,ids):
    result=resolve_biller(seeded,1,query)
    assert {x['biller_id'] for x in result['candidates']}==ids
    assert result['status']==('one' if len(ids)==1 else 'many')
