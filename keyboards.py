from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🇺🇸USD/США ', callback_data='USD'), InlineKeyboardButton(text='🇪🇺EUR/Еврозона', callback_data='EUR'), InlineKeyboardButton(text='🇯🇵JPY/Япония', callback_data='JPY')],
    [InlineKeyboardButton(text='🇨🇿CZK/Чехия', callback_data='CZK'), InlineKeyboardButton(text='🇩🇰DKK/Дания', callback_data='DKK'), InlineKeyboardButton(text='🇬🇧GBP/Великобритания', callback_data='GBP')],
    [InlineKeyboardButton(text='🇹🇷TRY/Турция', callback_data='TRY'), InlineKeyboardButton(text='🇨🇦CAD/Канада', callback_data='CAD'), InlineKeyboardButton(text='🇨🇳CNY/Китай', callback_data='CNY')],
    [InlineKeyboardButton(text='🇵🇭PHP/Филиппины', callback_data='PHP'), InlineKeyboardButton(text='🇲🇽MXN/Мексика', callback_data='MXN'), InlineKeyboardButton(text='🇮🇳INR/Индия', callback_data='INR')]
])