# PR_2: Система лояльности (Telegram Mini App)

## Проблема
Сеть кофеен нуждается в системе лояльности для повышения retention клиентов и увеличения повторных продаж.

## Решение
Разрабатана системв лояльности на базе Telegram Mini App с функционалом:
- Регистрация клиентов через Telegram
- Накопление бонусов за покупки
- История транзакций и баланса
- Административная панель для управления клиентами и акциями

## Технологии
**Backend:**
- **Python 3.10+**
- **Django** - веб-фреймворк для REST API
- **PostgreSQL** - реляционная база данных

**Frontend:**
- **JavaScript**
- **HTML5 / CSS3**
- **Telegram Web App API** - интеграция с Telegram

**Инструменты:**
- **Git** - контроль версий
- **Postman** - тестирование API
- **Docker** - контейнеризация

## Структура проекта
```markdown
PR_2.Web_app_for_tg_bot/
── backend/
   ── loyalty_backend/
      ── views.py          # Эндпоинты
      ── models.py
      ── serializers.py
      ── admin.py          # Администрирование сайта
      ── urls.py           # Пути для api
   ── requirements.txt
── frontend/
   ── index.html           # Главная страница
   ── js 
      ── profiles          # Профили
         ── admin.js
         ── user.js
         ── employee.js
      ── auth.js           # Методы аутентификации
      ── main.js           # Основные методы, которые не проходят в профили
      ── coupon.js         # Методы для купонов
      ── qr_scaner.js
── READ.ME
```

## Статус разработки
На финальной стадии

Реализовано:
-	База данных PostgreSQL с миграциями
-	REST API для управления клиентами и транзакциями
-	Frontend для Telegram Mini App
-	Интеграция с Telegram Bot API
-	Деплой на сервер
-	Тестирование
  
В процессе:
- Отладка временного шлюза в синхронизации
- Интеграция с Wallet
