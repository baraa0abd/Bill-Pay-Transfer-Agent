class SimulatedUser:
    def __init__(self,item):
        self.answers=iter(item.get('simulated_user_answers',[]))
        self.may_confirm=item['expected_outcome']=='EXECUTE_AFTER_CONFIRM'

    def answer(self,response):
        if response.get('ask_slot'): return next(self.answers,None)
        return None
