# -*- coding: utf-8 -*-
"""
Telegram-бот для автоматизации операционных процессов в небольшой сети точек

Версия: 2.1  
Автор: Петрухина А.Д.  
Дата: 2025-11-25  

Описание:
- Автоматический сбор геолокации при начале смены
- Учёт посещаемости и опозданий через интеграцию с Google Sheets
- Генерация финансовых ведомостей (PNG) из табличных данных
- Расписание напоминаний (начало/окончание смены, уборки, контроль сроков годности)
- Поддержка замен, обменов сменами, динамическое управление сотрудниками

Стек:
- Python 3.10+, aiogram 2.x, apscheduler, gspread_pandas, pandas, matplotlib
- Google Sheets API (чтение/запись), SQLite (FSM, кэширование)
- Telegram Bot API + Mini App (не включён в этот файл)
"""

import asyncio
import json
import logging
import math
import datetime
from functools import wraps
from io import BytesIO
from typing import Optional, Dict, Any, Union
import os
import calendar
from dotenv import load_dotenv

load_dotenv()

#from aiogram.contrib.fsm_storage.memory import MemoryStorage

import pandas as pd
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputFile,
    WebAppInfo,
)
from aiogram.utils import executor
from aiogram.utils.exceptions import BadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gspread_pandas import Spread
from gspread_pandas.conf import get_config, get_creds

# Локальные модули (SQLite-интеграция)
from database import (
    init_db, employee_verification, add_log_pref, edit_point, get_time_send, get_locations_by_date,
    clear_locations_by_date, get_id, get_state_form, get_work_username, get_username,
    get_admin, db_message, edit_message, edit_location_messages, edit_sent_messages, get_message_id, get_location_messages, get_sent_messages,
    end_shift, edit_shift, add_control_of_delay, changes_in_grafic, change_grafic, get_grafic_by_date, get_point, get_all_work_username, edit_location,
    get_today_workers, get_control_of_delay, get_gen_reminder, start_shift, get_shift_status,
    get_tg_id_by_lottery_number, get_lottery_participant, mark_lottery_winner, update_lottery_claimed
)

import redis
from aiogram.dispatcher.storage import BaseStorage

# === Настройка логгирования ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(TOKEN)

class RedisStorage(BaseStorage):
    def __init__(self, host='redis', port=6379, db=0, password=None, prefix='fsm'):
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        self.prefix = prefix

    def _get_key(self, chat: int, user: int, key: str) -> str:
        return f"{self.prefix}:{key}:{chat}:{user}"

    @staticmethod
    def check_address(chat: Union[str, int, None], user: Union[str, int, None]) -> (int, int):
        chat = int(chat) if chat else 0
        user = int(user) if user else 0
        return chat, user

    @staticmethod
    def resolve_state(state) -> Optional[str]:
        if state is None:
            return None
        return state.name if hasattr(state, 'name') else str(state)

    async def set_state(self, *, chat=None, user=None, state=None):
        chat, user = self.check_address(chat, user)
        key = self._get_key(chat, user, 'state')
        r = redis.Redis(connection_pool=self.pool)
        if state is None:
            r.delete(key)
        else:
            r.set(key, self.resolve_state(state))

    async def get_state(self, *, chat=None, user=None, default=None):
        chat, user = self.check_address(chat, user)
        key = self._get_key(chat, user, 'state')
        r = redis.Redis(connection_pool=self.pool)
        value = r.get(key)
        return value if value is not None else default

    async def set_data(self, *, chat=None, user=None, data=None):
        chat, user = self.check_address(chat, user)
        key = self._get_key(chat, user, 'data')
        r = redis.Redis(connection_pool=self.pool)
        r.set(key, json.dumps(data or {}))

    async def get_data(self, *, chat=None, user=None, default=None):
        chat, user = self.check_address(chat, user)
        key = self._get_key(chat, user, 'data')
        r = redis.Redis(connection_pool=self.pool)
        value = r.get(key)
        if value is not None:
            try:
                return json.loads(value)
            except:
                return {}
        return default or {}

    async def update_data(self, *, chat=None, user=None, data=None, **kwargs):
        current = await self.get_data(chat=chat, user=user)
        current.update(data or {})
        current.update(kwargs)
        await self.set_data(chat=chat, user=user, data=current)

    async def reset_state(self, *, chat=None, user=None, with_ :bool = True):
        await self.set_state(chat=chat, user=user, state=None)
        if with_:
            await self.set_data(chat=chat, user=user, data={})

    async def close(self):
        pass

    async def wait_closed(self):
        pass

storage = RedisStorage(host="amvera-ang1983-run-mybot", port=6379, db=0)
dp = Dispatcher(bot, storage=storage)

dp.middleware.setup(LoggingMiddleware())

admin_id = 1630556732
admin_id_1 = 708179577
admin_id_2 = 501871781

keyboard1 = InlineKeyboardMarkup(row_width=1)
keyboard1.add(
    InlineKeyboardButton(text='Начать смену', web_app=WebAppInfo(url='https://frontend-loyalty-app.vercel.app')),
    InlineKeyboardButton(text='Задать вопрос', callback_data='question'),
    InlineKeyboardButton(text='Кто сегодня на смене?', callback_data='who_work'),
    InlineKeyboardButton(text='Начать смену ПОМОЩНИКИ/СМЕНЩИКИ', web_app=WebAppInfo(url='https://frontend-loyalty-app.vercel.app')),
    InlineKeyboardButton(text='Уведомить о замене', callback_data='notification')
)

keyboard_admin = InlineKeyboardMarkup(row_width=2)
keyboard_admin.add(
    InlineKeyboardButton(text='Начать смену', web_app=WebAppInfo(url='https://frontend-loyalty-app.vercel.app')),
    InlineKeyboardButton(text='Задать вопрос', callback_data='question'),
    InlineKeyboardButton(text='Кто сегодня на смене?', callback_data='who_work'),
    InlineKeyboardButton(text='Начать смену ПОМОЩНИКИ/СМЕНЩИКИ', web_app=WebAppInfo(url='https://frontend-loyalty-app.vercel.app')),
    InlineKeyboardButton(text='Уведомить о замене', callback_data='notification'),
    InlineKeyboardButton(text='Табели ЗП', callback_data='payroll_sheets'),
    InlineKeyboardButton(text='Список сотрудников', callback_data='worker_list'),
    InlineKeyboardButton(text='Геолокации за сегодня', callback_data='worker_locations'),
    InlineKeyboardButton(text='Результаты лотереи', callback_data='lottery_results')
)

keyboard_allow = InlineKeyboardMarkup(row_width=1)
keyboard_allow.add(
    InlineKeyboardButton(text='Получить карту', web_app=WebAppInfo(url='https://frontend-loyalty-app.vercel.app'))
)

keyboard_start_work = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard_start_work.add(
    KeyboardButton('Отправить локацию', request_location= True)
)

keyboard_start_work_change = InlineKeyboardMarkup(row_width=1)
keyboard_start_work_change.add(
    InlineKeyboardButton(text='Помощник', callback_data='change:helper'),
    InlineKeyboardButton(text='Сменщик', callback_data='change:changer'),
    InlineKeyboardButton(text='Назад в главное меню', callback_data='back')
)

keyboard_point = InlineKeyboardMarkup(row_width=4)


keyboard_point_change = InlineKeyboardMarkup(row_width=4)


keyboard_notification = InlineKeyboardMarkup(row_width=1)
keyboard_notification.add(
    InlineKeyboardButton(text='Я заменяю', callback_data='not:i'),
    InlineKeyboardButton(text='Меня заменяют', callback_data='not:me'),
    InlineKeyboardButton(text='Обмен точками', callback_data='not:ch'),
    InlineKeyboardButton(text='Назад в главное меню', callback_data='back')
)

