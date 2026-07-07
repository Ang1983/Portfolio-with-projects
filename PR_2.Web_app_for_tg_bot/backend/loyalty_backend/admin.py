from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection, transaction
from django.utils.html import format_html
from django.contrib import messages
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required

from datetime import datetime, timedelta
import json

from .models import (
    Employee, Cashier, Shift, Menu,
    LoyaltyCard, Drink, Syrup, Product, Grafic, 
    ProductsForPurchase, Milk, CheckList, CategoryProducts, Product, 
    Expense, ExpenseCategory, ExpenseHistory
)

@admin.register(CategoryProducts)
class CategoryProductsAdmin(admin.ModelAdmin):
    list_display = ('category', 'description')
    search_fields = ('category', 'description')
    ordering = ('category',)
    
    fieldsets = (
        ('Основное', {
            'fields': ('category',)
        }),
        ('Описание', {
            'fields': ('description',)
        }),
    )

@admin.register(ProductsForPurchase)
class ProductsForPurchaseAdmin(admin.ModelAdmin):
    list_display = ('name_product', 'category', 'unit', 'url')
    list_filter = ('category',)
    search_fields = ('name_product',)
    list_editable = ('unit',)
    
    fieldsets = (
        ('Основное', {
            'fields': ('name_product', 'category')
        }),
        ('Количество', {
            'fields': ('unit', 'url')
        })
    )
    
    def preview_url(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">Ссылка</a>', obj.url)
        return '—'
    preview_url.short_description = 'URL'

@admin.register(Drink)
class DrinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'size', 'preview_url')
    search_fields = ('name',)
    list_filter = ('size',)
    list_editable = ('size',)
    
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'size')
        }),
        ('Изображение', {
            'fields': ('url',),
        }),
    )
    
    def preview_url(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">Ссылка</a>', obj.url)
        return '—'
    preview_url.short_description = 'URL'

@admin.register(Syrup)
class SyrupAdmin(admin.ModelAdmin):
    list_display = ('name', 'preview_url')
    search_fields = ('name',)
    
    fieldsets = (
        ('Основное', {
            'fields': ('name',)
        }),
        ('Изображение', {
            'fields': ('url',),
        }),
    )
    
    def preview_url(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">🔗 Ссылка</a>', obj.url)
        return '—'
    preview_url.short_description = 'URL'

@admin.register(Milk)
class MilkAdmin(admin.ModelAdmin):
    list_display = ('name_product', 'count', 'unit')
    search_fields = ('name_product',)
    list_editable = ('count', 'unit')
    
    fieldsets = (
        ('Основное', {
            'fields': ('name_product', 'count')
        }),
        ('Количество', {
            'fields': ('unit',)
        }),
    )


@admin.register(CheckList)
class CheckListAdmin(admin.ModelAdmin):
    list_display = ('name_product', 'count', 'unit')
    search_fields = ('name_product',)
    list_editable = ('count', 'unit')
    
    fieldsets = (
        ('Основное', {
            'fields': ('id', 'name_product')
        }),
        ('Количество', {
            'fields': ('count', 'unit')
        }),
    )

def get_grafic_columns():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'grafic' 
            AND column_name != 'date'
            AND column_name != 'id'
            ORDER BY ordinal_position
        """)
        return [row[0] for row in cursor.fetchall()]


def add_employee_column(full_name):
    with connection.cursor() as cursor:
        cursor.execute(f'ALTER TABLE grafic ADD COLUMN IF NOT EXISTS "{full_name}" TEXT')


def remove_employee_column(column_name):
    with connection.cursor() as cursor:
        if column_name in ['id', 'date']:
            return None
        else:
            cursor.execute(f'ALTER TABLE grafic DROP COLUMN "{column_name}"')


def get_employee_columns_mapping():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'grafic' 
            AND column_name != 'date'
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cursor.fetchall()]

    mapping = {}
    for emp in Employee.objects.filter(work_status__in=['boss', 'admin', 'SMM', 'employee']):
        col_name = emp.grafic_column_name
        if col_name in columns:
            mapping[col_name] = emp.full_name
    
    return mapping

@admin.register(Grafic)
class GraficAdmin(admin.ModelAdmin):
    list_display = ('id', 'date')
    list_display_links = ('id', 'date')
    date_hierarchy = 'date'
    ordering = ('-date',)
    search_fields = ('date',)
    
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
    
    def has_add_permission(self, request):
        return False


class GraficSheetAdmin(admin.AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('grafic-sheet/', self.admin_view(self.grafic_sheet_view), name='grafic-sheet'),
            path('grafic-save/', self.admin_view(self.grafic_save_view), name='grafic-save'),
            path('grafic-sync-columns/', self.admin_view(self.grafic_sync_columns), name='grafic-sync-columns'),
        ]
        return custom_urls + urls
    
    def grafic_sheet_view(self, request):
        today = datetime.now().date()
        dates = [today + timedelta(days=i) for i in range(14)]

        employees = Employee.objects.filter(
            work_status__in=['boss', 'admin', 'SMM', 'employee']
        ).order_by('full_name')

        db_columns = get_grafic_columns()

        grafic_data = Grafic.objects.filter(date__in=dates)

        grafic_dict = {}
        for g in grafic_data:
            grafic_dict[g.date] = {}
            for col in db_columns:
                grafic_dict[g.date][col] = getattr(g, col, '')
        
        context = {
            'dates': dates,
            'employees': employees,
            'db_columns': db_columns,
            'grafic_dict': grafic_dict,
            'title': 'График смен',
            **self.each_context(request),
        }
        
        return render(request, 'admin/grafic_sheet.html', context)
    
    @csrf_exempt
    @transaction.atomic
    def grafic_save_view(self, request):
        if request.method == 'POST':
            data = json.loads(request.body)
            
            for item in data:
                date = item.get('date')
                column = item.get('column')
                value = item.get('value', '')
                
                grafic, created = Grafic.objects.get_or_create(date=date)
                setattr(grafic, column, value)
                grafic.save()
            
            return JsonResponse({'status': 'success', 'message': 'График сохранён'})
        
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)
    
    @transaction.atomic
    def grafic_sync_columns(self, request):
        if request.method == 'POST':
            db_columns = get_grafic_columns()
            active_employees = Employee.objects.filter(active_status = 'active')
            
            added = []
            removed = []

            for emp in active_employees:
                col_name = emp.full_name
                if col_name not in db_columns:
                    try:
                        add_employee_column(emp.full_name)
                        added.append(emp.full_name)
                    except Exception as e:
                        messages.error(request, f'Ошибка добавления {emp.full_name}: {str(e)}')

            db_columns = get_grafic_columns()

            for col in db_columns:
                found = False
                for emp in active_employees:
                    if emp.full_name == col:
                        found = True
                        break
                if not found:
                    try:
                        remove_employee_column(col)
                        removed.append(col)
                    except Exception as e:
                        messages.error(request, f'Ошибка удаления {col}: {str(e)}')
            
            messages.success(
                request, 
                f'Синхронизация завершена. Добавлено: {len(added)}, Удалено: {len(removed)}'
            )
            return redirect('admin:grafic-sheet')
        
        return redirect('admin:grafic-sheet')

grafic_admin = GraficSheetAdmin(name='grafic_admin')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'full_name', 'work_status', 'phone', 'date_start')
    list_filter = ('active_status', 'work_status')
    search_fields = ('full_name', 'name', 'phone', 'telegram')
    date_hierarchy = 'date_start'
    
    fieldsets = (
        ('Основное', {
            'fields': ('user_id', 'name', 'full_name', 'max_user_id')
        }),
        ('Контакты', {
            'fields': ('phone', 'telegram', 'birthday')
        }),
        ('Работа', {
            'fields': ('work_status', 'date_start', 'experience', 'active_status')
        }),
        ('Зарплата', {
            'fields': ('type_salary', 'rate', 'percent'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_as_employee', 'activate_as_admin', 'deactivate', 'sync_grafic_columns']
    
    @admin.action(description='Активировать Сотрудник')
    def activate_as_employee(self, request, queryset):
        queryset.update(active_status='active')
        self.message_user(request, f'Активировано {queryset.count()} сотрудников')
    
    @admin.action(description='Активировать Админ')
    def activate_as_admin(self, request, queryset):
        queryset.update(work_status='admin')
        self.message_user(request, f'Активировано {queryset.count()} админов')
    
    @admin.action(description='Деактивировать (уволить) сотрудника')
    def deactivate(self, request, queryset):
        queryset.update(active_status='deactive')
        self.message_user(request, f'Деактивировано {queryset.count()} сотрудников')
    
    @admin.action(description='Синхронизировать колонки графика с таблицей сотрудников')
    def sync_grafic_columns(self, request, queryset):
        db_columns = get_grafic_columns()
        active_employees = Employee.objects.filter(active_status = 'active').exclude(work_status='boss')
            
        added = []
        removed = []

        for emp in active_employees:
            col_name = emp.full_name
            if col_name not in db_columns:
                try:
                    add_employee_column(emp.full_name)
                    added.append(emp.full_name)
                except Exception as e:
                    messages.error(request, f'Ошибка добавления {emp.full_name}: {str(e)}')

        db_columns = get_grafic_columns()

        for col in db_columns:
            found = False
            for emp in active_employees:
                if emp.full_name == col:
                    found = True
                    break
            if not found:
                try:
                    remove_employee_column(col)
                    removed.append(col)
                except Exception as e:
                    messages.error(request, f'Ошибка удаления {col}: {str(e)}')
            
        messages.success(
            request, 
            f'Синхронизация завершена. Добавлено: {len(added)}, Удалено: {len(removed)}'
        )

def get_control_of_deleyas_columns():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'control_of_delays' 
            AND column_name != 'date'
            ORDER BY ordinal_position
        """)
        return [row[0] for row in cursor.fetchall()]



def get_control_of_deleyas_columns():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'control_of_delays' 
            AND column_name != 'date'
            ORDER BY ordinal_position
        """)
        return [row[0] for row in cursor.fetchall()]


def add_cashier_column(short_name):
    column_name = short_name.lower().replace(' ', '_').replace('-', '_').replace('.', '')
    with connection.cursor() as cursor:
        cursor.execute(f"""
            ALTER TABLE control_of_delays 
            ADD COLUMN "{column_name}" TEXT DEFAULT NULL
        """)


def remove_cashier_column(column_name):
    if column_name in ['id', 'date']:
        return
    with connection.cursor() as cursor:
        cursor.execute(f"""
            ALTER TABLE control_of_delays 
            DROP COLUMN IF EXISTS "{column_name}"
        """)


def normalize_column_name(text):
    return text.lower().replace(' ', '_').replace('-', '_').replace('.', '')


def get_control_of_deleyas_columns():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'control_of_delays' 
            AND column_name != 'date'
            ORDER BY ordinal_position
        """)
        return [row[0] for row in cursor.fetchall()]


