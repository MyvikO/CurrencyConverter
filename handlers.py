import re, requests, json, time, random
import keyboards as kb
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from config import CRYPTO_URL,FIAT_URL, API_TOKEN_CRYPTO, API_TOKEN_FIAT
from currencies import CRYPTO_CURRENCIES, ALL_CURRENCIES, CURRENCY_FLAGS
from redis_client import get_redis

router = Router()

redis_client = get_redis()

# Функция для получения числа и валюты из текста пользователя
def parse_amount_and_currency(text: str) -> tuple[float, str] | None:
    pattern = '(\\d+(?:[.,]\\d+)?)\\s*([\\$€₽₸₴]|[A-Za-zА-Яа-яЁёŁł]+(?:\\s+[A-Za-zА-Яа-яЁёŁł]+){0,2}|[\U0001F1E6-\U0001F1FF]{2})'
    matches = re.search(pattern, text)
    if not matches:
        return None
    try:
        amount_str = matches.group(1)
        amount = float(amount_str.replace(",", "."))
        currency = str(matches.group(2)).strip().upper().replace('Ё', "Е")
        for code, symbols in ALL_CURRENCIES.items():
            if currency in [s.upper() for s in symbols]:
                return amount, code
    except ValueError:
        return None

# Функция для форматирования в приличный вид amount
def format_amount(amount, digits: int):
    s = format(amount, f",.{digits}f")
    return s

# Функция для получения ttl, необходимое функции get_request_fiat
def compute_ttl_from_response(data: dict, default_ttl=1920, max_ttl=43200) -> int:
    now = int(time.time())
    nxt = data.get("time_next_update_unix")
    if isinstance(nxt, (int, float)) and nxt > now:
        ttl = int(nxt - now)
        ttl = max(60, min(ttl, max_ttl))
    else:
        ttl = default_ttl
    ttl += random.randint(0, 30)  # джиттер
    return ttl


#Функция кэширования запросов фиата
def get_fiat_rates_cached(url, base_upper):
    key = f"fiat:latest:{base_upper}"
    r = redis_client.get(key)
    if r:
        return json.loads(r)
    r = requests.get(url=url, timeout=5)
    r.raise_for_status()
    rjson = r.json() or []
    ttl = compute_ttl_from_response(rjson)
    redis_client.setex(key, ttl, json.dumps(rjson))
    return rjson

# Функция кэширования доступных фиатных валют
def get_supported_vs_currencies_cached(url, headers, timeout):
    key = f"fiat:supported_vs_currencies"
    r = redis_client.get(key)
    if r:
        return json.loads(r)
    r = requests.get(url=url, headers=headers, timeout=timeout)
    r.raise_for_status()
    rjson = r.json() or []
    if not isinstance(rjson, list):
        rjson = []
    redis_client.setex(key, 3600, json.dumps(rjson))
    return rjson

