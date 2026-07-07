from django.db import models 
import random

class Employee(models.Model):
    STATUS_CHOICES = [
        ('boss', 'Босс'),
        ('admin', 'Админ'),
        ('SMM', 'SMM'),
        ('employee', 'Сотрудник'),
    ]
    
    user_id = models.BigIntegerField(primary_key=True, verbose_name='ID сотрудника')
    name = models.CharField(max_length=100, verbose_name='Имя')
    full_name = models.CharField(max_length=100, verbose_name='ФИО', unique=True)
    birthday = models.DateField(verbose_name='День рождения')
    work_status = models.CharField(max_length=100, choices=STATUS_CHOICES, verbose_name='Должность')
    telegram = models.CharField(max_length=100, verbose_name='Телеграм ссылка')
    phone = models.CharField(max_length=100, verbose_name='Номер телефона')
    date_start = models.DateField(verbose_name='Дата начала работы')
    experience = models.CharField(max_length=100, verbose_name='Опыт был/не было')
    type_salary = models.CharField(max_length=100, verbose_name='Тип ставки')
    rate = models.BigIntegerField(verbose_name='Час ставка')
    percent = models.BigIntegerField(verbose_name='Процент')
    active_status = models.CharField(max_length=20, verbose_name='Активирование пользователя')
    max_user_id = models.BigIntegerField(default=0)
    avatar = models.TextField()
    
    @property
    def is_work(self):
        return self.work_status in ['boss', 'admin', 'SMM', 'employee']
    
    @property
    def is_active(self):
        return self.active_status in ['active', 'deactive']
    
    @property
    def grafic_column_name(self):
        translit = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
            'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
            'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch',
            'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
            'э': 'e', 'ю': 'yu', 'я': 'ya',
            ' ': '_', '.': '', ',': '',
        }
        name_lower = self.full_name.lower()
        result = ''
        for char in name_lower:
            result += translit.get(char, char)
        result = ''.join(c for c in result if c.isalnum() or c == '_')
        return result[:50]
    
    class Meta:
        db_table = 'employee'
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'


class Cashier(models.Model):
    id = models.BigIntegerField(primary_key=True, verbose_name='ID кассы')
    adress = models.CharField(max_length=100, verbose_name='Полный адрес', unique=True)
    status = models.CharField(max_length=100, verbose_name='Активирование кассы')
    created_at = models.DateTimeField()
    short_name_point = models.CharField(max_length=100, verbose_name='Краткое название точки', unique=True)
    start_work = models.TimeField(verbose_name='Во сколько открывается')
    end_work = models.TimeField(verbose_name='Во сколько закрывается')
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        help_text="Latitude (e.g., 55.7558)"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        help_text="Longitude (e.g., 37.6173)"
    )
    
    class Meta:
        db_table = 'cashier'
        verbose_name = 'Кассы'
        verbose_name_plural = 'Кассы'


class Shift(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(Employee, on_delete=models.PROTECT, db_column='user_id')
    cashier_id = models.ForeignKey(Cashier, on_delete=models.PROTECT, db_column='cashier_id')
    date_shift = models.DateField()
    active_status = models.CharField(max_length=100)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'cashier_id', 'date_shift'],
                name='shift_id_cashier'
            )
        ]
        db_table = 'shift'
        verbose_name = 'Смены'
        verbose_name_plural = 'Смены'