keyboard_agree = InlineKeyboardMarkup(row_width=1)
keyboard_agree.add(
    InlineKeyboardButton(text='Верно', callback_data='notific:agree'),
    InlineKeyboardButton(text='Неверно', callback_data='notific:disagree'),
    InlineKeyboardButton(text='Назад в главное меню', callback_data='back')
)

clear_locations = InlineKeyboardMarkup()
clear_locations.add(
    InlineKeyboardButton(text='Ознакомлен, очистить данные', callback_data='clear'),
    InlineKeyboardButton(text='Назад в главное меню', callback_data='back')
)

admin = InlineKeyboardMarkup()
admin.add(
    InlineKeyboardButton(text='Администратор', callback_data='title:admin'),
    InlineKeyboardButton(text='Сотрудник', callback_data='title:user')
)

keyboard_back = InlineKeyboardMarkup()
keyboard_back.add(
    InlineKeyboardButton(text='Назад в главное меню', callback_data='back')
)

keyboard_ok = InlineKeyboardMarkup()
keyboard_ok.add(
    InlineKeyboardButton(text='Оки', callback_data='OK')
)

kb_gen = InlineKeyboardMarkup()
kb_gen.add(
    InlineKeyboardButton(text='Заполнить отчет', url='https://docs.google.com/forms/d/e/1FAIpQLScZ0SBbxKKNIh790XmCooS8XH8LKZPXb_az0EwpfBaIN9qhPQ/viewform'),
    InlineKeyboardButton(text='Оки', callback_data='OK')
)

kb_end = InlineKeyboardMarkup()
kb_end.add(
    InlineKeyboardButton(text='Итоги выручки', url='https://docs.google.com/forms/d/e/1FAIpQLSfnSUBGERqG9M7A78V12ajW_v-QDFgdPx390YsiuP_mNCLV5Q/viewform'),
    InlineKeyboardButton(text='Стоп лист', web_app=WebAppInfo(url='https://t.me/Zakupka_Teiku_bot?profile')),
    InlineKeyboardButton(text='Оки', callback_data='OK')
)

kb_chek = InlineKeyboardMarkup()
kb_chek.add(
    InlineKeyboardButton(text='Чек лист', web_app=WebAppInfo(url='https://t.me/Zakupka_Teiku_bot?profile')),
    InlineKeyboardButton(text='Оки', callback_data='OK')
)

secret = get_config(
    conf_dir= '/app',
    file_name='exalted-altar-452115-i9-ed1bf8b8c83f.json'
    )

creds = get_creds(config=secret)

with open('config.json', 'r', encoding='utf-8') as f:
    CATEGORIES = json.load(f)['categories']

ITEMS_PER_PAGE = 5
CATEGORY_LIST = list(CATEGORIES.keys())

class AccessDenied(Exception):
    pass

class Form(StatesGroup):
    get_location_st = State()
    notification_st = State()
    notification_name_st = State()
    verification = State()
    work_name_user = State()
    add_user_st = State()
    del_user_st = State()
    update_user_st = State()
    ask_question = State()
    lottery = State()

locations = {

}

cached_data = {
    'df_money': None,
    'df_4': None,
    'last_update': None
}

gen_points = {
    0: 'Протереть пыль на товарных стеллажах\nПротереть окна и двери от брызг\nПротереть ростовую фигурку', 
    3: 'Разобраться в тумбах\nПомыть холодильник',
    4: 'Протереть пыль с рабочих полок и барной стойки\nПротереть труднодоступные места на полу\nПротереть кофемашину под стаканами и снаружи\nПротереть стойку под кофемашиной',
    5: 'Протереть всю плитку в зоне посетителей\nПротереть пыль в труднодоступных местах\nПроверить наличие ценников и доставить их прни необходимости',
    6: 'Помыть органайзер для приборов и емкости для продуктов\nРазобрать темпер\nПомыть блендер\nПротереть ледогенератор внутри'
}

async def update_cached_data():
    global df_4, df_money, cached_data
    try:
        df_4_spread = Spread(spread='1GQQcMzWIUsvyKoqQRKG3ZV67s2KK-B2m3N3Ru84Md5M', config=secret, sheet='Вафли')
        df_4 = df_4_spread.sheet_to_df()
        cached_data['df_4'] = df_4.copy()
    except Exception as e:
        await bot.send_message(admin_id, f'[ОШИБКА] Не удалось обновить данные из таблиц: {e}')
    
async def get_girl_name(key):
    date = (datetime.date.today()).strftime('%Y-%m-%d')
    try:
        workers = await get_today_workers(date)

        worker = workers[key]

        chat_id = await get_id(worker)
        return await get_username(chat_id)
    except (KeyError, TypeError):
        return ''


def dataframe_to_image(df: pd.DataFrame) -> BytesIO:
    max_width = sum(df.astype(str).map(len).max()) + len(df.columns)
    fig_width = min(max_width / 5, 12)
    fig_height = len(df) * 0.6 

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('tight')
    ax.axis('off')

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc='center',
        loc='center'
    )

    max_widths = []
    for j, col in enumerate(df.columns):
        max_content_length = max(
            df[col].astype(str).map(len).max(),
            len(str(col))
        )
        max_widths.append(max_content_length)

    total_width = sum(max_widths)
    if total_width > 0:
        col_widths = [w / total_width for w in max_widths]
    else:
        col_widths = [1 / len(df.columns)] * len(df.columns)

    table.auto_set_column_width(list(range(len(df.columns))))
    for j, width in enumerate(col_widths):
        table.auto_set_column_width(j)
        for i in range(len(df) + 1):
            cell = table[(i, j)]
            cell.set_width(width)

    table.set_fontsize(9)
    table.scale(1, 2) 

    for (i, j), cell in table.get_celld().items():
        if i == 0:
            cell.set_text_props(weight='bold', color='black')
            cell.set_facecolor('#d5d5d5')
        else:
            cell.set_facecolor('#f8f9fa')

    plt.tight_layout(pad=0) 
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    plt.close(fig)

    return buf

def tables(name: str):
    df_name = df_money[df_money['Имя'] == name].copy().reset_index(drop=True)
    sum_value = sum(int(elem) for elem in df_name['Сколько перевести'])
    new_row = pd.DataFrame([{'Дата':'','Имя':'','Точка':'','Выручка':'','Взяли из кассы':'','Ставка':'','Процент':'','ЗП':'','Штраф': 'ИТОГО', 'Сколько перевести': sum_value, 'Комментарии':''}])
    df_name = pd.concat([df_name, new_row], ignore_index=True)
    return dataframe_to_image(df_name)

def get_category_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    for i, cat_name in enumerate(CATEGORY_LIST):
        kb.add(InlineKeyboardButton(cat_name, callback_data=f'cat:{i}'))
    kb.add(
            InlineKeyboardButton(text='Назад в главное меню', callback_data='back')
        )
    return kb

def get_subcategories_paginated(category_index: int, page: int = 0):
    cat_name = CATEGORY_LIST[category_index]
    category = CATEGORIES[cat_name]

    if cat_name == 'Штрафы':
        return None, False, False
    if cat_name == 'Ссылки':
        return None, False, False

    subcats = list(category['subcategories'].keys())
    total_pages = math.ceil(len(subcats) / ITEMS_PER_PAGE)
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_subcats = subcats[start:end]

 
    kb = InlineKeyboardMarkup(row_width=2)
    subcats = list(category['subcategories'].keys())

    for idx, subcat in enumerate(page_subcats, start=start):
        kb.add(InlineKeyboardButton(subcat, callback_data=f'sec:{category_index}:{idx}'))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton('Назад', callback_data=f'cat_page:{category_index}:{page-1}'))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton('Далее', callback_data=f'cat_page:{category_index}:{page+1}'))

    kb.row(*nav_buttons)
    kb.add(
        InlineKeyboardButton('К категориям', callback_data='back_to_categories'),
        InlineKeyboardButton('Назад в главное меню', callback_data='back')
    )
    return kb, page > 0, page < total_pages - 1

