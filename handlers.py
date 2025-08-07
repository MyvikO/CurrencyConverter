import asyncio, re, requests, json
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from config import API_TOKEN

router = Router()

CURRENCIES = {
    "USD": ["$", "USD", "доллар", "долларов", "бакс","баксов", "юзд", "🇺🇸"],
    "EUR": ["€", "EUR", "евро", "🇪🇺"],
    "BYN": ["Br", "BYN", "бун", "бел рублей", "🇧🇾"],
    "RUB": ["₽", "RUB", "руб", "рублей", "рубль", "🇷🇺"],
    "KZT": ["₸", "KZT", "тенге", "🇰🇿"],
    "PLN": ["zł", "PLN", "злотых", "🇵🇱"],
    "UAH": ["₴", "UAH", "гривна", "гривен", "🇺🇦"]
}

CURRENCY_FLAGS = {
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "BYN": "🇧🇾",
    "RUB": "🇷🇺",
    "KZT": "🇰🇿",
    "PLN": "🇵🇱",
    "UAH": "🇺🇦"
}
# Функция для получения числа и валюты из текста пользователя
def extract_amount_and_currency(text: str) -> tuple[float, str] | None:
    pattern = r'(\d+[.]\d+|\d+)\s*([a-zA-Zа-яА-Я]+)'
    matches = re.findall(pattern, text)
    if not matches:
        return None
    try:
        amount = float(matches[0][0])
        currency = str(matches[0][1]).strip().upper()
        for code, symbols in CURRENCIES.items():
            if currency in [s.upper() for s in symbols]:
                return amount, code
    except ValueError:
        return None
# Функция для процесса конвертирования
def currency_converter(amount: float, base_currency: str):
    url = f'https://v6.exchangerate-api.com/v6/{API_TOKEN}/latest/{base_currency}'
    try:
        r = requests.get(url=url)
        if r.ok:
            rjson = r.json()
            conversion_rates = rjson["conversion_rates"]
            target_currencies = list(CURRENCIES.keys())
            base_flag = CURRENCY_FLAGS.get(base_currency)
            results = []
        else:
            return None
        if not amount > 1000000000 and amount != 0:
            for target_currency in target_currencies:
                if target_currency == base_currency:
                    continue
                if target_currency in conversion_rates:
                    target_flag = CURRENCY_FLAGS.get(target_currency)
                    operation = amount * conversion_rates[target_currency]
                    results.append(f'{amount} {base_currency}{base_flag} = {round(operation, 2)} {target_currency}{target_flag}')
                else:
                    return None
        else:
            return None
        if results:
            return results
        else:
            return None
    except ValueError:
        return None
# Хендлер на команду /start
@router.message(CommandStart())
async def start_command(message: Message):
    await message.answer('Примеры команд боту: \n25.25 rub\n25 usd\n25 byn\n25 руб\n25 тенге')
# Хендлер на команду /list, выведение всех доступных валют
@router.message(Command('list'))
async def list_currencies(message: Message):
    currencies = []
    for curr in CURRENCIES.keys():
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
            await message.answer('Число слишком большое или равно нулю')
    else:
        return