def add_cashier_column(short_name):
    column_name = short_name.lower().replace(' ', '_').replace('-', '_').replace('.', '')
    with connection.cursor() as cursor:
        cursor.execute(f"""
            ALTER TABLE control_of_delays 
            ADD COLUMN "{column_name}" TEXT DEFAULT NULL
        """)


def remove_cashier_column(column_name):
    if column_name in ['id', 'date']:
        return
    with connection.cursor() as cursor:
        cursor.execute(f"""
            ALTER TABLE control_of_delays 
            DROP COLUMN IF EXISTS "{column_name}"
        """)


def normalize_column_name(text):
    return text.lower().replace(' ', '_').replace('-', '_').replace('.', '')


@admin.register(Cashier)
class CashierAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_name_point', 'latitude', 'longitude', 'has_coordinates')
    list_filter = ('latitude', 'longitude')
    search_fields = ('short_name_point',)
    
    fieldsets = (
        ('Основное', {
            'fields': ('id', 'adress', 'short_name_point', 'start_work', 'end_work', 'status')
        }),
        ('Геолокация', {
            'fields': ('latitude', 'longitude'),
            'description': 'Введите координаты вручную. Используйте Google Maps: найдите точку → кликните правой кнопкой → скопируйте координаты.'
        }),
    )
    
    actions = ['sync_control_columns']
    
    def has_coordinates(self, obj):
        if obj.latitude and obj.longitude:
            return "Да"
        return "Нет"
    has_coordinates.short_description = 'Координаты'
    
    @admin.action(description='Синхронизировать колонки control_of_deleyas с точками')
    def sync_control_columns(self, request, queryset):
        db_columns = get_control_of_deleyas_columns()
        active_cashiers = Cashier.objects.all()
        
        added = []
        removed = []

        for cashier in active_cashiers:
            col_name = normalize_column_name(cashier.short_name_point)
            if col_name not in db_columns:
                try:
                    add_cashier_column(cashier.short_name_point)
                    added.append(cashier.short_name_point)
                    self.message_user(
                        request, 
                        f'Добавлена колонка: {cashier.short_name_point}',
                        level=messages.SUCCESS
                    )
                except Exception as e:
                    self.message_user(
                        request, 
                        f'Ошибка добавления {cashier.short_name_point}: {str(e)}',
                        level=messages.ERROR
                    )
        
        db_columns = get_control_of_deleyas_columns()
        for col in db_columns:
            found = False
            for cashier in active_cashiers:
                if normalize_column_name(cashier.short_name_point) == col:
                    found = True
                    break
            if not found:
                try:
                    remove_cashier_column(col)
                    removed.append(col)
                    self.message_user(
                        request, 
                        f'Удалена колонка: {col}',
                        level=messages.WARNING
                    )
                except Exception as e:
                    self.message_user(
                        request, 
                        f'Ошибка удаления {col}: {str(e)}',
                        level=messages.ERROR
                    )
        
        if added or removed:
            self.message_user(
                request, 
                f'Синхронизация завершена. Добавлено: {len(added)}, Удалено: {len(removed)}',
                level=messages.SUCCESS
            )
        else:
            self.message_user(
                request, 
                'Все колонки уже синхронизированы',
                level=messages.INFO
            )
    
    def save_model(self, request, obj, form, change):
        try:
            with transaction.atomic():
                super().save_model(request, obj, form, change)

                if not change:
                    col_name = normalize_column_name(obj.short_name_point)
                    db_columns = get_control_of_deleyas_columns()
                    
                    if col_name not in db_columns:
                        add_cashier_column(obj.short_name_point)
                        self.message_user(
                            request, 
                            f'Добавлена колонка для точки: {obj.short_name_point}',
                            level=messages.SUCCESS
                        )
                        
        except Exception as e:
            self.message_user(
                request, 
                f'Ошибка сохранения: {str(e)}', 
                level=messages.ERROR
            )
            raise

