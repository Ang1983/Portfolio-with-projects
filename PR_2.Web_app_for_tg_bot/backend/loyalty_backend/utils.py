import hashlib
import hmac
import time
from urllib.parse import unquote
from django.conf import settings


def validate_init_data(init_data: str, token: str) -> bool:
    try:
        params = {}
        for part in init_data.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key] = value
        
        if 'hash' not in params:
            return False

        received_hash = params.pop('hash')

        data_check_string = '\n'.join(
            f"{k}={unquote(params[k])}" for k in sorted(params.keys())
        )

        secret_key = hmac.new(
            b"WebAppData",
            token.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(calculated_hash, received_hash)
        
    except Exception as e:
        print(f"Ошибка валидации initData: {e}")
        return False


def parse_init_data(init_data: str) -> dict:
    from urllib.parse import unquote
    import json
    
    params = {}
    for part in init_data.split('&'):
        if '=' in part:
            key, value = part.split('=', 1)
            params[key] = unquote(value)

    user_data = {}
    for key, value in params.items():
        if key.startswith('user['):
            user_key = key[5:-1]
            user_data[user_key] = value
        elif key in ['id', 'auth_date', 'first_name', 'last_name', 'username', 'language_code']:
            user_data[key] = value

    if 'user' in params:
        try:
            user_data.update(json.loads(params['user']))
        except:
            pass
    
    return user_data


def validate_auth_date(auth_date: str, max_age: int = 86400) -> bool:
    try:
        auth_timestamp = int(auth_date)
        current_timestamp = int(time.time())
        return current_timestamp - auth_timestamp <= max_age
    except:
        return False


def get_telegram_id_from_init_data(init_data: str) -> int:
    try:
        user_data = parse_init_data(init_data)
        telegram_id = user_data.get('id') or user_data.get('user_id')
        return int(telegram_id) if telegram_id else 0
    except Exception as e:
        print(f"Ошибка получения Telegram ID: {e}")
        return 0