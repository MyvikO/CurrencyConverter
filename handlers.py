import asyncio
from functools import partial
from aiogram import F , Router
from aiogram.filters import CommandStart,Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from currency_converter import CurrencyConverter
from CurrencyConverterBot import keyboards as kb


router = Router()
c = CurrencyConverter()

class AmountMoney(StatesGroup):
    choosing_amount_money = State()
    choosing_currency = State()

CURRENCIES = {
    'USD': ('USD/Доллар🇺🇸', 'USD'),
    'EUR': ('EUR/Евро🇪🇺', 'EUR'),
    'JPY': ('JPY/Японская иена🇯🇵', 'JPY'),
    'CZK': ('CZK/Чешская крона🇨🇿', 'CZK'),
    'DKK': ('DKK/Датская крона🇩🇰', 'DKK'),
    'GBP': ('GBP/Фунт стерлингов🇬🇧', 'GBP'),
    'CAD': ('CAD/Канадский доллар🇨🇦', 'CAD'),
    'CNY': ('CNY/Китайский юань🇨🇳', 'CNY'),
    'PHP': ('PHP/Филиппинское песо🇵🇭', 'PHP'),
    'MXN': ('MXN/Мексиканский песо🇲🇽', 'MXN'),
    'INR': ('INR/Индийская рупия🇮🇳', 'INR'),
    'TRY': ('TRY/Турецкая лира🇹🇷', 'TRY'),
}
@router.message(CommandStart())
async def start_command(message: Message):
    await message.answer(text=f'Привет, {message.from_user.first_name}! Это конвертер актуальных курсов самых популярных валют мира, предоставляемых Европейским центральным банком.💸\n\n'
                              'Обновление курсов валют происходит ежедневно.💲')
    await asyncio.sleep(1)
    await message.reply(text='Отправьте сумму, которую нужно перевести в другую валюту.💵 \n(Без лишних символов)')

@router.message(Command('list'))
async def currencies_lists(message: Message):
    all_currencies = [currency_title for _, (currency_title, _) in CURRENCIES.items()]
    await message.answer(f'Список поддерживаемых валют: \n\n{'\n'.join(all_currencies)}')

@router.message(F.text)
async def summa(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.reply(text='Число должно быть больше нуля❌. Отправьте сумму')
            return
        if amount > 1_000_000_000:
            await message.reply(text='Сумма слишком большая❌. Отправьте сумму до 1 миллиарда')
            return

        await state.update_data(amount=amount)
        await message.reply(
            text='Выберите валюту своей суммы💱',
            reply_markup=kb.main
        )
        await state.set_state(AmountMoney.choosing_currency)
    except ValueError:
        await message.reply(text='Неверный формат❌. Отправьте сумму')


async def convert_and_show(callback: CallbackQuery, state: FSMContext, base_currency: str):
    user_data = await state.get_data()
    amount = user_data.get('amount')
    await callback.answer('')
    await asyncio.sleep(1)
    try:
        results = []
        for currency_code, (currency_name, _) in CURRENCIES.items():
            if currency_code != base_currency:
                converted_amount = c.convert(
                    amount=amount,
                    currency=base_currency,
                    new_currency=currency_code)
                results.append(f"{round(converted_amount, 2)}      {currency_name}")

        await callback.message.edit_text(
            f'Результат конвертации {amount} {base_currency} :\n\n' + '\n\n'.join(results)
        )
        await asyncio.sleep(1.5)
        await callback.message.answer('Отправьте сумму:')
    except Exception as e:
        await callback.message.edit_text(f'Произошла ошибка: {str(e)}')
        await callback.message.answer('Отправьте сумму:')
    finally:
        await state.clear()

for currency_code in CURRENCIES:
    handler = partial(convert_and_show, base_currency=currency_code)
    router.callback_query(
        AmountMoney.choosing_currency,
        F.data == currency_code)(handler)
