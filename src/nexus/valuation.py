"""Local, explicitly supplied financial scenarios. Never infer statements from OHLC."""
import math
import statistics

from .learning import digest


def number(data,key,minimum=None):
    value=data.get(key)
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('قيمة مالية مفقودة أو غير صالحة: '+key)
    if minimum is not None and value<minimum:raise ValueError('قيمة أقل من الحد المسموح: '+key)
    return float(value)

def evaluate(data):
    if not isinstance(data,dict):raise ValueError('المدخلات المالية يجب أن تكون كائنًا')  # noqa: TRY004 -- Keep ValueError validation contract consumed by API handlers and existing risk tests.
    model=data.get('model');currency=data.get('currency')
    if not isinstance(currency,str) or len(currency)!=3 or not currency.isascii() or not currency.isalpha():raise ValueError('يلزم رمز عملة واضح من ثلاثة أحرف لاتينية')
    as_of=number(data,'as_of',0);published=number(data,'published_at',0)
    if published>as_of:raise ValueError('بيانات مالية منشورة بعد وقت التقييم')
    if not isinstance(data.get('source'),str) or not data['source'].strip():raise ValueError('يلزم توثيق مصدر المدخلات المالية')
    if not isinstance(data.get('asset'),str) or not data['asset'].strip():raise ValueError('يلزم اسم الأصل المقيم')
    out={'model':model,'asset':data['asset'],'currency':currency.upper(),'as_of':as_of,
         'published_at':published,'source':data['source'],'data_kind':'USER_SUPPLIED_FINANCIAL_SCENARIO',
         'execution_authority':False,'input_fingerprint':digest(data),
         'limitations':['assumptions_sensitive','not_independently_verified','underlying_not_cfd_contract_value']}
    def shares():
        count=number(data,'shares',0)
        if count==0:raise ValueError('عدد الأسهم يجب أن يكون موجبًا')
        return count
    def rate():
        value=number(data,'discount_rate')
        if value<=-1:raise ValueError('معدل الخصم يجب أن يتجاوز سالب واحد')
        return value
    def flows():
        values=data.get('cashflows')
        if not isinstance(values,list) or not 1<=len(values)<=50:raise ValueError('يلزم من تدفق واحد إلى خمسين تدفقًا دوريًا')
        result=[]
        for value in values:
            result.append(number({'value':value},'value'))
        return result
    if model in ('pv','dcf'):
        discount=rate();cash=flows()
        try:pv=sum(x/(1+discount)**(i+1) for i,x in enumerate(cash))
        except (OverflowError,ZeroDivisionError):raise ValueError('افتراض خصم غير قابل للحساب') from None
        out.update(present_value=pv,periods=len(cash))
        if model=='dcf':
            growth=number(data,'terminal_growth')
            if growth<=-1 or discount<=growth:raise ValueError('يلزم معدل خصم أعلى من النمو النهائي، والنمو أعلى من سالب واحد')
            terminal=cash[-1]*(1+growth)/(discount-growth)
            try:terminal_pv=terminal/(1+discount)**len(cash)
            except (OverflowError,ZeroDivisionError):raise ValueError('افتراض خصم نهائي غير قابل للحساب') from None
            enterprise=pv+terminal_pv
            debt=number(data,'debt',0);cash_balance=number(data,'cash',0)
            out.update(enterprise_value=enterprise,equity_value=enterprise-debt+cash_balance,
                       value_per_share=(enterprise-debt+cash_balance)/shares(),terminal_pv=terminal_pv,
                       terminal_fraction=terminal_pv/enterprise if enterprise else None,
                       cashflow_basis='FCFF_AFTER_OPERATING_TAX_AND_REINVESTMENT')
    elif model=='ddm':
        discount=rate();growth=number(data,'dividend_growth');dividend=number(data,'dividend_next',0)
        if growth<=-1 or discount<=growth:raise ValueError('خصم الأرباح يتطلب معدل عائد أعلى من نمو الأرباح')
        out.update(value_per_share=dividend/(discount-growth),dividend_basis='NEXT_PERIOD_DIVIDEND_PER_SHARE')
    elif model=='nav':
        assets=number(data,'assets_fair_value',0);liabilities=number(data,'liabilities',0)
        contingent=number(data,'contingent_liabilities',0)
        equity=assets-liabilities-contingent
        out.update(equity_value=equity,value_per_share=equity/shares())
    elif model=='multiples':
        basis=data.get('basis')
        if basis not in ('pe','ev_ebitda','ev_sales'):raise ValueError('نوع مضاعف غير معتمد')
        peers=data.get('peer_multiples')
        if not isinstance(peers,list) or len(peers)<3 or len(peers)>100:raise ValueError('يلزم ثلاثة مضاعفات مقارنة على الأقل، وبحد أقصى مئة')
        peers=[number({'value':x},'value',0) for x in peers]
        if min(peers)<=0:raise ValueError('مضاعفات المقارنة يجب أن تكون موجبة')
        metric=number(data,'metric',0)
        if metric<=0:raise ValueError('المقياس المالي يجب أن يكون موجبًا لهذا النموذج')
        median=statistics.median(peers);value=median*metric
        out.update(peer_count=len(peers),median_multiple=median,comparison_basis=basis)
        if basis=='pe':out['value_per_share']=value
        else:
            equity=value-number(data,'debt',0)+number(data,'cash',0)
            out.update(enterprise_value=value,equity_value=equity,value_per_share=equity/shares())
    elif model=='bond':
        par=number(data,'par',0);coupon=number(data,'coupon_rate',0);yield_rate=number(data,'yield_rate')
        frequency=data.get('payments_per_year');periods=data.get('periods')
        if type(frequency) is not int or frequency not in (1,2,4,12) or type(periods) is not int or not 1<=periods<=600:
            raise ValueError('عدد دفعات أو فترات السند غير صالح')
        if par<=0 or yield_rate/frequency<=-1:raise ValueError('قيمة اسمية أو عائد سند غير صالح')
        per=yield_rate/frequency
        try:out['clean_price_at_coupon_boundary']=sum((par*coupon/frequency)/(1+per)**i for i in range(1,periods+1))+par/(1+per)**periods
        except (OverflowError,ZeroDivisionError):raise ValueError('افتراض عائد سند غير قابل للحساب') from None
        out['limitations'].append('coupon_boundary_only_no_accrued_interest_or_day_count')
    else:raise ValueError('نموذج تقييم غير معتمد')
    if any(isinstance(v,float) and not math.isfinite(v) for v in out.values()):raise ValueError('نتيجة مالية غير محدودة')
    return out