def check_employee_exists(location_key):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                date = (datetime.date.today() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
                employees = await get_today_workers(date)
                employee = employees[location_key]
                if pd.isna(employee) or await employee_verification(await get_id(employee)) == False:
                    return
                return await func(*args, **kwargs)
            except KeyError:
                return
        return wrapper
    return decorator

async def check_access(user_id):
        if await employee_verification(user_id) == True:
            return
        else:
            await bot.send_message(user_id, 'Доступ заблокирован, можете отправить заявку администратору', reply_markup=keyboard_allow)
            raise AccessDenied()

@dp.errors_handler(exception=AccessDenied)
async def access_denied_handler(update, error):
    return True

@dp.message_handler(commands= ['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if await employee_verification(user_id) == True:
        if await get_admin(user_id) in ['admin', 'boss']:
            await message.reply(f'Привет {await get_username(user_id)}, я буду помогать тебе следить за опозданиями сотрудников ;)\nА так же могу ответить на вопросы из разных категорий по правилам Teiku!', reply_markup=keyboard_admin)
        else:
            await message.reply(f'Привет {await get_username(user_id)}, я твой бот помощник в империи Teiku!\nЧем могу помочь?', reply_markup=keyboard1)
    else: 
        await message.reply('Привет! На связи команда сети кофеен Тейку, это наш бот с системой лояльности, скорее открывай приложение и получи свою карту лояльности', reply_markup=keyboard_allow)

@dp.callback_query_handler(lambda c: c.data.startswith('lottery_results'), state="*")
async def change_worker(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.message.edit_text(
        'Введите номера победителей лотереи через запятую\n\n'
        'Пример: 12345678, 87654321, 11223344'
    )
    await Form.lottery.set()

@dp.message_handler(state=Form.lottery)
async def location(message: types.Message, state: FSMContext):
    await check_access(message.from_user.id)

    numbers_text = message.text.strip()

    lottery_numbers = [num.strip() for num in numbers_text.split(',') if num.strip()]
    
    if not lottery_numbers:
        await message.answer(
            'Не удалось распознать номера. Пожалуйста, введите номера через запятую.\n\n'
            'Пример: 12345678, 87654321, 11223344'
        )
        return

    winners_found = 0
    winners_notified = 0
    errors = []

    for lottery_number in lottery_numbers:
        try:
            tg_id = await get_tg_id_by_lottery_number(lottery_number)
            
            if not tg_id:
                errors.append(f'Номер {lottery_number} не найден в базе')
                continue

            winner_tg_id = await mark_lottery_winner(lottery_number)
            
            if not winner_tg_id:
                errors.append(f'Номер {lottery_number}: не удалось обновить статус')
                continue
            
            winners_found += 1

            winner_keyboard = InlineKeyboardMarkup(row_width=2)
            winner_keyboard.add(
                InlineKeyboardButton("Приду за подарком", callback_data=f"claim_{lottery_number}_yes_{message.chat.id}"),
                InlineKeyboardButton("Не буду забирать приз", callback_data=f"claim_{lottery_number}_no_{message.chat.id}")
            )

            try:
                await bot.send_message(
                    chat_id=winner_tg_id,
                    text=(
                        f'Поздравляем! Вы победили в лотерее!\n\n'
                        f'Ваш лотерейный номер: {lottery_number}\n'
                        f'Приходите в кофейню за своим призом!'
                    ), 
                    reply_markup=winner_keyboard
                )  
                winners_notified += 1
                
            except Exception as e:
                errors.append(f'Номер {lottery_number}: не удалось отправить уведомление ({str(e)})')

            try:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f'Победитель лотереи\n\n'
                        f'Номер: {lottery_number}\n'
                        f'TG ID: {winner_tg_id}\n'
                        f'Ожидается ответ от участника...'
                    )
                )
                
            except Exception as e:
                errors.append(f'Номер {lottery_number}: не удалось уведомить бариста ({str(e)})')
                
                
        except Exception as e:
            errors.append(f'Номер {lottery_number}: ошибка обработки ({str(e)})')
    
    # Формируем отчет
    report = f'Обработка победителей лотереи завершена\n\n'
    report += f' Статистика:\n'
    report += f'• Всего номеров: {len(lottery_numbers)}\n'
    report += f'• Победителей найдено: {winners_found}\n'
    report += f'• Уведомлений отправлено: {winners_notified}\n'
    
    if errors:
        report += f'\nОшибки:\n'
        for error in errors:
            report += f'• {error}\n'
    
    await message.answer(report)

@dp.callback_query_handler(lambda c: c.data.startswith('claim_'))
async def handle_claim_response(callback_query: types.CallbackQuery):
    data = callback_query.data.split('_')
    lottery_number = data[1]
    claimed = data[2] == 'yes'
    admin_tg_id = data[3]
    
    tg_id = await update_lottery_claimed(lottery_number, claimed)
    
    if not tg_id:
        await callback_query.answer('Ошибка: номер не найден', show_alert=True)
        return
    
    if claimed:
        await callback_query.message.edit_text(
            f'Ждем вас за подароком)\n\n'
            f'Номер: {lottery_number}\n'
        )
    else:
        await callback_query.answer('Вы отказались от приза', show_alert=True)
        await callback_query.message.edit_text(
            f'Вы отказались от приза\n\n'
            f'Номер: {lottery_number}'
        )
        
        await bot.send_message(
            admin_tg_id,
            text=f'Победитель {lottery_number} не будет забирать приз\nTG ID: {tg_id}\nМожно провести перерозыгрыш'
        )

@dp.callback_query_handler(lambda c: c.data.startswith('start_work'), state="*")
async def work(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    user_id = callback_query.from_user.id
    work_username = await get_work_username(user_id)
    log_pref = 'Сотрудник'
    date = (datetime.date.today() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')

    await add_log_pref(user_id, work_username, log_pref, date)

    sent_message = await bot.send_message(callback_query.from_user.id, 'Отправьте вашу геолокацию, для согласования с админом', reply_markup=keyboard_start_work)
    edit_message(user_id, sent_message.message_id)
    await Form.get_location_st.set()

@dp.callback_query_handler(lambda c: c.data.startswith('work_change'), state="*")
async def worker_change(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.message.edit_text(f'В качестве кого вы вышли?', reply_markup=keyboard_start_work_change)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('change:'), state="*")
async def change_worker(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    user_id = callback_query.from_user.id
    work_username = await get_work_username(user_id)
    date = (datetime.date.today() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')

    log = callback_query.data.split(':')[1]

    if log == 'helper':
        log_prefix = 'Помощник'
    else:
        log_prefix = 'Сменщик'

    await add_log_pref(user_id, work_username, log_prefix, date)

    sent_message = await bot.send_message(callback_query.from_user.id, 'Отправьте вашу геолокацию, для согласования с админом', reply_markup=keyboard_start_work)
    edit_message(user_id, sent_message.message_id)
    await Form.get_location_st.set()

@dp.message_handler(state=Form.get_location_st, content_types=['location', 'text'])
async def location(message: types.Message, state: FSMContext):
    await check_access(message.from_user.id)
    user_id = message.from_user.id
    request_msg_id = get_message_id(user_id)
    work_username = await get_work_username(user_id)

    date = (datetime.date.today() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
    time_send = (datetime.datetime.now()+ datetime.timedelta(hours=3)).strftime('%H:%M')

    log_prefix, _ = await get_time_send(date, user_id)

    locations = await get_today_workers(date)

    location_map = []

    point_name = ''

    for point, full_name in locations.items():
        if full_name == work_username:
            point_name = point.split('_')[0]
            location_map.append(await get_id(full_name))

    await edit_location(user_id, date, point_name, message.location.latitude, message.location.longitude, time_send)
    
    await bot.delete_message(chat_id=user_id, message_id=message.message_id)
    await bot.delete_message(chat_id=user_id, message_id=request_msg_id)

    if log_prefix == 'Сменщик' or log_prefix == 'Помощник':
        await bot.send_message(user_id, 'На какую точку вы вышли?', reply_markup=keyboard_point_change)
        return

    if user_id in location_map:
        value_to_set = f'{work_username} в {time_send}'
        await add_control_of_delay(date, point_name, value_to_set, user_id)
        await start_shift(date, point_name, user_id)
    else:
        await bot.send_message(user_id, 'Сотрудника какой точки вы заменяете? Выберете', reply_markup=keyboard_point)
        return
    
    await bot.send_message(user_id, 'Ваша геолокация отправлена админу, хорошей смены!', reply_markup=keyboard_ok)
   
@dp.callback_query_handler(lambda c: c.data.startswith('point:'), state="*")
async def point_name(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()
    point_name = callback_query.data.split(':')[1]
    point_tipe = callback_query.data.split(':')[2]

    user_id = callback_query.from_user.id
    worker_username = await get_work_username(user_id)

    date = (datetime.date.today()+ datetime.timedelta(hours=3)).strftime('%Y-%m-%d')

    log_prefix, time_send = await get_time_send(date, user_id)

    point_key = locations.get(point_name)

    await edit_point(user_id, point_key, log_prefix)

    value_to_set = f'{worker_username} в {time_send}'

    await callback_query.message.delete()

    if point_tipe == 'worker':
        await edit_shift(date, point_key, user_id)
        await add_control_of_delay(date, point_key, value_to_set, user_id)
        await change_grafic(date, point_key, worker_username)
    elif point_tipe == 'change':
        if log_prefix == 'Сменщик':
            await edit_shift(date, point_key, user_id)
            await change_grafic(date, point_key, worker_username)
        helper_type = 'ПОМОЩНИКИ' if log_prefix == 'Помощник' else 'СМЕНЩИКИ'
        helper_row_name = f'{date} {helper_type}'
        if helper_row_name:
            await add_control_of_delay(helper_row_name, point_key, value_to_set, user_id)
        else:
            await bot.send_message(admin_id, "[ОШИБКА] Не удалось вставить строку",reply_markup=keyboard_ok)
        make_gen_message(point_key)
    
    await bot.send_message(user_id, 'Ваша геолокация отправлена админу, хорошей смены!', reply_markup=keyboard_ok)

@dp.callback_query_handler(lambda c: c.data.startswith('worker_locations'), state="*")
async def locations_for_day(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()
    location_messages = []

    user_id = callback_query.from_user.id
    date = (datetime.date.today()+ datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
    locations_list = await get_locations_by_date(date)

    for location in locations_list:
        user_work = location['user_id']
        log_prefix = location['log_prefix']
        work_username = await get_work_username(user_work)
        point = location['point']
        time_send = location['time_send']
        latitude = location['latitude']
        longitude = location['longitude']
        if type(latitude) != float or type(longitude) != float:
            pass
        else:
            loc = await bot.send_location(user_id, latitude, longitude)
        location_messages.append(loc.message_id)
        loc_msg = await bot.send_message(user_id, f'{log_prefix} {work_username} {point} отправил геолокацию в {time_send}')
        location_messages.append(loc_msg.message_id)

    await edit_location_messages(user_id, location_messages)

    await bot.send_message(user_id, 'После ознакомления, для очистки данных из памяти нажмите соответствующую кнопку', reply_markup=clear_locations)

@dp.callback_query_handler(lambda c: c.data.startswith('clear'), state="*")
async def clear_locations_data(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    user_id = callback_query.from_user.id
    date = (datetime.date.today()+ datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
    location_messages = get_location_messages(user_id)

    for message_id in location_messages:
        await bot.delete_message(chat_id=user_id, message_id=message_id)

    await clear_locations_by_date(date)

    await callback_query.message.edit_text('Данные геолокаций за сегодня очищены', reply_markup=keyboard_ok)


    
@dp.callback_query_handler(lambda c: c.data.startswith('notification'), state="*")
async def worker_notification(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()
    await callback_query.message.edit_text('О чем вы хотите уведомить администратора?', reply_markup=keyboard_notification)

async def create_calendar_keyboard(prefix: str):
    year = datetime.datetime.now().year
    month = datetime.datetime.now().month
    
    keyboard = InlineKeyboardMarkup(row_width=7)

    days_of_week = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    for day in days_of_week:
        keyboard.insert(InlineKeyboardButton(day, callback_data="ignore"))

    cal = calendar.monthcalendar(year, month)

    for week in cal:
        for day in week:
            if day == 0:
                keyboard.insert(InlineKeyboardButton(' ', callback_data="ignore"))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                keyboard.insert(
                    InlineKeyboardButton(
                        str(day), 
                        callback_data=f"c:{prefix}:{date_str}"
                    )
                )

    keyboard.add(InlineKeyboardButton('Назад', callback_data=f"back"))
    
    return keyboard

async def create_worker_keyboard(date: str, prefix: str):
    keyboard = InlineKeyboardMarkup(row_width=1)

    working = await get_grafic_by_date(date) 
    workers = await get_all_work_username()

    if 'me' in prefix:
        for worker in workers:
            if worker not in working:
                worker = worker.replace(' ', '_')
                keyboard.insert(
                    InlineKeyboardButton(
                        str(worker.replace('_', ' ')), 
                        callback_data=f"w:{prefix}:{worker}"
                    )
                )
    else:
        for worker in working:
            worker = worker.replace(' ', '_')
            keyboard.insert(
                InlineKeyboardButton(
                    str(worker.replace('_', ' ')), 
                    callback_data=f"w:{prefix}:{worker}"
                )
            )

    keyboard.add(InlineKeyboardButton('Назад', callback_data=f"back"))
    
    return keyboard

async def create_agree_keyboard(prefix: str):
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(InlineKeyboardButton('Да все верно', callback_data=f"a:{prefix}"))

    keyboard.add(InlineKeyboardButton('Назад', callback_data=f"back"))
    
    return keyboard

@dp.callback_query_handler(lambda c: c.data.startswith('not:'), state="*")
async def worker_notification(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()
    not_tipe = callback_query.data.split(':')[1]

    if not_tipe == 'i':
        await callback_query.message.edit_text('Какого числа вы выходите на замену?', reply_markup= await create_calendar_keyboard(callback_query.data))
    elif not_tipe == 'me':
        await callback_query.message.edit_text('На какую дату вы нашли себе замену?', reply_markup= await create_calendar_keyboard(callback_query.data))
    elif not_tipe == 'ch':
        await callback_query.message.edit_text('В какой день вы меняетесь сменами?', reply_markup= await create_calendar_keyboard(callback_query.data))

@dp.callback_query_handler(lambda c: c.data.startswith('c:'), state="*")
async def worker_notification(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    _, _,  not_tipe, date_str = callback_query.data.split(':')
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

    if not_tipe == 'i':
        await callback_query.message.edit_text('Кого вы заменяете?', reply_markup= await create_worker_keyboard(date, callback_query.data))
    elif not_tipe == 'me':
        await callback_query.message.edit_text('Кто вас заменяет?', reply_markup= await create_worker_keyboard(date, callback_query.data))
    elif not_tipe == 'ch':
        await callback_query.message.edit_text('С кем вы меняетесь сменами?', reply_markup= await create_worker_keyboard(date, callback_query.data))

@dp.callback_query_handler(lambda c: c.data.startswith('w:'), state="*")
async def worker_notification(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    _, _, _, not_tipe, date_str, worker_username = callback_query.data.split(':')
    worker_username = worker_username.replace('_', ' ')
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

    if not_tipe == 'ch':
        first_point, second_point = await get_point(date, await get_work_username(callback_query.from_user.id), worker_username, not_tipe)
        await callback_query.message.edit_text(f'Вы выходить вместо {worker_username} на {first_point} {date}, а этот сотрудник вместо вас на {second_point}?', reply_markup=create_agree_keyboard(callback_query.data))
    else:
        point = await get_point(date, await get_work_username(callback_query.from_user.id), worker_username, not_tipe)
        if not_tipe == 'i':
            await callback_query.message.edit_text(f'Вы выходите вместо {worker_username} на {point} {date}?', reply_markup= await create_agree_keyboard(callback_query.data))
        elif not_tipe == 'me':
            await callback_query.message.edit_text(f'Вместо вас выходит {worker_username} на {point} {date}?', reply_markup= await create_agree_keyboard(callback_query.data))

@dp.callback_query_handler(lambda c: c.data.startswith('a:'), state="*")
async def notific_ver(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    if await get_admin(callback_query.from_user.id) in ['admin', 'boss']:
        reply_markup = keyboard_admin
    else:
        reply_markup = keyboard1

    _, _, _, _, not_tipe, date_str, worker_username = callback_query.data.split(':')
    worker_username = worker_username.replace('_', ' ')
    worker = await get_work_username(callback_query.from_user.id)
    date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

    await changes_in_grafic(date, await get_work_username(callback_query.from_user.id), worker_username, not_tipe)

    if not_tipe == 'ch':
        first_point, second_point = await get_point(date, await get_work_username(callback_query.from_user.id), worker_username, not_tipe)
        await bot.send_message(admin_id_1, f'ТАБЛИЦА В МИНИ ПРИЛОЖЕНИИ!!! Я тестирую базу данных. Сотрудники {worker_username} выходит на {second_point}, а {worker} на {first_point} {date}\nДанные в таблице график обновлены, проверьте', reply_markup=keyboard_ok)
        await bot.send_message(await get_id(worker_username), f'НЕ ДОБАВЛЕНО В ТАБЛИЦУ!!! Я тестирую базу данных. Сотрудник {worker} сообщил, что вы поменялись точками {date}', reply_markup=keyboard_ok)
        await callback_query.message.edit_text('ТАБЛИЦА В МИНИ ПРИЛОЖЕНИИ!!! Я тестирую базу данных. Благодарю, администратору отправлено уведомление о вашей замене', reply_markup=reply_markup)
    else:
        point = await get_point(date, await get_work_username(callback_query.from_user.id), worker_username, not_tipe)
        if not_tipe == 'i':
            await bot.send_message(admin_id_1, f'ТАБЛИЦА В МИНИ ПРИЛОЖЕНИИ!!! Я тестирую базу данных. Вместо сотрудника {worker_username}, {date} на точку {point} выйдет {worker}\nДанные в таблице график обновлены, проверьте', reply_markup=keyboard_ok)
            await bot.send_message(await get_id(worker_username), f'НЕ ДОБАВЛЕНО В ТАБЛИЦУ!!! Я тестирую базу данных. Сотрудник {worker} сообщил, что он заменяет вас {date} по адресу {point}', reply_markup=keyboard_ok)
            await callback_query.message.edit_text('ТАБЛИЦА В МИНИ ПРИЛОЖЕНИИ!!! Я тестирую базу данных. Благодарю, администратору отправлено уведомление о вашей замене', reply_markup=reply_markup)
        elif not_tipe == 'me':
            await bot.send_message(admin_id_1, f'ТАБЛИЦА В МИНИ ПРИЛОЖЕНИИ!!! Я тестирую базу данных. Вместо сотрудника {worker}, {date} на точку {point} выйдет {worker}\nСотрудник {worker_username} не найден в таблице, данные изменены в ячейке, проверьте', reply_markup=keyboard_ok)
            await bot.send_message(await get_id(worker_username), f'НЕ ДОБАВЛЕНО В ТАБЛИЦУ!!! Я тестирую базу данных. Сотрудник {worker} сообщил, что вы заменяете его {date} по адресу {point}', reply_markup=keyboard_ok)
            await callback_query.message.edit_text('ТАБЛИЦА В МИНИ ПРИЛОЖЕНИИ!!! Я тестирую базу данных. Благодарю, администратору отправлено уведомление о вашей замене', reply_markup=reply_markup)

@dp.callback_query_handler(lambda c: c.data.startswith('OK'), state="*")
async def ok_message(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()
    await callback_query.message.delete()

@dp.callback_query_handler(lambda c: c.data.startswith('worker_list'), state="*")
async def worker_user_list(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(text='Добавить сотрудника', callback_data='work_list:add'),
        InlineKeyboardButton(text='Удалить сотрудника', callback_data='work_list:del'),
        InlineKeyboardButton(text='Список всех сотрудников', callback_data='work_list:see'),
        InlineKeyboardButton(text='Поменять имя сотрудника по графику', callback_data='work_list:update'),
        InlineKeyboardButton(text='Назад в главное меню', callback_data='back')
    )

    await callback_query.message.edit_text('Для добавления сотрудника вам нужен его user_id, если вы его не знаете, попросите нового сотрудника запросить доступ напрямую через бота', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('allow'), state="*")
async def ok_message(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    cancel = InlineKeyboardMarkup()
    cancel.add(
        InlineKeyboardButton(text='Отмена', callback_data='cancel')
    )

    edit_message(callback_query.from_user.id, callback_query.message.message_id)

    await callback_query.message.edit_text('Ваше имя', reply_markup=cancel)
    await Form.verification.set()

@dp.message_handler(state=Form.verification)
async def verification_us(message: types.Message, state: FSMContext):
    global user_id_ver, name_ver
    user_id_ver = message.from_user.id
    username = message.from_user.username
    name_ver = message.text.strip()

    message_id = get_message_id(user_id_ver)

    await bot.delete_message(chat_id=user_id_ver, message_id=message.message_id)
    await bot.delete_message(chat_id=user_id_ver, message_id=message_id)

    sent_mes = await bot.send_message(user_id_ver, 'Ваша заявка направлена администратору')

    edit_message(user_id_ver, sent_mes.message_id)

    allow_verification = InlineKeyboardMarkup()
    allow_verification.add(
        InlineKeyboardButton(text='Принять', callback_data='verification:allow'),
        InlineKeyboardButton(text='Отклонить', callback_data='verification:forbid')
    )

    await bot.send_message(admin_id, f'Пользователь {name_ver} {user_id_ver} @{username} запросил доступ', reply_markup=allow_verification)

@dp.callback_query_handler(lambda c: c.data.startswith('verification:'), state="*")
async def verific_use(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    ver = callback_query.data.split(':')[1]
    message_id_ver = get_message_id(user_id_ver)

    if ver == 'allow':
        await bot.delete_message(chat_id=user_id_ver, message_id=message_id_ver)
        await callback_query.message.edit_text('Имя сотрудника в графике')
        edit_message(callback_query.from_user.id ,callback_query.message.message_id)
        await Form.work_name_user.set()
    else:
        await callback_query.message.delete()
        await bot.edit_message_text(chat_id=user_id_ver, message_id=message_id_ver, text='Ваш запрос отклонен, досвидания', reply_markup=keyboard_ok)

@dp.message_handler(state=Form.work_name_user)
async def verification_users_name(message: types.Message, state: FSMContext):
    global idx
    work_username = message.text.strip()
    admin_message_id = get_message_id(message.from_user.id)

    await bot.delete_message(chat_id=admin_id, message_id=admin_message_id)
    await bot.delete_message(chat_id=admin_id, message_id=message.message_id)

    idx = await get_id(work_username)

    await bot.send_message(admin_id, 'Выберите какую должность занимает сотрудник', reply_markup=admin)

@dp.callback_query_handler(lambda c: c.data.startswith('title:'), state="*")
async def end_of_verification(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    user_id = await get_state_form(idx) 

    job_title = callback_query.data.split(':')[1]

    if user_id != user_id_ver:
        await callback_query.message.edit_text('Сотрудник добавлен в БД, хорошего дня!', reply_markup=keyboard_back)
    else:
        await bot.send_message(chat_id=user_id_ver, text='Администратор принял вашу заявку', reply_markup=keyboard_back)
        await callback_query.message.edit_text('Сотрудник добавлен в систему, хорошего дня!', reply_markup=keyboard_ok)
        
@dp.callback_query_handler(lambda c: c.data.startswith('work_list:'), state="*")
async def work_user_list(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    tipe = callback_query.data.split(':')[1]

    if tipe == 'add':
        await callback_query.message.edit_text('Напишите user_id, имя сотрудника просто и как в графике, через запятую. Пример - 111111111, Лина, Ангелина в', reply_markup=keyboard_back)
        edit_message(callback_query.from_user.id ,callback_query.message.message_id)
        await Form.add_user_st.set()
    elif tipe == 'del':
        await callback_query.message.edit_text('Напишите имя сотрудника как в графике, чтобы я мог вычислить его user_id', reply_markup=keyboard_back)
        edit_message(callback_query.from_user.id ,callback_query.message.message_id)
        await Form.del_user_st.set()
    elif tipe == 'update':
        await callback_query.message.edit_text('Напишите имя сотрудника как в графике было раньше и на какое нужно поменять. Все через запятую', reply_markup=keyboard_back)
        edit_message(callback_query.from_user.id ,callback_query.message.message_id)
        await Form.update_user_st.set()

@dp.message_handler(state=Form.add_user_st)
async def add_user_on_list(message: types.Message, state: FSMContext):
    await check_access(message.from_user.id)
    global idx
    user_id = int(message.text.split(',')[0])
    username = message.text.split(',')[1].strip()
    work_username = message.text.split(',')[2].strip()

    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)

    message_id = get_message_id(message.from_user.id)

    idx = await get_id(work_username)
    await bot.edit_message_text(chat_id=message.from_user.id, message_id=message_id, text='Выберите какую должность занимает сотрудник', reply_markup=admin)

@dp.message_handler(state=Form.del_user_st)
async def del_user_on_list(message: types.Message, state: FSMContext):
    await check_access(message.from_user.id)
    name = message.text.strip()

    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)

    message_id = get_message_id(message.from_user.id)

    await bot.edit_message_text(chat_id=message.from_user.id, message_id=message_id, text='Сотрудник удален из базы, можете проверить в списке сотрудников', reply_markup=keyboard_back)

@dp.message_handler(state=Form.update_user_st)
async def update_user_on_list(message: types.Message, state: FSMContext):
    await check_access(message.from_user.id)
    old_work_username = message.text.split(',')[0].strip()
    new_work_username = message.text.split(',')[1].strip()

    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)

    message_id = get_message_id(message.from_user.id)

    await bot.edit_message_text(chat_id=message.from_user.id, message_id=message_id, text='Данные обновлены можете проверить в списке сотрудников', reply_markup=keyboard_back)

@dp.callback_query_handler(lambda c: c.data.startswith('payroll_sheets'), state="*")
async def add_payroll_sheets(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    global df_money
    await callback_query.answer()

    user_id = callback_query.from_user.id

    df_money_spread = Spread(spread='1u461QHkwAGssXHOJ94ftvdO2OaeuLmhGvz9U7n1m0Uo', config=secret, sheet='Выплата сотрудникам за неделю')
    df_money = df_money_spread.sheet_to_df().reset_index(drop=True)
    df_money['Сколько перевести'] = (
        df_money['Сколько перевести']
        .astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .replace('#N/A', '0')
        .replace('', '0')
        .astype(int)
    )
    df_money = df_money.iloc[:, 0:11]
    df_money['Имя'] = df_money['Имя'].str.lower()

    unique_names = df_money['Имя'].dropna().unique()

    sent_message_ids = []

    for name in unique_names:
        if not name.strip():
            continue
        try:
            image_buffer = tables(name)
            image_buffer.seek(0)

            msg = await bot.send_photo(
                chat_id=user_id,
                photo=InputFile(image_buffer, filename=f"{name}.png"),
                caption=name.capitalize()
            )
            sent_message_ids.append(msg.message_id)

        except Exception as e:
            error_msg = await bot.send_message(
                chat_id=user_id,
                text=f"Ошибка при генерации табеля для {name}: {str(e)}"
            )
            sent_message_ids.append(error_msg.message_id)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('Ознакомлен', callback_data='delete_payroll_messages'))
    button_msg = await bot.send_message(chat_id=user_id, text='Табели за неделю, после ознакомления диалог очистится, сначала разошлите табели сотрудникам', reply_markup=keyboard)
    
    edit_sent_messages(user_id, sent_message_ids)

@dp.callback_query_handler(lambda c: c.data.startswith('delete_payroll_messages'), state="*")
async def add_payroll_sheets(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    user_id = callback_query.from_user.id

    sent_message_ids = get_sent_messages(user_id)

    for message_id in sent_message_ids:
        await bot.delete_message(chat_id=user_id, message_id=message_id)

    reply_markup = keyboard_admin if await get_admin(user_id) in ['admin', 'boss'] else keyboard1

    await callback_query.message.edit_text('Данные с табелями очищенны', reply_markup=keyboard_ok)

@dp.callback_query_handler(lambda c: c.data.startswith('question'), state="*")
async def handle_ask_document(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()
    await callback_query.message.edit_text('Что вас интересует?', reply_markup=get_category_keyboard())
   
@dp.callback_query_handler(lambda c: c.data == 'back_to_categories', state='*')
async def back_to_categories(callback_query: types.CallbackQuery):
    await check_access(callback_query.from_user.id)
    await callback_query.message.edit_text('Что вы хотите узнать?', reply_markup=get_category_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith('cat:'), state='*')
async def handle_category(callback_query: types.CallbackQuery):
    await check_access(callback_query.from_user.id)
    cat_index = int(callback_query.data.split(':')[1])
    cat_name = CATEGORY_LIST[cat_index]

    if cat_name == 'Штрафы':
        media = types.MediaGroup()
        media.attach_photo(types.InputFile('data/shtraf_1.jpg'))
        media.attach_photo(types.InputFile('data/shtraf_2.jpg'))
        await callback_query.message.answer_photo(
            photo=types.InputFile('data/shtraf_1.jpg'),
            caption='Фото 1 из 2: Штрафы',
            reply_markup=keyboard_ok
        )
        await callback_query.message.answer_photo(
            photo=types.InputFile('data/shtraf_2.jpg'),
            caption='Фото 2 из 2: Штрафы',
            reply_markup=keyboard_ok
        )
        return

    if cat_name == 'Ссылки':
        kb = InlineKeyboardMarkup()
        for btn in CATEGORIES['Ссылки']['buttons']:
            kb.add(InlineKeyboardButton(btn['text'], url=btn['url'].strip()))
        kb.add(InlineKeyboardButton('К категориям', callback_data='back_to_categories'))
        await callback_query.message.edit_text('Полезные ссылки:', reply_markup=kb)
        return

    kb, _, _ = get_subcategories_paginated(cat_index, page=0)
    if kb:
        await callback_query.message.edit_text(f'Категория: {cat_name}\nВыберите подкатегорию:', reply_markup=kb)
    else:
        await callback_query.message.edit_text('Подкатегории не найдены.', reply_markup=get_category_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith('cat_page:'), state='*')
async def handle_subcategory_pagination(callback_query: types.CallbackQuery):
    await check_access(callback_query.from_user.id)
    _, cat_index, page = callback_query.data.split(':')
    cat_index = int(cat_index)
    page = int(page)
    kb, _, _ = get_subcategories_paginated(cat_index, page)
    await callback_query.message.edit_text(f'{page + 1}', reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('sec:'), state='*')
async def handle_subcategory(callback_query: types.CallbackQuery):
    await check_access(callback_query.from_user.id)
    _, cat_index, subcat_index_str = callback_query.data.split(':', 2)
    cat_index = int(cat_index)
    subcat_index = int(subcat_index_str)

    cat_name = CATEGORY_LIST[cat_index]
    subcats = list(CATEGORIES[cat_name]['subcategories'].keys())

    if subcat_index < 0 or subcat_index >= len(subcats):
        await callback_query.message.edit_text('Ошибка: подкатегория не найдена', reply_markup=keyboard_back)
        return

    subcat_name = subcats[subcat_index]
    subcat_data = CATEGORIES[cat_name]['subcategories'][subcat_name]

    text = ""
    if 'text_file' in subcat_data and subcat_data['text_file']:
        try:
            with open(subcat_data['text_file'], 'r', encoding='utf-8') as f:
                text = f.read().strip()
        except Exception as e:
            return None
    elif 'text' in subcat_data:
        text = subcat_data['text']
    else:
        text = 'Информация отсутствует'

    if len(text) > 4000:
        text = text[:4000] + '...'

    kb = InlineKeyboardMarkup()
    if 'buttons' in subcat_data:
        for btn in subcat_data['buttons']:
            if btn.get('url'):
                kb.add(InlineKeyboardButton(btn['text'], url=btn['url'].strip()))
    kb.add(InlineKeyboardButton('К подкатегориям', callback_data=f'cat_page:{cat_index}:0'),
           InlineKeyboardButton('Назад в главное меню', callback_data='back'))

    await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)

@dp.callback_query_handler(lambda c: c.data.startswith('back'), state='*')
async def back_button(callback_query: types.CallbackQuery, state: FSMContext):
    await check_access(callback_query.from_user.id)
    await callback_query.answer()

    user_id = callback_query.from_user.id
    reply_markup = keyboard_admin if await get_admin(user_id) in ['admin', 'boss'] else keyboard1

    try:
        await callback_query.message.edit_text('Чем могу помочь?)', reply_markup=reply_markup)
    except BadRequest as e:
        if 'There is no text' in str(e):
            await callback_query.message.delete()
            await callback_query.message.answer('Чем могу помочь?)', reply_markup=reply_markup)

def make_send_message(key):
    @check_employee_exists(key)
    async def handler():
        try:
            date = (datetime.datetime.now() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
            workers = await get_today_workers(date)
        
            if not workers:
                logger.info(f"На дату {date} нет записей в графике")
                return
        
            logger.info(f"Поиск работника на точке '{key}' среди: {list(workers.items())}")

            for point_value, employee_name in workers.items():
                try:
                    worker_point = point_value.split('_')[0]
                except Exception:
                    worker_point = point_name

                if worker_point != key:
                    continue

                chat_id = await get_id(employee_name)
                if not chat_id:
                    logger.warning(f"Не найден chat_id для {employee_name}, пропускаем")
                    continue

                logger.info(f"Работник найден: {employee_name} ({point_value}), chat_id: {chat_id}")
            
                try:
                    msg = 'Доброе утро! Через 10 минут начало рабочего дня\nНе забудь начать смену)'
                    await bot.send_message(chat_id, msg, reply_markup=keyboard_ok)
                    logger.info(f"Утреннее сообщение отправлено {employee_name}")

                    weekday = datetime.datetime.now().weekday()
                
                    if weekday in (0, 3):
                        await bot.send_message(
                            chat_id, 
                            'Сегодня чек лист, заполнить до 13.00', 
                            reply_markup=kb_chek
                        )
                        logger.info(f"Сообщение про чек-лист отправлено {employee_name}")
                    
                    #elif weekday in (1, 3):
                        #await bot.send_message(
                            #chat_id, 
                            #'Сегодня заказ молока до 16.00, за отсутствие молока на следующий день штраф 700 рублей)', 
                           #reply_markup=keyboard_ok
                        #)
                        #logger.info(f"Сообщение про молоко отправлено {employee_name}")

                    return
                
                except Exception as send_err:
                    logger.error(f"Ошибка при отправке сообщения {employee_name}: {send_err}")
                    continue

            logger.warning(f"Не найден работник на точке '{key}' в графике на {date}")
        
        except Exception as e:
            logger.exception(f"Критическая ошибка в make_send_message('{key}'): {e}")
    return handler


def make_end_message(key):
    @check_employee_exists(key)
    async def handler():
        try:
            date = (datetime.datetime.now() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
            workers = await get_today_workers(date)
        
            if not workers:
                logger.info(f"На дату {date} нет активных записей в графике")
                return
        
            logger.info(f"Поиск активного работника на точке '{key}' среди: {list(workers.items())}")

            for point_value, employee_name in workers.items():
                try:
                    worker_point = point_value.split('_')[0]
                except:
                    worker_point = point_value

                if worker_point != key:
                    continue

                chat_id = await get_id(employee_name)
                if not chat_id:
                    logger.warning(f"Не найден chat_id для {employee_name}, пропускаем")
                    continue

                shift_started = await get_shift_status(date, point_value, chat_id)
            
                if not shift_started:
                    logger.info(f"Смена у {employee_name} ({point_value}) не активна, пропускаем")
                    continue

                logger.info(f"Активная смена найдена: {employee_name} ({point_value}), chat_id: {chat_id}")
            
                try:
                    await bot.send_message(
                        chat_id,
                        'Через 10 минут конец рабочего дня, не забудь заполнить отчет по выручке, хорошего вечера)',
                        reply_markup=kb_end
                    )
                    logger.info(f"Сообщение отправлено {employee_name}")

                    await end_shift(date, point_value, chat_id)
                    logger.info(f"Смена закрыта для {employee_name}")

                    return
                
                except Exception as send_err:
                    logger.error(f"Ошибка при отправке сообщения {employee_name}: {send_err}")
                    continue

            logger.warning(f"Не найдено активных смен на точке '{key}'")
                
        except Exception as e:
            logger.error(f"ОШИБКА в make_end_message ({key}): {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    return handler


def make_gen_message(key):
    @check_employee_exists(key)
    async def handler():
        try:
            date = (datetime.datetime.now() + datetime.timedelta(hours=3)).date()
            first_day_weekday = date.replace(day=1).weekday()
            week_number = (date.day + first_day_weekday - 1) // 7 + 1
            workers = await get_today_workers(date)
        
            if not workers:
                logger.info(f"На дату {date} нет активных записей в графике")
                return
        
            logger.info(f"Поиск работника на точке '{key}' среди: {list(workers.items())}")

            chem_dates, gen_dates = await get_gen_reminder(date)

            for point_value, employee_name in workers.items():
                try:
                    worker_point = point_value.split('_')[0]
                except Exception:
                    worker_point = point_value

                if worker_point != key:
                    continue

                chat_id = await get_id(employee_name)
                if not chat_id:
                    logger.warning(f"Не найден chat_id для {employee_name}, пропускаем")
                    continue

                shift_started = await get_shift_status(date, point_value, chat_id)
            
                if not shift_started:
                    logger.info(f"Смена у {employee_name} ({point_value}) не активна, пропускаем")
                    continue
            
                logger.info(f"Активная смена найдена: {employee_name} ({point_value}), chat_id: {chat_id}")
            
                try:
                    if date in chem_dates:
                        await bot.send_message(
                            chat_id, 
                            'Сегодня по графику мытье кофемашины с химией', 
                            reply_markup=keyboard_ok
                        )
                        logger.info(f"Сообщение про химию отправлено {employee_name}")

                    if week_number == 2 or week_number == 4:
                        if first_day_weekday in (0,1,2):
                            text = gen_points[0]
                        elif first_day_weekday == 3:
                            text = gen_points[3]
                        elif first_day_weekday == 4:
                            text = gen_points[4]
                        elif first_day_weekday == 5:
                            text = gen_points[5]
                        elif first_day_weekday == 6:
                            text = gen_points[6]
                        await bot.send_message(
                            chat_id, 
                            f'Сегодня по графику генеральная уборка\n\nВыполняем\n{text}', 
                            reply_markup=keyboard_ok
                        )
                        logger.info(f"Сообщение про ген. уборку отправлено {employee_name}")
                
                except Exception as send_err:
                    logger.error(f"Ошибка при отправке напоминания {employee_name}: {send_err}")
                    continue

            logger.warning(f"Не найдено активных смен на точке '{key}' для напоминания об уборке")
        
        except Exception as e:
            logger.exception(f"Критическая ошибка в make_gen_message('{key}'): {e}")
    return handler


def make_cleaning_reminder(key):
    async def handler():
        try:
            date = (datetime.datetime.now() + datetime.timedelta(hours=3)).date()
            first_day_weekday = date.replace(day=1).weekday()
            week_number = (date.day + first_day_weekday - 1) // 7 + 1
            workers = await get_today_workers(date)
        
            if not workers:
                logger.info(f"На дату {date} нет активных записей в графике")
                return
        
            logger.info(f"Поиск работника на точке '{key}' среди: {list(workers.items())}")

            chem_dates, gen_dates = await get_gen_reminder(date)

            for point_value, employee_name in workers.items():
                try:
                    worker_point = point_value.split('_')[0]
                except Exception:
                    worker_point = point_value

                if worker_point != key:
                    continue

                chat_id = await get_id(employee_name)
                if not chat_id:
                    logger.warning(f"Не найден chat_id для {employee_name}, пропускаем")
                    continue

                shift_started = await get_shift_status(date, point_value, chat_id)
            
                if not shift_started:
                    logger.info(f"Смена у {employee_name} ({point_value}) не активна, пропускаем")
                    continue
            
                logger.info(f"Активная смена найдена: {employee_name} ({point_value}), chat_id: {chat_id}")
            
                try:
                    if date in chem_dates:
                        await bot.send_message(
                            chat_id, 
                            'Сегодня по графику было мытье кофемашины с химией, не забудьте заполнить отчет', 
                            reply_markup=kb_gen
                        )
                        logger.info(f"Сообщение про химию отправлено {employee_name}")

                    if week_number == 2 or week_number == 4:
                        if first_day_weekday in (0,1,2):
                            text = gen_points[0]
                        elif first_day_weekday == 3:
                            text = gen_points[3]
                        elif first_day_weekday == 4:
                            text = gen_points[4]
                        elif first_day_weekday == 5:
                            text = gen_points[5]
                        elif first_day_weekday == 6:
                            text = gen_points[6]
                        await bot.send_message(
                            chat_id, 
                            f'Сегодня по графику была генеральная уборка, не забудьте заполнить отчет\n\nВы должны были выполнить\n{text}', 
                            reply_markup=kb_gen
                        )
                        logger.info(f"Сообщение про ген. уборку отправлено {employee_name}")
                
                except Exception as send_err:
                    logger.error(f"Ошибка при отправке напоминания {employee_name}: {send_err}")
                    continue

            logger.warning(f"Не найдено активных смен на точке '{key}' для напоминания об уборке")
        
        except Exception as e:
            logger.exception(f"Критическая ошибка в make_gen_message('{key}'): {e}")
    return handler


def make_out_work(key, location_name):
    @check_employee_exists(key)
    async def handler():
        try:
            date = (datetime.datetime.now() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
            workers = await get_today_workers(date)
        
            if not workers:
                logger.info(f"На дату {date} нет записей в графике")
                return
        
            logger.info(f"Проверка опозданий на точке '{key}' среди: {list(workers.items())}")

            control_value = await get_control_of_delay(date, key)
            logger.info(f"Значение из get_control_of_delay('{date}', '{key}'): {control_value}")

            for point_value, employee_name in workers.items():
                try:
                    worker_point = point_value.split('_')[0]
                except Exception:
                    worker_point = point_name

                if worker_point != key:
                    continue

                logger.info(f"Работник на точке '{key}': {employee_name} ({point_value})")

                if control_value is None or str(control_value).strip() == '':
                    message = (
                        f'Прошло 10 минут с начала рабочего дня, сотрудник {employee_name} не отправил геолокацию\n'
                        f'Адрес кофейни: {location_name}'
                    )

                    for admin_chat_id in [admin_id, admin_id_1, admin_id_2]:
                        if admin_chat_id:
                            try:
                                await bot.send_message(admin_chat_id, message, reply_markup=keyboard_ok)
                            except Exception as admin_err:
                                logger.error(f"Не удалось отправить уведомление админу {admin_chat_id}: {admin_err}")
                
                    logger.warning(f"ОТПРАВЛЕНО ПРЕДУПРЕЖДЕНИЕ АДМИНАМ об опоздании {employee_name} ({point_value})")
                else:
                    logger.info(f"Сотрудник {employee_name} ({point_value}) отметился вовремя")

            logger.warning(f"Не найден работник на точке '{key}' в графике на {date}")
        
        except Exception as e:
            logger.exception(f"Критическая ошибка в make_out_work('{key}', '{location_name}'): {e}")
    return handler


async def schedule_nk_jobs(scheduler):
    if datetime.datetime.now().isoweekday() >= 6:
        morning_time = ('08', '50')
        evening_time = ('20', '50')
        gen_time = ('09', '30')
        gen_end = ('20', '30')
        out_time = ('09', '10')
    else:
        morning_time = ('8', '20')
        evening_time = ('20', '20')
        gen_time = ('09', '00')
        gen_end = ('20', '00')
        out_time = ('08', '40')

    scheduler.add_job(make_send_message('нк'), 'cron', hour=morning_time[0], minute=evening_time[1], timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)
    scheduler.add_job(make_end_message('нк'), 'cron', hour=evening_time[0], minute=evening_time[1], timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)
    scheduler.add_job(make_gen_message('нк'), 'cron', hour=gen_time[0], minute=gen_time[1], timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)
    scheduler.add_job(make_cleaning_reminder('нк'), 'cron', hour=gen_end[0], minute=gen_end[1], timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)
    scheduler.add_job(make_out_work('нк', 'Новокосино'), 'cron', hour=out_time[0], minute=out_time[1], timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)

async def schedule_messages():
    scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
    
    location = {

    }

    await schedule_nk_jobs(scheduler)

    morning_times = []
    evening_times = []
    gen_time = []
    gen_end = []
    out_time = []

    for (mh, mm), (eh, em), (gh, gm), (geh, gem), (oh, om), key in zip(morning_times, evening_times, gen_time, gen_end, out_time, location.keys()):
        scheduler.add_job(make_send_message(key), 'cron', hour=mh, minute=mm, timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)
        scheduler.add_job(make_end_message(key), 'cron', hour=eh, minute=em, timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)
        scheduler.add_job(make_gen_message(key), 'cron', hour=gh, minute=gm, timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)
        scheduler.add_job(make_cleaning_reminder(key), 'cron', hour=geh, minute=gem, timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)
        scheduler.add_job(make_out_work(key, location[key]), 'cron', hour=oh, minute=om, timezone='Europe/Moscow', coalesce=True, misfire_grace_time=420)

    scheduler.start()

async def cache_updater():
    while True:
        await update_cached_data()
        await asyncio.sleep(60 * 180)

async def on_startup(_):
    await init_db()
    asyncio.create_task(cache_updater())
    await schedule_messages()

if __name__ == '__main__':
    db_message()
    executor.start_polling(dp, on_startup=on_startup)
