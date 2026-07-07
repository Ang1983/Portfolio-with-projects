import sqlite3
import asyncpg
import os
import json
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

MESSAGES_DB = '/data/messages.db' 

load_dotenv()
pool: Optional[asyncpg.Pool] = None

async def get_pool():
    return await asyncpg.create_pool(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

async def init_db():
    global pool
    pool = await get_pool()

async def close_db():
    if pool:
        await pool.close()

async def get_tg_id(user_id: int):
    async with pool.acquire() as conn:
        if isinstance(user_id, str):
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return None
            
        tg_id = await conn.fetch(
            '''SELECT user_id 
               FROM employee
               WHERE max_user_id=$1''',
               user_id
        )
        if tg_id:
            return int(tg_id[0]['user_id'])
        return None

async def get_gen_reminder(date: str):
    async with pool.acquire() as conn:
        if isinstance(date, str):
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            date_obj = date
        await conn.execute(
            '''DELETE FROM grafic_of_gen 
               WHERE "мытье с химией" < $1 
               AND "ген. уборка" < $1''',
            date_obj
        )

        rows = await conn.fetch(
            '''SELECT "мытье с химией", "ген. уборка" 
               FROM grafic_of_gen 
               ORDER BY "мытье с химией" ASC'''
        )

        chem_dates = [row['мытье с химией'] for row in rows if row['мытье с химией']]
        gen_dates = [row['ген. уборка'] for row in rows if row['ген. уборка']]
        
        return chem_dates, gen_dates

async def get_control_of_delay(date: str, point: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f'SELECT "{point}" FROM control_of_delays WHERE date = $1',
            date
        )
        return row[f"{point}"]
    
async def update_lottery_claimed(lottery_number: str, claimed: bool) -> Optional[int]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''SELECT tg_id 
               FROM lottery_participants 
               WHERE lottery_number = $1::text''',
            str(lottery_number).strip()
        )
        
        if not row:
            return None
        
        await conn.execute(
            '''UPDATE lottery_participants 
               SET notified = $1
               WHERE lottery_number = $2::text''',
            claimed, str(lottery_number).strip()
        )
        
        return int(row['tg_id'])
    
    
async def get_tg_id_by_lottery_number(lottery_number: str) -> Optional[int]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT tg_id FROM lottery_participants WHERE lottery_number = $1',
            lottery_number.strip()
        )
        return row['tg_id'] if row else None


async def get_lottery_participant(lottery_number: str) -> Optional[Dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM lottery_participants WHERE lottery_number = $1',
            lottery_number.strip()
        )
        return dict(row) if row else None


async def mark_lottery_winner(lottery_number: str) -> Optional[int]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            '''SELECT tg_id 
               FROM lottery_participants 
               WHERE lottery_number = $1::text''',
            str(lottery_number).strip()
        )
        
        if not row:
            return None
        
        await conn.execute(
            '''UPDATE lottery_participants 
               SET is_winner = TRUE
               WHERE lottery_number = $1::text''',
            str(lottery_number).strip()
        )
        
        return int(row['tg_id'])


async def get_all_lottery_participants() -> List[Dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM lottery_participants ORDER BY created_at DESC')
        return [dict(row) for row in rows]



async def get_today_workers(date_param) -> Dict[str, str]:
    if isinstance(date_param, str):
        date_obj = datetime.strptime(date_param, '%Y-%m-%d').date()
    else:
        date_obj = date_param
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM grafic WHERE date = $1',
            date_obj
        )

        if not row:
            return {}

        return {
            v: k for k, v in row.items()
            if k not in ('id', 'date') and v not in (None, '') and str(v).strip()
        }

async def get_cashier_id(point: str):
    async with pool.acquire() as conn:
        cashier_id = await conn.fetchval(
            'SELECT id FROM cashier WHERE short_name_point = $1',
            point
        )
        return cashier_id
    
async def get_shift_status(date: str, point: str, user_id: int) -> bool:
    async with pool.acquire() as conn:
        if isinstance(date, str):
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            date_obj = date

        point_check = point.split('_')[0] if '_' in point else point

        cashier_id = await get_cashier_id(point_check)

        row = await conn.fetchrow('''
            SELECT 1 
            FROM shift 
            WHERE date_shift = $1 
              AND cashier_id = $2 
              AND user_id = $3
              AND active_status = 'начата'
            LIMIT 1
        ''', date_obj, cashier_id, user_id)

        return row is not None 
    
async def start_shift(date: str, point: str, user_id: int):
    async with pool.acquire() as conn:
        if isinstance(date, str):
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            date_obj = date

        cashier_id = await get_cashier_id(point)

        await conn.execute('''
            UPDATE shift 
            SET active_status = 'начата'
            WHERE date_shift = $1 
              AND cashier_id = $2 
              AND user_id = $3
        ''', date_obj, cashier_id, user_id)
    
async def end_shift(date: str, point: str, user_id: int):
    async with pool.acquire() as conn:
        cashier_id = await get_cashier_id(point)

        if isinstance(date, str):
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            date_obj = date

        await conn.execute('''
            UPDATE shift 
            SET active_status = 'закончена'
            WHERE date_shift = $1 
              AND cashier_id = $2 
              AND active_status = 'начата'
              AND user_id = $3
        ''', date_obj, cashier_id, user_id)

async def edit_shift(date: str, point: str, user_id: int):
    async with pool.acquire() as conn:
        cashier_id = await get_cashier_id(point)
        if not cashier_id:
            return

        if isinstance(date, str):
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            date_obj = date

        log_prefix = await conn.fetchval(
            'SELECT log_prefix FROM locations WHERE date = $1 AND user_id = $2',
            date, user_id
        )

        active_shift = await conn.fetchval(
            'SELECT id FROM shift WHERE date_shift = $1 AND cashier_id = $2 AND active_status = $3',
            date_obj, cashier_id, 'начата'
        )

        employee = await conn.fetchval(
            'SELECT full_name FROM employee WHERE user_id = $1',
            user_id
        )

        employee_on_point = await conn.fetchval(
            f'SELECT "{point}" FROM grafic_on_point WHERE date = $1',
            date_obj
        )

        if employee != employee_on_point:
            await conn.execute(f'''
                UPDATE grafic_on_point 
                SET "{point}" = $1
                WHERE date = $2
            ''', employee, date_obj)

        if log_prefix == 'Сотрудник':
            try:
                await conn.execute('''
                    UPDATE shift 
                    SET user_id = $1, active_status = 'начата'
                    WHERE cashier_id = $2 AND date_shift = $3
                ''', user_id, cashier_id, date_obj)
            except:
                await conn.execute('''
                    INSERT INTO shift (date_shift, cashier_id, user_id, active_status)
                    VALUES ($1, $2, $3, 'начата')
                    ON CONFLICT (user_id, cashier_id, date_shift) DO UPDATE
                    SET user_id = $3, active_status = 'начата'
                ''', date_obj, cashier_id, user_id)

        elif log_prefix == 'Сменщик':
            if active_shift:
                await conn.execute('''
                    UPDATE shift 
                    SET active_status = 'закончена'
                    WHERE id = $1
                ''', active_shift)

                await conn.execute('''
                    INSERT INTO shift (date_shift, cashier_id, user_id, active_status)
                    VALUES ($1, $2, $3, 'начата')
                    ON CONFLICT (user_id, cashier_id, date_shift) DO UPDATE
                    SET user_id = $3, active_status = 'начата'
                ''', date_obj, cashier_id, user_id)


async def add_control_of_delay(date: str, point: str, message: str, user_id: int):
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            'SELECT 1 FROM control_of_delays WHERE date = $1',
            date
        )
        
        if exists:
            current_value = await conn.fetchval(
                f'SELECT "{point}" FROM control_of_delays WHERE date = $1',
                date
            )

            if current_value:
                message_to_set = f'{current_value}\n{message}'
            else:
                message_to_set = message

            await conn.execute(f'''
                UPDATE control_of_delays 
                SET "{point}" = $1 
                WHERE date = $2
            ''', message_to_set, date)
        else:
            await conn.execute(f'''
                INSERT INTO control_of_delays (date, "{point}") 
                VALUES ($1, $2)
            ''', date, message)

async def change_grafic(date: str, point: str, user: str):
    async with pool.acquire() as conn:
        async with conn.transaction():
            columns = await conn.fetch('''
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'grafic'
            ''')

            if isinstance(date, str):
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            else:
                date_obj = date

            for col in columns:
                if col['data_type'] in ['text', 'character varying', 'integer', 'bigint']:
                    query = f'SELECT "{col["column_name"]}" FROM grafic WHERE "{col["column_name"]}"::TEXT = $1 AND date = $2 LIMIT 1'
                    result = await conn.fetchval(query, point, date_obj)
                    if result:
                        update_point = 'UPDATE grafic SET "{}" = $1 WHERE date = $2'.format(col['column_name'])
                        await conn.execute(update_point, None, date_obj)

            update_point = 'UPDATE grafic SET "{}" = $1 WHERE date = $2'.format(user)
            await conn.execute(update_point, point, date_obj)

async def get_grafic_by_date(date: str) -> Dict[str, str]:
    async with pool.acquire() as conn:
        if isinstance(date, str):
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            date_obj = date

        columns = await conn.fetch('''
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'grafic'
            AND table_schema = 'public'
            AND column_name != 'date'
            AND column_name != 'id'
        ''')

        row = await conn.fetchrow(
            'SELECT * FROM grafic WHERE date = $1',
            date_obj
        )

        if row:
            return {
                k: v for k, v in row.items() 
                if k not in ('id', 'date') and v not in (None, '')
            }
        return {}
    
async def get_point(date: str, user: str, work_username: str, type: str):
    async with pool.acquire() as conn:
        async with conn.transaction():
            if type == 'i':
                get_point = 'SELECT "{}" FROM grafic WHERE date = $1'.format(work_username)
                point = await conn.fetchval(get_point, date)
                return point
            elif type == 'me':
                get_point = 'SELECT "{}" FROM grafic WHERE date = $1'.format(user)
                point = await conn.fetchval(get_point, date)
                return point
            elif type == 'ch':
                get_first_point = 'SELECT "{}" FROM grafic WHERE date = $1'.format(work_username)
                first_point = await conn.fetchval(get_first_point, date)

                get_second_point = 'SELECT "{}" FROM grafic WHERE date = $1'.format(user)
                second_point = await conn.fetchval(get_second_point, date)

                return first_point, second_point

async def changes_in_grafic(date: str, user: str, change_user: str, type: str):
    async with pool.acquire() as conn:
        async with conn.transaction():
            if type == 'i':
                get_point = 'SELECT "{}" FROM grafic WHERE date = $1'.format(change_user)
                point = await conn.fetchval(get_point, date)

                update_change_worker = 'UPDATE grafic SET "{}" = $1 WHERE date = $2'.format(change_user)
                await conn.execute(update_change_worker, None, date)

                update_worker = 'UPDATE grafic SET "{}" = $1 WHERE date = $2'.format(user)
                await conn.execute(update_worker, point, date)

                user_id = await get_id(user)
                if user_id and point:
                    cashier_id = await get_cashier_id(point)
                    update_shift = 'UPDATE shift SET user_id = $1 WHERE date_shift = $2 AND cashier_id = $3'
                    await conn.execute(update_shift, user_id, date, cashier_id)

            elif type == 'me':
                get_point = 'SELECT "{}" FROM grafic WHERE date = $1'.format(user)
                point = await conn.fetchval(get_point, date)

                update_change_worker = 'UPDATE grafic SET "{}" = $1 WHERE date = $2'.format(user)
                await conn.execute(update_change_worker, None, date)

                update_worker = 'UPDATE grafic SET "{}" = $1 WHERE date = $2'.format(change_user)
                await conn.execute(update_worker, point, date)

                change_user_id = await get_id(change_user)
                if change_user_id and point:
                    cashier_id = await get_cashier_id(point)
                    update_shift = 'UPDATE shift SET user_id = $1 WHERE date_shift = $2 AND cashier_id = $3'
                    await conn.execute(update_shift, change_user_id, date,cashier_id)

            elif type == 'change':
                get_first_point = 'SELECT "{}" FROM grafic WHERE date = $1'.format(change_user)
                first_point = await conn.fetchval(get_first_point, date)

                get_second_point = 'SELECT "{}" FROM grafic WHERE date = $1'.format(user)
                second_point = await conn.fetchval(get_second_point, date)

                update_first_worker = 'UPDATE grafic SET "{}" = $1 WHERE date = $2'.format(user)
                await conn.execute(update_first_worker, first_point, date)

                update_second_worker = 'UPDATE grafic SET "{}" = $1 WHERE date = $2'.format(change_user)
                await conn.execute(update_second_worker, second_point, date)

                user_id = await get_id(user)
                change_user_id = await get_id(change_user)
                
                if user_id and first_point:
                    first_cashier_id = await get_cashier_id(first_point)
                    update_first_shift = 'UPDATE shift SET user_id = $1 WHERE date_shift = $2 AND cashier_id = $3'
                    await conn.execute(update_first_shift, user_id, date, first_cashier_id)

                if change_user_id and second_point:
                    second_cashier_id = await get_cashier_id(second_point)
                    update_second_shift = 'UPDATE shift SET user_id = $1 WHERE date_shift = $2 AND cashier_id = $3'
                    await conn.execute(update_second_shift, change_user_id, date, second_cashier_id)


async def add_log_pref(user_id: int, work_username: str, log_pref: str, date: str):
    async with pool.acquire() as conn:
        time_send = datetime.now().strftime('%H:%M')
        await conn.execute('''
            INSERT INTO locations (user_id, username, log_prefix, date, time_send)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, time_send) DO UPDATE SET
                username = EXCLUDED.username,
                log_prefix = EXCLUDED.log_prefix
        ''', user_id, work_username, log_pref, date, time_send)


async def edit_location(user_id: int, date: str, point: str, latitude: float, longitude: float, time_send: str):
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE locations 
            SET point = $1, latitude = $2, longitude = $3, time_send = $4
            WHERE user_id = $5 AND date = $6
        ''', point, latitude, longitude, time_send, user_id, date)