class LoyaltyCard(models.Model):
    HOW_FIND_CHOICES = [
        ('mai', 'МЭИ'),
        ('mtusy', 'МТУСИ'),
        ('yandex', 'Яндекс карты'),
        ('friend', 'Посоветовали друзья'),
        ('street', 'Проходил мимо'),
        ('social media', 'Соцсети'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    how_find = models.CharField(max_length=50, choices=HOW_FIND_CHOICES)
    birthday = models.DateField()
    bonuses = models.BigIntegerField(default=0)
    university_percent = models.IntegerField(default=0)
    max_id = models.BigIntegerField(default=0)
    avatar = models.TextField()
    
    def __str__(self):
        return f"{self.full_name}"
    
    class Meta:
        db_table = 'loyalty_card'
        verbose_name = 'Карты лояльности'
        verbose_name_plural = 'Карты лояльности'

class Product(models.Model):
    id = models.CharField(primary_key=True, verbose_name='ID товара')
    name = models.TextField(max_length=100, verbose_name='Наименование товара')
    category = models.TextField(max_length=100, verbose_name='Категория')
    url = models.ImageField(max_length=100, null=True, blank=True, verbose_name='Фото', upload_to='products/')
    price = models.IntegerField(verbose_name='Цена')
    barcode = models.BigIntegerField(verbose_name='Штрихкод (если есть)')

    class Meta:
        db_table = 'products'
        verbose_name = 'Товары'
        verbose_name_plural = 'Товары'

class Menu(models.Model):
    id = models.CharField(primary_key=True, verbose_name='')
    name = models.TextField(max_length=100, verbose_name='Наименование товара')
    category = models.TextField(max_length=100, verbose_name='Категория')
    photo = models.ImageField(max_length=100, null=True, blank=True, verbose_name='Фото', upload_to='products/')
    video = models.FileField(max_length=100, null=True, blank=True, verbose_name='Видео', upload_to='products/')
    description = models.CharField(max_length=100, null=True, verbose_name='описание напитка')

    class Meta:
        db_table = 'menu'
        verbose_name = 'Меню'
        verbose_name_plural = 'Меню'


class Receipt(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    
    id = models.CharField(max_length=100, primary_key=True)
    shift_id = models.ForeignKey(Shift, on_delete=models.PROTECT, null=True, db_column='shift_id')
    cashier_id = models.ForeignKey(Cashier, on_delete=models.PROTECT, null=True, db_column='cashier_id')
    loyalty_card_id = models.ForeignKey(LoyaltyCard, on_delete=models.PROTECT, null=True, db_column='loyalty_card_id')
    type = models.CharField(max_length=100)
    date_operation = models.DateTimeField(null=True, blank=True)
    amount = models.BigIntegerField()
    payment_method = models.CharField(max_length=100)
    bonus_add = models.BigIntegerField()
    bonus_remove = models.BigIntegerField()
    
    def __str__(self):
        return f"Receipt #{self.id}"
    
    class Meta:
        db_table = 'receipts'
        verbose_name = 'Чеки'
        verbose_name_plural = 'Чеки'

class PositionReceipt(models.Model):
    id_position = models.BigAutoField(primary_key=True)
    id_receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, db_column='id_receipt')
    id_product = models.ForeignKey(Product, on_delete=models.PROTECT, db_column='id_product')
    product = models.TextField()
    count = models.IntegerField()
    price = models.IntegerField()
    amount = models.IntegerField()
    discount = models.IntegerField()
    percent_bonus = models.IntegerField()
    barcode = models.BigIntegerField()

    class Meta:
        db_table = 'position_receipt'
        verbose_name = 'Чек по позициям'
        verbose_name_plural = 'Чек по позициям'


class GoogleSheetSalary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    week_start = models.DateField()
    week_end = models.DateField()
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    sheet_row_id = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ['employee', 'week_start']

class Drink(models.Model):
    name = models.CharField(max_length=100, verbose_name='Наименование')
    size = models.IntegerField(default=250, verbose_name='Объем напитка')
    url = models.ImageField(max_length=100, verbose_name='URL картинки', upload_to='products/')
    
    def __str__(self):
        return f"{self.name} {self.size}мл"
    
    class Meta:
        db_table = 'loyalty_backend_drink'
        verbose_name = 'Напитки по купону'
        verbose_name_plural = 'Напитки по купону'


class Syrup(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название сиропа')
    url = models.ImageField(max_length=100, verbose_name='URL картинки', upload_to='syrup/')
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'loyalty_backend_syrup'
        verbose_name = 'Сиропы'
        verbose_name_plural = 'Сиропы'

def generate_tg_id():
    return random.randint(0, 999999999999)

class Coupon(models.Model):
    SYRUP_CHOICES = [
        ('vanilla', 'Ваниль'),
        ('caramel', 'Карамель'),
        ('chocolate', 'Шоколад'),
        ('salt_caramel', 'Соленая карамель'),
        ('strawberry', 'Клубника'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    tg_id = models.BigIntegerField(unique=True, default=generate_tg_id)
    drink = models.CharField(max_length=100)
    syrup = models.CharField(max_length=50, choices=SYRUP_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    max_id = models.BigIntegerField(default=0)
    
    def __str__(self):
        return f"Coupon {self.id} - {self.drink}"
    
class TimeScanQR(models.Model):
    id = models.BigAutoField(primary_key=True)
    loyalty_card = models.BigIntegerField()
    shift_id = models.BigIntegerField()
    cashier_id = models.BigIntegerField()
    scan_time = models.DateTimeField()
    bonus_used = models.IntegerField(default=0)
    used_at = models.BooleanField(default=False)
    comment_loyalty_card = models.CharField()
    is_own_cup = models.IntegerField()
    
    class Meta:
        db_table = 'time_scan_qr'

class Grafic(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='ID')
    date = models.DateField(unique=True, verbose_name='Дата')

    class Meta:
        db_table = 'grafic'
        managed = False
        verbose_name = 'График'
        verbose_name_plural = 'График сотрудников'
    
    def __str__(self):
        return f"График на {self.date}"

class CategoryProducts(models.Model):
    category = models.CharField(max_length=100, verbose_name='Категория')
    description = models.CharField(verbose_name='Описание категории')

    def __str__(self):
        return self.category
    
    class Meta:
        db_table = 'category_products'
        verbose_name = 'Категории продуктов'
        verbose_name_plural = 'Категории продуктов'

class ProductsForPurchase(models.Model): 
    name_product = models.CharField(max_length=100, verbose_name='Наименование')
    category = models.ForeignKey(CategoryProducts, on_delete=models.PROTECT, null=True, db_column='category', verbose_name='Категория')
    count = models.IntegerField(verbose_name='Цена 1 позиции')
    unit = models.IntegerField(verbose_name='Количество в 1 позиции')
    url = models.CharField(max_length=100, verbose_name='URL')
    
    class Meta:
        db_table = 'products_for_purchase'
        verbose_name = 'Продукты'
        verbose_name_plural = 'Заказ продуктов'

class Milk(models.Model):
    name_product = models.CharField(max_length=100, verbose_name='Нименование', unique=True)
    count = models.IntegerField(verbose_name='Цена')
    unit = models.IntegerField(verbose_name='Количество в 1 позиции')
    
    class Meta:
        db_table = 'milk'
        verbose_name = 'Молоко'
        verbose_name_plural = 'Молоко'

class MilkOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'pending'),
        ('confirmed', 'confirmed'),
        ('completed', 'completed'),
        ('cancelled', 'cancelled'),
        ('problem', 'problem'),
    ]
    
    cashier = models.ForeignKey(
        Cashier, 
        to_field='short_name_point',
        on_delete=models.CASCADE, 
        verbose_name='Точка',
        related_name='milk_orders',
        db_column='cashier'
    )

    cashier_address = models.ForeignKey(
        Cashier, 
        to_field='adress',
        on_delete=models.CASCADE, 
        verbose_name='Адрес',
        related_name='milk_orders_address',
        db_column='cashier_address'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')
    
    class Meta:
        db_table = 'milk_order'
        verbose_name = 'Заказ молока'
        verbose_name_plural = 'Заказы молока'
        ordering = ('-created_at',)
    
    def __str__(self):
        return f'Заказ #{self.id} от {self.employee.full_name}'
    
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())


class MilkOrderItem(models.Model):
    order_id = models.ForeignKey(
        MilkOrder, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name='Заказ',
        db_column='order_id'
    )
    milk = models.ForeignKey(
        'Milk', 
        to_field='name_product',
        on_delete=models.CASCADE, 
        verbose_name='Молоко',
        db_column='milk'
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    
    class Meta:
        db_table = 'milk_order_item'
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
    
    def __str__(self):
        return f'{self.milk.name_product} - {self.quantity}'

class CheckList(models.Model):
    name_product = models.CharField(max_length=100, verbose_name='Наименование')
    count = models.IntegerField(verbose_name='Количество')
    unit = models.TextField(verbose_name='Единицы измерения')
    
    class Meta:
        db_table = 'check_list'
        verbose_name = 'Чек лист'
        verbose_name_plural = 'Чек лист'

class ControlOfDeleyas(models.Model):
    date = models.CharField(max_length=100, primary_key=True, help_text="Date in YYYY-MM-DD format")
    
    class Meta:
        db_table = 'control_of_delays'
        verbose_name = 'Контроль опозданий'
        verbose_name_plural = 'Контроль опозданий'
        managed = False 
    
    def __str__(self):
        return f"Control for {self.date}"


class Location(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.BigIntegerField(help_text="Telegram or MAX user ID")
    username = models.CharField(max_length=100, help_text="Employee full name")
    log_prefix = models.CharField(max_length=50, help_text="Role: Сотрудник/Сменщик/Помощник")
    point = models.CharField(max_length=100, null=True, blank=True, help_text="Cashier point name")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    time_send = models.CharField(max_length=10, help_text="Time in HH:MM format")
    date = models.CharField(max_length=20, help_text="Date in YYYY-MM-DD format")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'locations'
        verbose_name = 'Геолокация'
        verbose_name_plural = 'Геолокации'
        managed = False
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} - {self.date} {self.time_send}"


class CategoryMenu(models.Model):
    category = models.CharField(max_length=100)
    used_in_menu = models.BooleanField()

    class Meta:
        db_table = 'category_menu'
        verbose_name = 'Категории меню'
        verbose_name_plural = 'Категории меню'

class MonthPreference(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='month_prefs')
    year = models.IntegerField()
    month = models.IntegerField()
    availability = models.JSONField(default=dict)
    priority_points = models.JSONField(default=list)
    blocked_points = models.JSONField(default=list)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['employee', 'year', 'month']
        db_table = 'month_preference'
        verbose_name = 'Пожелания на месяц'
        verbose_name_plural = 'Пожелания на месяц'

class ExpenseCategory(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, verbose_name="Название статьи")

    class Meta:
        verbose_name = "Статья расходов"
        db_table = 'expense_category'
        verbose_name_plural = "Статьи расходов"
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    cashier = models.ForeignKey(
        Cashier, 
        on_delete=models.CASCADE, 
        to_field='short_name_point',
        db_column='cashier',
        related_name='expenses',
        verbose_name="Кофейня"
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        to_field='name',
        db_column='category',
        related_name='expenses',
        verbose_name="Статья расходов"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Сумма"
    )
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='created_by',
        to_field='full_name',
        verbose_name="Кто добавил"
    )
    
    class Meta:
        verbose_name = "Расход"
        db_table = 'expense_per_month'
        verbose_name_plural = "Расходы"
        ordering = ['-created_at']
        unique_together = ['cashier', 'category', 'created_at']

    def __str__(self):
        return f"{self.cashier.short_name_point} — {self.category.name}: {self.amount}"

class ExpenseHistory(models.Model):
    category_name = models.CharField(max_length=255)
    point_name = models.CharField(max_length=100)
    date = models.DateField()
    old_amount = models.DecimalField(max_digits=10, decimal_places=2)
    new_amount = models.DecimalField(max_digits=10, decimal_places=2)
    changed_by = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='expense_history')
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'expense_history'
        verbose_name = "История расходов"
        verbose_name_plural = "Истории расходов"

    def __str__(self):
        return f"{self.category_name} | {self.point_name} | {self.date} | {self.old_amount} -> {self.new_amount}"
    
class LotteryParticipant(models.Model):
    id = models.BigAutoField(primary_key=True)
    tg_id = models.BigIntegerField(unique=True)
    lottery_number = models.CharField(max_length=20, unique=True)
    is_winner = models.BooleanField(default=False)
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lottery_participants'
        verbose_name = 'Участник лотереи'
        verbose_name_plural = 'Участники лотереи'
