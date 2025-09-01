from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main(amount: float, base_currency: str) -> InlineKeyboardMarkup:
    data = f"update:{amount}:{base_currency}"
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить курсы", callback_data=data)
    builder.adjust(1)
    return builder.as_markup()