@admin.register(Product)
class Product(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'url', 'barcode')
    list_filter = ('category',)
    fields = ('name', 'category', 'price', 'barcode', 'url')

    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.photo.url
            )
        return '—'
    photo_preview.short_description = 'Фото'

@admin.register(Menu)
class Menu(admin.ModelAdmin):
    list_display = ('name', 'category', 'photo', 'video', 'description')
    list_filter = ('category',)
    fields = ('name', 'category', 'description', 'photo', 'video')

    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.photo.url
            )
        return '—'
    photo_preview.short_description = 'Фото'

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['cashier', 'category', 'amount', 'created_at', 'created_by']
    list_filter = ['cashier', 'category', 'created_at']
    search_fields = ['comment']
    readonly_fields = ['created_at', 'created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ExpenseHistory)
class ExpenseHistoryAdmin(admin.ModelAdmin):
    list_display = ['changed_at', 'category_name', 'point_name', 'date', 'old_amount', 'new_amount', 'changed_by']
    list_filter = ['changed_at', 'category_name', 'point_name', 'changed_by']
    search_fields = ['category_name', 'point_name']
    readonly_fields = ['changed_at', 'category_name', 'point_name', 'date', 'old_amount', 'new_amount', 'changed_by']
    date_hierarchy = 'changed_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


class ExpenseMatrixAdminSite(admin.AdminSite):
    site_header = "Управление расходами"
    site_title = "Админ-панель расходов"
    index_title = "Панель управления"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'expense-matrix/',
                self.admin_view(self.expense_matrix_view),
                name='expense-matrix'
            ),
        ]
        return custom_urls + urls
    
    @staff_member_required
    def expense_matrix_view(self, request):
        context = {
            **self.each_context(request),
            'title': 'Матрица расходов',
            'current_month': timezone.now().strftime('%Y-%m'),
        }
        return render(request, 'admin/expense_matrix.html', context)


expense_admin_site = ExpenseMatrixAdminSite(name='expense_admin')

expense_admin_site.register(Expense, ExpenseAdmin)
expense_admin_site.register(ExpenseCategory, ExpenseCategoryAdmin)
expense_admin_site.register(ExpenseHistory, ExpenseHistoryAdmin)