import asyncio
import os

from t_tech.invest import AsyncClient
from t_tech.invest.schemas import AssetsRequest, InstrumentStatus, InstrumentType


import os

from t_tech.invest import Client


Share(figi='TCS00Y3XYV94', ticker='MDMG', class_code='TQBR', isin='RU000A108KL3', lot=1, currency='rub', klong=Quotation(units=0, nano=0), kshort=Quotation(units=0, nano=0), dlong=Quotation(units=0, nano=300000000), dshort=Quota
tion(units=0, nano=300000000), dlong_min=Quotation(units=0, nano=300000000), dshort_min=Quotation(units=0, nano=300000000), short_enabled_flag=True, name='Мать и дитя', exchange='moex_mrng_evng_e_wknd_dlr', ipo_date=datetime.dat
etime(2024, 5, 13, 0, 0, tzinfo=datetime.timezone.utc), issue_size=75125010, country_of_risk='RU', country_of_risk_name='Российская Федерация', sector='health_care', issue_size_plan=75125010, nominal=MoneyValue(currency='rub', u
nits=7, nano=168720000), trading_status=<SecurityTradingStatus.SECURITY_TRADING_STATUS_NORMAL_TRADING: 5>, otc_flag=False, buy_available_flag=True, sell_available_flag=True, div_yield_flag=True, share_type=<ShareType.SHARE_TYPE_
COMMON: 1>, min_price_increment=Quotation(units=0, nano=100000000), api_trade_available_flag=True, uid='0d53d29a-3794-41c6-ba72-556d46bacb46', real_exchange=<RealExchange.REAL_EXCHANGE_MOEX: 1>, position_uid='c4187467-5961-4413-
b3e6-3822cfeeed86', asset_uid='6321ea79-6930-45fc-9425-85c214259756', instrument_exchange=<InstrumentExchangeType.INSTRUMENT_EXCHANGE_UNSPECIFIED: 0>, required_tests=[], for_iis_flag=True, for_qual_investor_flag=False, weekend_f
lag=True, blocked_tca_flag=False, liquidity_flag=True, first_1min_candle_date=datetime.datetime(2020, 11, 9, 6, 59, tzinfo=datetime.timezone.utc), first_1day_candle_date=datetime.datetime(2020, 11, 9, 7, 0, tzinfo=datetime.timez
one.utc), brand=BrandData(logo_name='US55279C2008.png', logo_base_color='#952e6b', text_color='#ffffff'), dlong_client=Quotation(units=0, nano=300000000), dshort_client=Quotation(units=0, nano=300000000))



TOKEN = 't.YS2uyKoFJ_BjA2Jz2CLNsRrpEWL5e7ad4Mq48OKNUySiNbs2QrGhIcW4gkj4-MTl62oO1quiZK8GPLkd6OM7Dw'

async def main():
    async with AsyncClient(TOKEN) as client:
        method = getattr(client.instruments, 'shares')
        response = await method()  # Без аргументов

        for item in response.instruments:
            print(item)



asyncio.run(main())




# def find_indicatives():
#     """
#     Ищет индикативы (индексы, товары) по ключевым словам
#     """
#     found_items = []
#
#     with Client(TOKEN) as client:
#         request = IndicativesRequest()
#         indicatives = client.instruments.indicatives(request=request)
#
#         for instrument in indicatives.instruments:
#             name_lower = instrument.name.lower() if instrument.name else ""
#             ticker_lower = instrument.ticker.lower() if instrument.ticker else ""
#
#
#             found_items.append({
#                 "type": "indicative",
#                 "ticker": instrument.ticker,
#                 "name": instrument.name,
#                 "uid": instrument.uid,
#                 "figi": instrument.figi,
#                 "currency": instrument.currency,
#             })
#
#     return DataFrame(found_items).to_csv("indicatives.csv", index=False)
#
# find_indicatives()
# if __name__ == "__main__":
#     # Ищем индексы, золото, нефть
#     keywords = ["imoex", "rts", "gold", "xau", "brent", "oil", "brn"]
#
#     df = find_indicatives(keywords)
#
#     if df.empty:
#         print("\n❌ В индикативах ничего не найдено.")
#         print("Возможно, эти инструменты доступны только как фонды (ETF/БПИФ) или фьючерсы.")
#     else:
#         print("\n" + "=" * 100)
#         print("✅ НАЙДЕННЫЕ ИНДИКАТИВЫ:")
#         print("=" * 100)
#         print(df.to_string(index=False))
#
#         print("\n" + "=" * 100)
#         print("💡 ГОТОВЫЕ UID ДЛЯ ТВОЕГО ДЕМОНА:")
#         print("=" * 100)
#
#         for _, row in df.iterrows():
#             if 'IMOEX' in row['ticker'].upper() or 'MOEX' in row['name'].upper():
#                 print(f"📊 Индекс МосБиржи: uid='{row['uid']}'")
#             if 'GOLD' in row['name'].upper() or 'XAU' in row['ticker'].upper():
#                 print(f"🥇 Золото: uid='{row['uid']}'")
#             if 'BRENT' in row['name'].upper() or 'OIL' in row['name'].upper():
#                 print(f"🛢 Нефть Brent: uid='{row['uid']}'")
#
#         print("\n" + "=" * 100)
#         print("⚠️ ВАЖНО ПРО ИНДИКАТИВЫ:")
#         print("=" * 100)
#         print("1. Индикативы (индексы) часто отдают ТОЛЬКО текущую цену.")
#         print("2. Исторические свечи (candles) могут НЕ работать для indicatives.")
#         print("3. Для статистики и графиков лучше использовать БПИФы/ETF (TGLD, TMOS).")
#         print("4. Для нефти бери фьючерсы (futures) — у них есть полноценные свечи.")