# Функция для процесса конвертирования
def currency_converter(amount: float, base_currency: str) -> list:
    format_base_amount = format_amount(amount, digits=1)
    base_upper = base_currency.upper()
    base_lower = base_currency.lower()
    if not (0 < amount <= 1_000_000_000):
        raise

    conversion_rates = {}

    # Запрос фиат валют
    try:
        url = f'{FIAT_URL}/{API_TOKEN_FIAT}/latest/{base_upper}'
        request_fiat = get_fiat_rates_cached(url, base_upper)
        if request_fiat:
            conversion_rates = request_fiat.get("conversion_rates", {}) or {}
    except requests.RequestException:
        pass

    # Запрос криптовалют
    coin_ids = sorted({v["id"] for v in CRYPTO_CURRENCIES.values() if "id" in v}) # ['bitcoin', 'ethereum', 'solana', 'the-open-network']

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

    for symbol, values in CRYPTO_CURRENCIES.items():
        price = None
        if "id" in values:
            data = r1_json.get(values["id"])
            if isinstance(data, dict):
                price = data.get(base_lower)

        if isinstance(price, (int, float)):
            conversion_rates[symbol] = float(price)

    # Если базовая валюта - криптовалюта: добираем её цену в фиатах
    if base_upper in CRYPTO_CURRENCIES:
        base_asset = CRYPTO_CURRENCIES.get(base_upper, {})
        base_id = base_asset.get("id")

        # Запрашиваем список поддерживаемых фиатных валют
        vs_supported = set()
        try:
            url = f"{CRYPTO_URL}/simple/supported_vs_currencies"
            request_supported_fiat = get_supported_vs_currencies_cached(url=url, headers=headers, timeout=5)
            if request_supported_fiat:
                vs_supported = {s.lower() for s in request_supported_fiat if isinstance(s, str)}
        except requests.RequestException:
            pass

        # Фиаты, которые поддерживает CoinGecko
        fiat_targets = [code for code in ALL_CURRENCIES.keys() if code not in CRYPTO_CURRENCIES]
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
            if target_currency in CRYPTO_CURRENCIES:
                if target_currency in conversion_rates:
                    rate = float(conversion_rates[target_currency])
                    converted = round(amount / rate, 4)
                    format_converted = format_amount(converted, digits=4)
                    results.append(f'{format_base_amount} {base_currency}{base_flag} = {format_converted} {target_currency}{target_flag}')
            else:
                if target_currency in conversion_rates:
                    rate = float(conversion_rates[target_currency])
                    converted = round(amount * rate, 2)
                    format_converted = format_amount(converted, digits=2)
                    results.append(f'{format_base_amount} {base_currency}{base_flag} = {format_converted} {target_currency}{target_flag}')
    return results or None
# Хендлер на команду /start
@router.message(CommandStart())
async def start_command(message: Message):
    await message.answer('👋 Привет! Я CurrencyConverterBot — конвертирую суммы из одной валюты в другие.\n\n'
                         'Примеры ввода:\n'
                         ' • 25.25 rub\n'
                         ' • 25,25рублей\n'
                         ' • 25 usd\n'
                         ' • 25 byn\n'
                         ' • 25 руб\n'
                         ' • 25 тенге\n'
                         ' • 1 btc\n'
                         ' • 1 биткоин')
# Хендлер на команду /list, выведение всех доступных валют
@router.message(Command('list'))
async def list_currencies(message: Message):
    currencies = []
    for curr in ALL_CURRENCIES.keys():
        target_flag = CURRENCY_FLAGS.get(curr, "")
        currencies.append(f' • {curr}{target_flag}')
    await message.answer(f'Список поддерживаемых валют: \n{'\n'.join(currencies)}')
# Основной хендлер, который реагирует на текст пользователя
@router.message(F.text)
async def handle_conversion_request(message: Message):
    extracted = parse_amount_and_currency(message.text)
    if extracted:
        amount, base_currency = extracted
        conversion_results = currency_converter(amount, base_currency)
        if conversion_results:
            await message.answer('\n'.join(conversion_results), reply_markup=kb.main(amount, base_currency))
        else:
            await message.answer('Ошибка, повторите запрос')
    else:
        return

@router.callback_query(F.data.startswith('update:'))
async def handle_update_rates_callback(callback: CallbackQuery):
    old_text = callback.message.text
    try:
        _, amount_str, base_currency = callback.data.split(":")
        amount = float(amount_str.replace(",", ""))
    except Exception:
        return await callback.answer("Некорректные данные кнопки")

    conversion_results = currency_converter(amount, base_currency)
    if not conversion_results:
        return await callback.answer("Ошибка при получении курсов")

    new_text = '\n'.join(conversion_results)
    if new_text == old_text:
        return await callback.answer("Курсы не изменились 👍")

    return await callback.message.edit_text(new_text, reply_markup=kb.main(amount, base_currency))