async def edit_point(user_id: int, log_prefix: str, point: str):
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE locations 
            SET point = $1 
            WHERE user_id = $2 AND log_prefix = $3
        ''', point, user_id, log_prefix)


async def get_time_send(date: str, user_id: int) -> Optional[Tuple[str, str]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT log_prefix, time_send 
            FROM locations 
            WHERE date = $1 AND user_id = $2
        ''', date, user_id)
        return (row['log_prefix'], row['time_send']) if row else None


async def get_locations_by_date(date: str) -> List[Dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM locations WHERE date = $1', date)
        return [dict(row) for row in rows]


async def clear_locations_by_date(date: str):
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM locations WHERE date = $1', date)




async def employee_verification(user_id: int) -> bool: 
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT 1 FROM employee WHERE user_id = $1 AND active_status = $2', 
            user_id, 'active'
        )
        return row is not None
    
async def get_all_work_username():
    async with pool.acquire() as conn:
        columns = await conn.fetch('''
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'grafic'
            AND table_schema = 'public'
            AND column_name != 'date'
            AND column_name != 'id'
        ''')
        return [col['column_name'] for col in columns]

async def get_state_form(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT work_status FROM employee WHERE user_id = $1', 
            user_id
        )
        return row['work_status'] if row else None

async def get_id(full_name: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT user_id FROM employee WHERE full_name = $1', 
            full_name
        )
        return row['user_id'] if row else None

