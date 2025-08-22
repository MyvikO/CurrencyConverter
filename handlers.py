import re, requests
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import *

router = Router()

# Функция для получения числа и валюты из текста пользователя
def extract_amount_and_currency(text: str) -> tuple[float, str] | None:
    pattern = '(\\d+(?:[.,]\\d+)?)\\s*([\\$€₽₸₴]|[A-Za-zА-Яа-яЁёŁł]+(?:\\s+[A-Za-zА-Яа-яЁёŁł]+){0,2}|[\U0001F1E6-\U0001F1FF]{2})'
    matches = re.search(pattern, text)
    if not matches:
        return None
    try:
        amount_str = matches.group(1)
        amount = float(amount_str.replace(",", "."))
        currency = str(matches.group(2)).strip().upper()
        for code, symbols in ALL_CURRENCIES.items():
            if currency in [s.upper() for s in symbols]:
                return amount, code
    except ValueError:
        return None
# Функция для процесса конвертирования
def currency_converter(amount: float, base_currency: str):
    base_upper = base_currency.upper()
    base_lower = base_currency.lower()
    if not (0 < amount <= 1_000_000_000):
        return None
    # Запрос фиат валют
    conversion_rates_fiat = {}
    try:
        url = f'https://v6.exchangerate-api.com/v6/{API_TOKEN_FIAT}/latest/{base_upper}'
        r = requests.get(url=url, timeout=5)
        if r.ok:
            rjson = r.json()
            conversion_rates_fiat = rjson.get("conversion_rates", {}) or {}
    except requests.RequestException:
        pass
    # Запрос криптовалют
    conversion_rates_crypto = {}
    try:
        r1 = requests.get(f"{CRYPTO_URL}/simple/price",
                          params={"ids": ",".join(coins), "vs_currencies": base_lower},
                          headers={
                              "accept": "application/json",
                              "x-cg-demo-api-key": API_TOKEN_CRYPTO
                                    },
                          timeout=5)
        if r1.ok:
            r1_json = r1.json()
            for c in coins:
                price = (r1_json.get(c) or {}).get(base_lower)
                if isinstance(price, (int, float)):
                    conversion_rates_crypto[c] = float(price)

        r2 = requests.get(f"{CRYPTO_URL}/simple/token_price/ethereum",
                          params={"contract_addresses": ",".join(token_contracts),
                                  "vs_currencies": base_lower},
                          headers={
                              "accept": "application/json",
                              "x-cg-demo-api-key": API_TOKEN_CRYPTO
                                    },
                          timeout=5)
        if r2.ok:
            r2_json = r2.json()
            for co in token_contracts:
                price = (r2_json.get(co) or {}).get(base_lower)
                if isinstance(price, (int, float)):
                    conversion_rates_crypto[co] = float(price)
    except requests.RequestException:
        pass

    base_flag = CURRENCY_FLAGS.get(base_upper, "")
    results = []
    # Добавление в results конвертации фиата
    if conversion_rates_fiat:
        for target_currency in ALL_CURRENCIES.keys():
            if target_currency == base_upper:
                continue
            if target_currency in conversion_rates_fiat:
                rate = conversion_rates_fiat[target_currency]
                target_flag = CURRENCY_FLAGS.get(target_currency)
                converted = round(amount * float(rate), 2)
                results.append(f'{amount} {base_currency}{base_flag} = {converted} {target_currency}{target_flag}')
            else:
                continue
    # Добавление в results конвертации криптовалют
    if conversion_rates_crypto:
        for c in coins:
            price = conversion_rates_crypto.get(c)
            if price > 0:
                symbol_id = coins_symbol.get(c)
                converted = round(amount / price, 4)
                results.append(f'{amount} {base_upper}{base_flag} = {converted} {symbol_id}💰')
        for co in token_contracts:
            price = conversion_rates_crypto.get(co)
            if price > 0:
                symbol_id = coins_symbol.get(co)
                converted = round(amount / price, 4)
                results.append(f'{amount} {base_upper}{base_flag} = {converted} {symbol_id}💰')
    return results or None
# Хендлер на команду /start
@router.message(CommandStart())
async def start_command(message: Message):
    await message.answer('Примеры команд боту: \n25.25 rub\n25,25рублей\n25 usd\n25 byn\n25 руб\n25 тенге\n1 btc\n 1 биткоин')
# Хендлер на команду /list, выведение всех доступных валют
@router.message(Command('list'))
async def list_currencies(message: Message):
    currencies = []
    for curr in ALL_CURRENCIES.keys():
        target_flag = CURRENCY_FLAGS.get(curr)
        currencies.append(f'{curr}{target_flag}')
    await message.answer(f'Список поддерживаемых валют: \n{'\n'.join(currencies)}')
# Основной хендлер, который реагирует на текст пользователя
@router.message(F.text)
async def summa(message: Message):
    extracted_data = extract_amount_and_currency(message.text)
    if extracted_data:
        amount = extracted_data[0]
        base_currency = extracted_data[1]
        conversion_results = currency_converter(amount, base_currency)
        if conversion_results:
            await message.answer('\n'.join(conversion_results))
        else:
            await message.answer('Ошибка, повторите запрос')
    else:
        return




