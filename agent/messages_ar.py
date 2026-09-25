from datetime import datetime, timezone

MESSAGES = {
 'INSUFFICIENT_FUNDS':'الرصيد ما يكفي للمبلغ والعمولة. ما انخصم شي بهالمحاولة؛ زيد رصيدك أو قلل المبلغ.',
 'UNKNOWN_PAYEE':'ما لگينا المستلم بحسابك. ما انخصم شي؛ اختار اسم من جهات اتصالك.',
 'UNKNOWN_BILLER':'ما لگينا هالفاتورة بحسابك. ما انخصم شي؛ راجع رقم الحساب والمزوّد.',
 'UNKNOWN_USER':'الحساب مو موجود. ما انخصم شي؛ اختار حساب من القائمة.',
 'BILL_ALREADY_PAID':'هالفاتورة مدفوعة من قبل. ما انخصم شي مرة ثانية؛ راجع الحركات.',
 'AMOUNT_INVALID':'المبلغ مو صالح لهالطلب. ما انخصم شي؛ اكتب مبلغ صحيح بالدينار.',
 'LIMIT_EXCEEDED':'تجاوزت الحد اليومي. ما انخصم شي بهالمحاولة؛ قلل المبلغ أو جرّب باچر.',
 'BILLER_UNAVAILABLE':'المزوّد متوقف هسه. ما انخصم شي؛ جرّب من جديد بعدين.',
 'IDEMPOTENCY_CONFLICT':'هالطلب مرتبط بتفاصيل مختلفة. ما سوينا دفعة جديدة؛ راجع الحركات والطلب الأصلي.',
 'IDEMPOTENCY_REQUIRED':'رقم الطلب مفقود. ما انخصم شي؛ ارجع راجع الطلب من جديد.',
 'IN_PROGRESS':'طلبك قيد التحقق. بعد ما نعرف النتيجة؛ لا تعيد الطلب، نتابعه بنفس الرقم حتى ما ينخصم مرتين.',
 'STATUS_UNKNOWN':'بعدنا ما متأكدين من نتيجة الدفع، ودا نتحقق من الحالة. لا تعيد الطلب؛ نتابعه بنفس الرقم حتى ما ينخصم مرتين.',
 'DRAFT_EXPIRED':'انتهت مهلة التأكيد، وما نفّذنا هالطلب. راجع التفاصيل واطلب بطاقة جديدة.',
 'DRAFT_SUPERSEDED':'هالبطاقة تبدلت وما نفّذناها. راجع البطاقة الجديدة قبل التأكيد.',
 'DRAFT_CANCELLED':'هالطلب ملغي وما نفّذناه. اكتب طلب جديد إذا تريد.',
 'DRAFT_FORBIDDEN':'ما نكدر نأكد هالبطاقة من حسابك. ما نفّذنا طلب جديد؛ اختار حسابك وراجع البطاقة.',
 'DRAFT_TAMPERED':'تفاصيل البطاقة تغيرت، فوقفنا التأكيد. ما نفّذنا طلب جديد؛ راجع الحركات واطلب بطاقة جديدة.',
 'DRAFT_PENDING':'هالطلب بعده ينتظر تأكيدك، ما انخصم شي. راجع البطاقة واضغط أكّد.',
 'CANCELLED':'ألغينا الطلب، ما انخصم شي بهالطلب. تكدر تكتب طلب جديد.',
 'FORBIDDEN':'ما تكدر تفتح طلب تابع لحساب ثاني. ما نفّذنا طلب جديد؛ اختار حسابك.',
 'UNSUPPORTED':'هالطلب مو مدعوم. ما انخصم شي؛ أگدر أساعدك بتحويل أو دفع فاتورة.',
 'UNCLEAR':'الطلب مو واضح. ما انخصم شي؛ اكتب لمن وشكد تريد تدز.',
 'PARSER_UNAVAILABLE':'ما كدرت أفهم الطلب هسه. ما انخصم شي؛ جرّب تكتبه مرة ثانية.',
}


def message(result):
    if result.get('status')=='succeeded' and result.get('id'):
        timestamp=datetime.fromtimestamp(result['created_at'],timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        return (f"تم الدفع إلى {result.get('payee_name','الجهة المحددة')}: {result['amount_iqd']:,} د.ع، "
                f"العمولة {result['fee_iqd']:,} د.ع. رصيدك {result['balance_iqd']:,} د.ع. "
                f"رقم الوصل: {result['id']} — {timestamp}.")
    code=result.get('code','STATUS_UNKNOWN')
    if code=='INSUFFICIENT_FUNDS' and '|' in result.get('detail',''):
        needed,available=result['detail'].split('|')
        return f'ما تكدر تدفع: تحتاج {int(needed):,} د.ع ورصيدك {int(available):,} د.ع. ما انخصم شي؛ زيد رصيدك أو قلل المبلغ.'
    return MESSAGES.get(code,MESSAGES['STATUS_UNKNOWN'])