async def get_id_max(full_name: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT max_user_id FROM employee WHERE full_name = $1', 
            full_name
        )
        return row['user_id'] if row else None

async def get_username(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT name FROM employee WHERE user_id = $1', 
            user_id
        )
        return row['name'] if row else None

async def get_work_username(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT full_name FROM employee WHERE user_id = $1', 
            user_id
        )
        return row['full_name'] if row else None

async def get_admin(user_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT work_status FROM employee WHERE user_id = $1', 
            user_id
        )
        return row['work_status'] if row else None



def db_message():
    with sqlite3.connect(MESSAGES_DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                message_id INTEGER,
                location_messages TEXT,
                sent_messages TEXT
            )
        ''')
        conn.commit()


def edit_message(user_id: int, message_id: int):
    with sqlite3.connect(MESSAGES_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (user_id, message_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET message_id = excluded.message_id
        ''', (user_id, message_id))
        conn.commit()


def edit_location_messages(user_id: int, location_messages: List[int]):
    with sqlite3.connect(MESSAGES_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO messages (user_id, location_messages) VALUES (?, ?) '
            'ON CONFLICT(user_id) DO UPDATE SET location_messages = excluded.location_messages',
            (user_id, json.dumps(location_messages))
        )
        conn.commit()


def edit_sent_messages(user_id: int, sent_messages: List[int]):
    with sqlite3.connect(MESSAGES_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO messages (user_id, sent_messages) VALUES (?, ?) '
            'ON CONFLICT(user_id) DO UPDATE SET sent_messages = excluded.sent_messages',
            (user_id, json.dumps(sent_messages))
        )
        conn.commit()


def get_message_id(user_id: int) -> Optional[int]:
    with sqlite3.connect(MESSAGES_DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT message_id FROM messages WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return row['message_id'] if row else None


def get_location_messages(user_id: int) -> List[int]:
    with sqlite3.connect(MESSAGES_DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT location_messages FROM messages WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row and row['location_messages']:
            try:
                return json.loads(row['location_messages'])
            except (json.JSONDecodeError, TypeError):
                return []
        return []


def get_sent_messages(user_id: int) -> List[int]:
    with sqlite3.connect(MESSAGES_DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT sent_messages FROM messages WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row and row['sent_messages']:
            try:
                return json.loads(row['sent_messages'])
            except (json.JSONDecodeError, TypeError):
                return []
        return []