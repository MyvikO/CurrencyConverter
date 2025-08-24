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

    conversion_rates = {}

    # Запрос фиат валют
    try:
        url = f'https://v6.exchangerate-api.com/v6/{API_TOKEN_FIAT}/latest/{base_upper}'
        r = requests.get(url=url, timeout=5)
        if r.ok:
            rjson = r.json()
            conversion_rates = rjson.get("conversion_rates", {}) or {}
    except requests.RequestException:
        pass
    # Запрос криптовалют
    coin_ids = sorted({v["id"] for v in ASSETS.values() if "id" in v}) # ['bitcoin', 'ethereum', 'solana', 'the-open-network']

    headers = {"accept": "application/json", "x-cg-demo-api-key": API_TOKEN_CRYPTO}

    r1_json = {}

    try:
        if coin_ids:
            r1 = requests.get(
                f"{CRYPTO_URL}/simple/price",
                params={"ids": ",".join(coin_ids), "vs_currencies": base_lower},
                headers=headers, timeout=5
            )
            if r1.ok:
                r1_json = r1.json()
    except requests.RequestException:
        pass

    for symbol, values in ASSETS.items():
        price = None
        if "id" in values:
            data = r1_json.get(values["id"])
            if isinstance(data, dict):
                price = data.get(base_lower)

        if isinstance(price, (int, float)):
            conversion_rates[symbol] = float(price)

    # Если базовая валюта - криптовалюта: добираем её цену в фиатах (crypto -> fiat)
    if base_upper in ASSETS:
        base_asset = ASSETS.get(base_upper, {})
        base_id = base_asset.get("id")

        # Запрашиваем список поддерживаемых фиатных валют
        vs_supported = set()
        try:
            r_vs = requests.get(f"{CRYPTO_URL}/simple/supported_vs_currencies",
                                headers=headers, timeout=5)
            if r_vs.ok:
                r_vs_json = r_vs.json() or []
                if not isinstance(r_vs_json, list):
                    r_vs_json = []
                vs_supported = {s.lower() for s in r_vs_json if isinstance(s, str)}
        except requests.RequestException:
            pass

        # Фиаты, которые поддерживает CoinGecko
        fiat_targets = [code for code in ALL_CURRENCIES.keys() if code not in ASSETS]
        fiat_supported = [c for c in fiat_targets if c.lower() in vs_supported]

        if base_id and fiat_supported:
            try:
                r2 = requests.get(
                    f"{CRYPTO_URL}/simple/price",
                    params={"ids": base_id, "vs_currencies": ",".join([c.lower() for c in fiat_supported])},
                    headers=headers, timeout=5
                )
                if r2.ok:
                    r2_json = (r2.json() or {}).get(base_id, {})
                    for fiat_code in fiat_supported:
                        price_in_fiat = r2_json.get(fiat_code.lower())
                        if isinstance(price_in_fiat, (int, float)):
                            conversion_rates[fiat_code] = float(price_in_fiat)
            except requests.RequestException:
                pass
    base_flag = CURRENCY_FLAGS.get(base_upper, "")
    results = []
    # Добавление в results конвертаций
    if conversion_rates:
        for target_currency in ALL_CURRENCIES.keys():
            if target_currency == base_upper:
                continue
            target_flag = CURRENCY_FLAGS.get(target_currency, "")
            if target_currency in ASSETS:
                if target_currency in conversion_rates:
                    rate = float(conversion_rates[target_currency])
                    converted = round(amount / rate, 4)
                    results.append(f'{amount} {base_currency}{base_flag} = {converted} {target_currency}{target_flag}')
            else:
                if target_currency in conversion_rates:
                    rate = float(conversion_rates[target_currency])
                    converted = round(amount * rate, 2)
                    results.append(f'{amount} {base_currency}{base_flag} = {converted} {target_currency}{target_flag}')
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




