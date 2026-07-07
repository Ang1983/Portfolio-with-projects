from django.db import connection
from rest_framework import viewsets, status 
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import qrcode
from io import BytesIO
import base64
import json
import logging
import math
import random
import string
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from dateutil.relativedelta import relativedelta
from django.db import connection, transaction
import calendar
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from decimal import Decimal
import calendar

logger = logging.getLogger(__name__)

from .models import (
    Employee, Cashier, Shift, 
    LoyaltyCard, Drink, Syrup, 
    Coupon, Receipt, TimeScanQR, 
    PositionReceipt, Product, Grafic, 
    ProductsForPurchase, Milk, CheckList, CategoryProducts, Menu,
    Milk, MilkOrder, MilkOrderItem, Location, ControlOfDeleyas, CategoryMenu,
    MonthPreference, Expense, ExpenseCategory, ExpenseHistory, LotteryParticipant
)
from .serializers import (
    EmployeeSerializer, CashierSerializer, ShiftSerializer,
    LoyaltyCardSerializer, DrinkSerializer, SyrupSerializer,
    CouponSerializer, ReceiptSerializer, TimeScanQRSerializer,
    MilkSerializer, MilkOrderItemSerializer, MilkOrderSerializer,
    MilkOrderCreateSerializer,
    ExpenseCreateSerializer, 
    ExpenseListSerializer, 
    ExpenseCategorySerializer,
    CashierShortSerializer
)

from .optimizer import run_month_optimization

@api_view(['POST'])
@permission_classes([AllowAny])
def authenticate_user(request):
    tg_id = request.data.get('tg_id')
    messanger = request.data.get('messanger')

    if messanger == 'telegram':
        employee = Employee.objects.filter(user_id=tg_id).first()
        loyalty_card = LoyaltyCard.objects.filter(id=tg_id).first()
    elif messanger == 'max':
        employee = Employee.objects.filter(max_user_id=tg_id).first()
        loyalty_card = LoyaltyCard.objects.filter(max_id=tg_id).first()

    if employee:
        serializer = EmployeeSerializer(employee)

        activate_status = employee.active_status if employee.active_status else ''

        if activate_status == 'deactive':
            if loyalty_card:
                if loyalty_card.how_find == 'coupon' and loyalty_card.full_name == '-':
                    return Response({
                        'authenticated': False,
                        'profile_type': None
                    })
                
                serializer = LoyaltyCardSerializer(loyalty_card)

                return Response({
                    'authenticated': True,
                    'profile_type': 'user',
                    'user_data': serializer.data
                })

            return Response({
               'authenticated': False,
                'profile_type': None
            })

        else:
            status_lower = employee.work_status if employee.work_status else ''
        
            profile_type = 'admin' if status_lower in ['boss', 'admin'] else \
                          'smm' if status_lower == 'SMM' else 'employee'
        
            return Response({
                'authenticated': True,
                'profile_type': profile_type,
                'user_data': serializer.data
            })

    if loyalty_card:
        if loyalty_card.how_find == 'coupon' and loyalty_card.full_name == '-':
            return Response({
                'authenticated': False,
                'profile_type': None
            })
        else:
            serializer = LoyaltyCardSerializer(loyalty_card)
            return Response({
                'authenticated': True,
                'profile_type': 'user',
                'user_data': serializer.data
            })
    
    return Response({
        'authenticated': False,
        'profile_type': None
    })


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


class CashierViewSet(viewsets.ModelViewSet):
    queryset = Cashier.objects.all()
    serializer_class = CashierSerializer


class LoyaltyCardViewSet(viewsets.ModelViewSet):
    queryset = LoyaltyCard.objects.all()
    serializer_class = LoyaltyCardSerializer
    
    def create(self, request):
        full_name = request.data.get('full_name')
        tg_id = request.data.get('tg_id')
        messanger = request.data.get('messanger')
        how_find = request.data.get('how_find', 'social_media')
        card_status = request.data.get('status', 'active')
        birthday = request.data.get('birthday')
        university_percent = request.data.get('university_percent')
        
        if not full_name:
            return Response(
                {'error': 'Имя обязательно'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not how_find:
            return Response(
                {'error': 'Поле "Откуда узнали" обязательно'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if messanger == 'telegram':
                loyalty_card = LoyaltyCard.objects.get(id=tg_id)
            elif messanger == 'max':
                loyalty_card = LoyaltyCard.objects.get(max_id=tg_id)

            if loyalty_card.how_find == 'coupon':
                loyalty_card.full_name = full_name
                loyalty_card.birthday = birthday
                loyalty_card.bonuses = 0
                loyalty_card.university_percent = university_percent
                loyalty_card.save()
                
                logging.info(f"Карта обновлена: tg_id={tg_id}")
                serializer = self.get_serializer(loyalty_card)
                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(
                {'error': 'Карта лояльности уже зарегистрирована'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except LoyaltyCard.DoesNotExist:
            pass
        
        logging.info("Данные валидны, создаём карту...")

        if messanger == 'telegram':
            loyalty_card = LoyaltyCard.objects.create(
                id=tg_id,
                full_name=full_name,
                status=card_status,
                how_find=how_find,
                birthday=birthday,
                bonuses = 50,
                university_percent = university_percent,
                max_id=0
            )
        elif messanger == 'max':
            loyalty_card = LoyaltyCard.objects.create(
                max_id=tg_id,
                full_name=full_name,
                status=card_status,
                how_find=how_find,
                birthday=birthday,
                bonuses = 50,
                university_percent = university_percent
            )
        
        serializer = self.get_serializer(loyalty_card)
        logging.info("Карта создана:", serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DrinkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Drink.objects.all()
    serializer_class = DrinkSerializer


class SyrupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Syrup.objects.all()
    serializer_class = SyrupSerializer


class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    
    def create(self, request):
        tg_id = request.data.get('tg_id')
        messanger = request.data.get('messanger')
        drink_name = request.data.get('drink_name')
        syrup = request.data.get('syrup', 'no')

        if not tg_id:
            return Response(
                {'error': 'Не указан tg_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not drink_name:
            return Response(
                {'error': 'Не указано название напитка'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if messanger == 'telegram':
                coupon = Coupon.objects.create(
                    tg_id=tg_id,
                    drink=drink_name,
                    syrup=syrup if syrup != 'no' else None
                )
            elif messanger == 'max':
                coupon = Coupon.objects.create(
                    max_id=tg_id,
                    drink=drink_name,
                    syrup=syrup if syrup != 'no' else None
                )

            qr_data = {
                'type': 'coupon',
                'coupon_id': coupon.id,
                'messanger': messanger,
                'tg_id': tg_id,
                'drink_name': coupon.drink,
                'syrup': syrup
            }
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(qr_data, ensure_ascii=False))
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return Response({
                'coupon': CouponSerializer(coupon).data,
                'qr_code': f'data:image/png;base64,{img_str}'
            })
            
        except ObjectDoesNotExist:
            available_drinks = list(Drink.objects.values_list('name', flat=True))
            return Response(
                {
                    'error': f'Напиток "{drink_name}" не найден',
                    'available_drinks': available_drinks
                },
                status=status.HTTP_404_NOT_FOUND
            )
            
        except MultipleObjectsReturned:
            drinks = Drink.objects.filter(name__iexact=drink_name.strip())
            return Response(
                {
                    'error': f'Найдено несколько напитков с именем "{drink_name}"',
                    'matches': list(drinks.values('id', 'name', 'size'))
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            print(f"Ошибка создания купона: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class ReceiptViewSet(viewsets.ModelViewSet):
    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer
    
    def get_queryset(self):
        queryset = Receipt.objects.all()
        tg_id = self.request.query_params.get('tg_id')
        employee_tg_id = self.request.query_params.get('employee_tg_id')
        messanger = self.request.query_params.get('messanger')
        date = self.request.query_params.get('date')
        
        if tg_id:
            if messanger == 'telegram':
                loyalty_card = LoyaltyCard.objects.filter(id=tg_id).first()
                if loyalty_card:
                    queryset = queryset.filter(loyalty_card_id=loyalty_card)
            elif messanger == 'max':
                loyalty_card = LoyaltyCard.objects.filter(max_id=tg_id).first()
                if loyalty_card:
                    queryset = queryset.filter(loyalty_card_id=loyalty_card)
        
        if employee_tg_id:
            employee = Employee.objects.filter(user_id=employee_tg_id).first()
            if employee:
                shifts = Shift.objects.filter(user_id=employee)
                queryset = queryset.filter(shift_id__in=shifts)
        
        if date:
            queryset = queryset.filter(date_operation__date=date)
        
        return queryset.order_by('-date_operation')

def _handle_coupon_scan(data, employee_tg_id):
    try:
        tg_id = data.get('tg_id')
        messanger = data.get('messanger')
        name_drink = data.get('drink_name')
        drink_name = f'{name_drink} 250мл'
        syrup = data.get('syrup')

        if messanger == 'telegram':
            coupons = Coupon.objects.filter(tg_id=tg_id)
        elif messanger == 'max':
            coupons = Coupon.objects.filter(max_id=tg_id)

        if not coupons.exists():
            return Response({
                'success': False,
                'error': 'Купоны не найдены'
            }, status=404)

        if coupons.filter(used=True).exists():
            return Response({
                'success': False,
                'error': 'Вы уже воспользовались купоном. Больше купоны недоступны.'
            }, status=400)

        coupon = coupons.filter(used=False).first()
        
        if not coupon:
            return Response({
                'success': False,
                'error': 'Все купоны уже использованы'
            }, status=400)
        
        syrup_map = {
            'vanilla': 'Ваниль',
            'caramel': 'Карамель',
            'chocolate': 'Шоколад',
            'salt_caramel': 'Солёная карамель',
            'strawberry': 'Клубника',
            'no': 'Без сиропа'
        }
        syrup_name = syrup_map.get(syrup, syrup) if syrup else 'Без сиропа'

        coupon.used = True
        coupon.used_at = datetime.now(ZoneInfo('Europe/Moscow'))+timedelta(hours=3)
        coupon.save()

        try:
            employee = Employee.objects.get(user_id=employee_tg_id)
        except:
            employee = Employee.objects.get(max_user_id=employee_tg_id)

        current_shift = Shift.objects.filter(
            user_id=employee.user_id,
            date_shift=datetime.today().date(),
            active_status='начата'
        ).first()
        
        receipt = Receipt.objects.create(
            id = f'coupon:{tg_id}',
            shift_id=current_shift,
            cashier_id=current_shift.cashier_id_id if current_shift else None,
            type='coupon',
            date_operation = datetime.now(ZoneInfo('Europe/Moscow'))+timedelta(hours=3),
            amount=0,
            payment_method='coupon',
            bonus_add=0,
            bonus_remove=0
        )

        id_product = Product.objects.filter(name=drink_name).first()

        position_receipt = PositionReceipt.objects.create(
            id_receipt = receipt,
            id_product = id_product,
            product = drink_name,
            count = 1,
            price = 0,
            amount = 0,
            discount = 0,
            percent_bonus = 0,
            barcode = 0
        )

        if messanger == 'telegram':
            loyalty_card, created = LoyaltyCard.objects.get_or_create(
                id=tg_id,
                defaults={
                    'full_name': '-',
                    'status': 'active',
                    'how_find': 'coupon'
                }
            )
        elif messanger == 'max':
            loyalty_card, created = LoyaltyCard.objects.get_or_create(
                max_id=tg_id,
                defaults={
                    'full_name': '-',
                    'status': 'active',
                    'how_find': 'coupon'
                }
            )
    
        return Response({
            'success': True,
            'type': 'coupon',
            'drink_name': coupon.drink,
            'syrup_name': syrup_name,
            'receipt_id': receipt.id
        })
    
    except Coupon.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Купон не найден'
        }, status=404)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)


def _handle_loyalty_scan(data, employee_tg_id):
    try:
        bonus_amount = data.get('bonus_amount', 0)
        tg_id = data.get('tg_id')
        is_own_cup = data.get('is_own_cup')
        univercity_percent = data.get('univercity_percent')

        try:
            loyalty_card = LoyaltyCard.objects.get(id=tg_id)
            messanger = 'telegram'
        except:
            loyalty_card = LoyaltyCard.objects.get(max_id=tg_id)
            messanger = 'max'
        
        try:
            employee = Employee.objects.get(user_id=employee_tg_id)
        except:
            employee = Employee.objects.get(max_user_id=employee_tg_id)

        current_shift = Shift.objects.filter(
            user_id=employee.user_id,
            date_shift=datetime.today(),
            active_status='начата'
        ).first()
        
        if not current_shift:
            return Response({
                'success': False,
                'error': 'Смена не найдена'
            }, status=404)
        
        now = datetime.now(ZoneInfo('Europe/Moscow'))+timedelta(hours=3)

        time_threshold = now - timedelta(minutes=2)
        
        try:
            found_scan = TimeScanQR.objects.filter(
                loyalty_card=loyalty_card.id,
                shift_id=current_shift.id,
                cashier_id=current_shift.cashier_id_id,
                used_at=False,
                scan_time__gte=time_threshold
            ).latest('scan_time')

            return Response({
                'success': True,
                'type': 'loyalty_card',
                'card_name': loyalty_card.full_name,
                'university_percent': found_scan.comment_loyalty_card,
                'bonus_used': found_scan.bonus_used,
                'scan_id': found_scan.id,
                'message': 'Запись уже существует (защита от дублирования)'
            })

        except TimeScanQR.DoesNotExist:
            scan_record = TimeScanQR.objects.create(
                loyalty_card=loyalty_card.id,
                shift_id=current_shift.id,
                cashier_id=current_shift.cashier_id_id,
                scan_time=now,
                bonus_used=bonus_amount,
                used_at=False,
                comment_loyalty_card=univercity_percent,
                is_own_cup=is_own_cup * 30
            )

            if bonus_amount <= loyalty_card.bonuses:
                loyalty_card.bonuses -= bonus_amount
                loyalty_card.save()

    
                return Response({
                    'success': True,
                    'type': 'loyalty_card',
                    'card_name': loyalty_card.full_name,
                    'university_percent': univercity_percent,
                    'bonus_used': bonus_amount,
                    'scan_id': scan_record.id,
                    'message': 'Запись успешно создана'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Некорректное количество бонусов'
                }, status=404)

    except LoyaltyCard.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Карта лояльности не найдена'
        }, status=404)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)
    
def _handle_discount_scan(data, employee_tg_id):
    try:
        tg_id = data.get('tg_id')
        messanger = data.get('messanger')
        lottery_number = data.get('lottery_number')
        drink_name = data.get('drink_name')
        drink_category = data.get('drink_category', '')
        discount = data.get('discount', 30)

        try:
            loyalty_card = LoyaltyCard.objects.get(id=tg_id)
            messanger = 'telegram'
        except:
            loyalty_card = LoyaltyCard.objects.get(max_id=tg_id)
            messanger = 'max'

        try:
            employee = Employee.objects.get(user_id=employee_tg_id)
        except:
            employee = Employee.objects.get(max_user_id=employee_tg_id)

        current_shift = Shift.objects.filter(
            user_id=employee.user_id,
            date_shift=datetime.today(),
            active_status='начата'
        ).first()
        
        if not current_shift:
            return Response({
                'success': False,
                'error': 'Смена не найдена'
            }, status=404)
        
        now = datetime.now(ZoneInfo('Europe/Moscow')) + timedelta(hours=3)
        time_threshold = now - timedelta(minutes=2)

        try:
            found_scan = TimeScanQR.objects.filter(
                loyalty_card=loyalty_card.id,
                shift_id=current_shift.id,
                cashier_id=current_shift.cashier_id_id,
                used_at=False,
                scan_time__gte=time_threshold
            ).latest('scan_time')

            return Response({
                'success': True,
                'type': 'discount_30',
                'card_name': loyalty_card.full_name,
                'lottery_number': lottery_number,
                'drink_name': drink_name,
                'discount': discount,
                'scan_id': found_scan.id,
                'message': 'Запись уже существует (защита от дублирования)'
            })

        except TimeScanQR.DoesNotExist:
            try:
                participant = LotteryParticipant.objects.get(
                    tg_id=tg_id,
                    lottery_number=lottery_number,
                    notified=False
                )
            except LotteryParticipant.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Участник лотереи не найден или QR уже использован'
                }, status=404)

            scan_record = TimeScanQR.objects.create(
                loyalty_card=loyalty_card.id,
                shift_id=current_shift.id,
                cashier_id=current_shift.cashier_id_id,
                scan_time=now,
                bonus_used=0,
                used_at=False,
                comment_loyalty_card=30,
                is_own_cup=0
            )

            participant.notified = True
            participant.save()

            return Response({
                'success': True,
                'type': 'discount_30',
                'card_name': loyalty_card.full_name,
                'lottery_number': lottery_number,
                'drink_name': drink_name,
                'discount': discount,
                'scan_id': scan_record.id,
                'message': 'Скидка 30% применена успешно'
            })

    except LoyaltyCard.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Карта лояльности не найдена'
        }, status=404)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def scan_qr(request):
    qr_data = request.data.get('qr_data')
    employee_tg_id = request.data.get('employee_tg_id')
    
    try:
        data = json.loads(qr_data)
        qr_type = data.get('type')

        if qr_type == 'coupon':
            return _handle_coupon_scan(data, employee_tg_id)

        elif qr_type == 'loyalty_card':
            return _handle_loyalty_scan(data, employee_tg_id)
        
        elif qr_type == 'discount_30':
            return _handle_discount_scan(data, employee_tg_id)

        
        return Response({
            'success': False,
            'error': 'Неизвестный тип QR-кода'
        }, status=400)
    
    except Exception as e:
        print(f"Ошибка сканирования QR: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)


@api_view(['GET'])
@permission_classes([AllowAny])
def employee_daily_stats(request):
    employee_tg_id = request.query_params.get('tg_id')
    messanger = request.query_params.get('messanger')
    logger.info(messanger)
    date_str = request.query_params.get('date', timezone.now().date().isoformat())
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        if messanger == 'telegram':
            employee = Employee.objects.get(user_id=employee_tg_id)
            logger.info(employee)
            logger.info(employee.user_id)
        elif messanger == 'max':
            employee = Employee.objects.get(max_user_id=employee_tg_id)
            logger.info(employee)
            logger.info(employee.user_id)

        shifts = Shift.objects.filter(
            user_id=employee.user_id,
            date_shift=date
        )
        cashier_ids = shifts.values_list('cashier_id', flat=True).distinct()

        if shifts.exists():
            all_receipts = Receipt.objects.filter(
                cashier_id__in=cashier_ids,
                date_operation__date=date
            )

            total_for_day = all_receipts.aggregate(total=Sum('amount'))['total'] or 0

            receipts = Receipt.objects.filter(
                shift_id__in=shifts
            )

            receipts_cash = Receipt.objects.filter(shift_id__in=shifts, payment_method='наличные').aggregate(total=Sum('amount'))['total']
        
            total_revenue = receipts.aggregate(total=Sum('amount'))['total'] or 0
            coupon_count = receipts.filter(payment_method='coupon').count()
        
            return Response({
                'date': date_str,
                'shift_status': 'ok',
                'total_for_day': total_for_day,
                'total_revenue': float(total_revenue),
                'cash': receipts_cash,
                'receipt_count': receipts.count(),
                'coupon_count': coupon_count
            })
        
        else:
            return Response({
                'date': date_str,
                'shift_status': 'У вас нет смены или не начата смена сегодня'
            })

    except Exception as e:
        return Response({
            'error': str(e),
            'messanger': messanger,
            'tgId': employee_tg_id
        }, status=400)
    
@api_view(['GET'])
@permission_classes([AllowAny])
def employee_grafic(request):
    employee_tg_id = request.query_params.get('tg_id')
    messanger = request.query_params.get('messanger')
    
    try:
        if messanger == 'telegram':
            employee = Employee.objects.get(user_id=employee_tg_id)
        elif messanger == 'max':
            employee = Employee.objects.get(max_user_id=employee_tg_id)

        safe_column = employee.full_name.replace('"', '')
        
        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT date, "{safe_column}" FROM public.grafic ORDER BY date ASC'
            )
            grafic_data = cursor.fetchall()

        shift_data = []

        for date, point_value in grafic_data:
            if point_value is None:
                continue

            parts = point_value.split('_')
            point_code = parts[0]
            day_part = parts[1] if len(parts) > 1 else None
            
            try:
                cashier = Cashier.objects.get(short_name_point=point_code)
            except Cashier.DoesNotExist:
                continue

            start_time = cashier.start_work
            end_time = cashier.end_work

            if point_code == 'нк':
                if datetime.isoweekday(date) >= 6:
                    start_time = datetime.strptime('09:00', '%H:%M').time()
                    end_time = datetime.strptime('21:00', '%H:%M').time()
                else: 
                    start_time = datetime.strptime('08:30', '%H:%M').time()
                    end_time = datetime.strptime('20:30', '%H:%M').time()

            def time_to_minutes(t):
                return t.hour * 60 + t.minute
            
            def minutes_to_time(m):
                return f"{m // 60:02d}:{m % 60:02d}"
            
            start_min = time_to_minutes(start_time)
            end_min = time_to_minutes(end_time)
            duration = end_min - start_min
            half_min = start_min + duration // 2

            if day_part == 'у':
                shift_start = minutes_to_time(start_min)
                shift_end = minutes_to_time(half_min)
                shift_type = 'morning'
            elif day_part == 'в':
                shift_start = minutes_to_time(half_min)
                shift_end = minutes_to_time(end_min)
                shift_type = 'evening'
            else:
                shift_start = minutes_to_time(start_min)
                shift_end = minutes_to_time(end_min)
                shift_type = 'full'

            shift_data.append({
                'date': date.isoformat() if hasattr(date, 'isoformat') else str(date),
                'point_code': point_code,
                'day_part': day_part,
                'shift_start': shift_start,
                'shift_end': shift_end,
                'shift_type': shift_type,
                'cafe_hours': f'{start_time.strftime("%H:%M")} - {end_time.strftime("%H:%M")}',
                'address': cashier.adress 
            })

        return Response({
            'employee': {
                'name': employee.full_name,
                'tg_id': employee.user_id
            },
            'shifts': shift_data,
            'count': len(shift_data)
        }, status=200)

    except Employee.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=404)
    except Cashier.DoesNotExist:
        return Response({'error': f'Точка "{point_code}" не найдена'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def check_flyer_coupon_eligibility(request):
    tg_id = request.data.get('tg_id')
    messanger = request.data.get('messanger')
    
    if not tg_id:
        return Response(
            {'success': False, 'error': 'Не указан tg_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if messanger == 'telegram':
        has_used_coupon = Coupon.objects.filter(
            tg_id=tg_id,
            used=True
        ).exists()
    elif messanger == 'max':
        has_used_coupon = Coupon.objects.filter(
            max_id=tg_id,
            used=True
        ).exists()
    
    if has_used_coupon:
        if messanger == 'telegram':
            has_used_coupon = Coupon.objects.filter(
                tg_id=tg_id,
                used=True
            ).order_by('-used_at').first()
        elif messanger == 'max':
            has_used_coupon = Coupon.objects.filter(
                max_id=tg_id,
                used=True
            ).order_by('-used_at').first()
        
        return Response({
            'success': False,
            'already_used': True,
            'reason': 'used_before',
            'message': 'Вы уже воспользовались купоном с листовки',
            'used_drink': has_used_coupon.drink,
            'used_at': has_used_coupon.used_at.strftime('%d.%m.%Y') if has_used_coupon.used_at else None
        }, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'success': True,
        'message': 'Вы можете получить купон',
        'flyer_id': request.data.get('flyer_id')
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def history(request):
    tg_id = request.query_params.get('tg_id')
    messanger = request.query_params.get('messanger')
    
    if not tg_id:
        return Response({'error': 'Не указан tg_id'}, status=400)
    
    try:
        if messanger == 'telegram':
            loyalty_card = LoyaltyCard.objects.get(id=tg_id)
        elif messanger == 'max':
            loyalty_card = LoyaltyCard.objects.get(max_id=tg_id)
            logger.info(f'Найдена карта: {loyalty_card}')

        receipts = Receipt.objects.filter(
            loyalty_card_id=loyalty_card
        ).order_by('-date_operation')
        logger.info(f'Найдены чеки: {receipts}')

        receipts_data = []
        
        for receipt in receipts:
            positions = PositionReceipt.objects.filter(id_receipt=receipt)

            with connection.cursor() as cursor:
                short_name_point = Cashier.objects.get(id=receipt.cashier_id_id)

                student = loyalty_card.university_percent

                if student > 0:
                    cursor.execute(f'''
                        SELECT percent
                        FROM cashback_percent
                        WHERE name = 'Студенты'
                    ''')
                    bonus_percent = cursor.fetchall()
                else:
                    cursor.execute(f'''
                        SELECT percent
                        FROM cashback_percent
                        WHERE name = %s
                    ''', (short_name_point.short_name_point,))
                    bonus_percent = cursor.fetchall()

            receipts_data.append({
                'date_operation': receipt.date_operation.strftime('%d.%m.%Y %H:%M'),
                'bonus_percent': bonus_percent,
                'amount': float(receipt.amount),
                'type': receipt.type,
                'products': [
                    {
                        'name': pos.product,
                        'count': pos.count,
                        'price': float(pos.price)
                    }
                    for pos in positions
                ]
            })

        if loyalty_card.how_find == 'coupon':
            if messanger == 'telegram':
                coupons = Coupon.objects.filter(tg_id=tg_id).order_by('-used_at')
            elif messanger == 'max':
                coupons = Coupon.objects.filter(max_id=tg_id).order_by('-used_at')

            logger.info(f'Найден купон: {coupons}')
            
            for coupon in coupons:
                receipts_data.append({
                    'date_operation': coupon.used_at.strftime('%d.%m.%Y %H:%M') if coupon.used_at else coupon.created_at.strftime('%d.%m.%Y %H:%M'),
                    'type': 'купон',
                    'amount': 0.0,
                    'products': [
                        {
                            'name': f"{coupon.drink} 250мл",
                            'count': 1,
                            'price': 0.0,
                            'syrup': coupon.syrup if coupon.syrup else 'Без сиропа'
                        }
                    ]
                })
        
        return Response({
            'success': True,
            'receipts': receipts_data
        })
        
    except LoyaltyCard.DoesNotExist:
        return Response({'error': 'Карта лояльности не найдена'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def create_loyalty_qr(request):
    tg_id = request.data.get('tg_id')
    messanger = request.data.get('messanger')
    operation_type = request.data.get('type', 'loyalty_card')

    if not tg_id:
        return Response(
            {'error': 'Не указан tg_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        if messanger == 'telegram':
            loyalty_card = LoyaltyCard.objects.get(id=tg_id)
        elif messanger == 'max':
            loyalty_card = LoyaltyCard.objects.get(max_id=tg_id)

        qr_data = {
            'type': operation_type,
            'tg_id': tg_id,
            'name': loyalty_card.full_name,
            'bonus_avaliable': loyalty_card.bonuses,
            'univercity_percent': loyalty_card.university_percent
        }

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_data, ensure_ascii=False))
        qr.make(fit=True)
        img = qr.make_image(fill_color="#8B5CF6", back_color="white")

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return Response({
            'success': True,
            'qr_code': f'data:image/png;base64,{img_str}',
            'data': qr_data
        })
        
    except LoyaltyCard.DoesNotExist:
        return Response(
            {'error': 'Карта лояльности не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Ошибка генерации QR: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['POST'])
@permission_classes([AllowAny])
def added_bonuses(request):
    tg_id = request.data.get('tg_id')
    messanger = request.data.get('messanger')
    amount = request.data.get('amount')

    if messanger == 'telegram':
        loyalty_card = LoyaltyCard.objects.filter(id=tg_id).first()
    elif messanger == 'max':
        loyalty_card = LoyaltyCard.objects.filter(max_id=tg_id).first()

    loyalty_card.bonuses -= amount
    loyalty_card.save()

    return Response({
        'success': True,
        'new_balance': loyalty_card.bonuses,
        'message': f'Списано {amount} бонусов'
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_info(request):
    tg_id = request.query_params.get('tg_id')
    messanger = request.query_params.get('messanger')

    if messanger == 'telegram':
        loyalty_card = LoyaltyCard.objects.filter(id=tg_id).first()
    elif messanger == 'max':
        loyalty_card = LoyaltyCard.objects.filter(max_id=tg_id).first()

    serializer = LoyaltyCardSerializer(loyalty_card)
    return Response({
        'authenticated': True,
        'profile_type': 'user',
        'user_data': serializer.data
    })

def get_grafic_columns():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'grafic' 
            AND column_name != 'date' 
            AND column_name != 'id'
            AND column_name != 'Николай Тетрадзе'
            ORDER BY ordinal_position
        """)
        return [row[0] for row in cursor.fetchall()]


def get_month_dates(year, month):
    days_in_month = calendar.monthrange(year, month)[1]
    dates = []
    for day in range(1, days_in_month + 1):
        dates.append(datetime(year, month, day).date())
    return dates


@staff_member_required
def grafic_sheet_view(request):
    month_param = request.GET.get('month', '')
    
    if month_param:
        try:
            year, month = map(int, month_param.split('-'))
        except:
            today = datetime.now().date()
            next_month = today + relativedelta(months=1)
            year, month = next_month.year, next_month.month
    else:
        today = datetime.now().date()
        next_month = today + relativedelta(months=1)
        year, month = next_month.year, next_month.month

    dates = get_month_dates(year, month)
    db_columns = get_grafic_columns()

    grafic_dict = {}
    
    if db_columns:
        columns_sql = ', '.join([f'"{col}"' for col in db_columns])
        
        with connection.cursor() as cursor:
            cursor.execute(f'''
                SELECT date, {columns_sql} 
                FROM grafic 
                WHERE date IN %s
            ''', [tuple(dates)])

            col_names = [desc[0] for desc in cursor.description]

            for row in cursor.fetchall():
                row_dict = dict(zip(col_names, row))
                grafic_dict[row_dict['date']] = row_dict

    rows = []
    for date in dates:
        row = {'date': date}
        if date in grafic_dict:
            for col in db_columns:
                row[col] = grafic_dict[date].get(col, '') or ''
        else:
            for col in db_columns:
                row[col] = ''
        rows.append(row)

    month_name = datetime(year, month, 1).strftime('%B %Y')
    current_date = datetime(year, month, 1)
    prev_month = (current_date - relativedelta(months=1)).strftime('%Y-%m')
    next_month = (current_date + relativedelta(months=1)).strftime('%Y-%m')
    
    context = {
        'dates': dates,
        'db_columns': db_columns,
        'rows': rows,
        'title': f'График на {month_name}',
        'current_month': f'{year}-{month:02d}',
        'prev_month': prev_month,
        'next_month': next_month,
    }
    
    return render(request, 'admin/grafic_sheet.html', context)


def grafic_for_employee_sheet_view(request):
    month_param = request.GET.get('month', '')
    
    if month_param:
        try:
            year, month = map(int, month_param.split('-'))
        except:
            today = datetime.now().date()
            year, month = today.year, today.month
    else:
        today = datetime.now().date()
        year, month = today.year, today.month

    dates = get_month_dates(year, month)
    db_columns = get_grafic_columns()

    grafic_dict = {}
    
    if db_columns:
        columns_sql = ', '.join([f'"{col}"' for col in db_columns])
        
        with connection.cursor() as cursor:
            cursor.execute(f'''
                SELECT date, {columns_sql} 
                FROM grafic 
                WHERE date IN %s
            ''', [tuple(dates)])

            col_names = [desc[0] for desc in cursor.description]

            for row in cursor.fetchall():
                row_dict = dict(zip(col_names, row))
                grafic_dict[row_dict['date']] = row_dict

    rows = []
    for date in dates:
        row = {'date': date}
        if date in grafic_dict:
            for col in db_columns:
                row[col] = grafic_dict[date].get(col, '') or ''
        else:
            for col in db_columns:
                row[col] = ''
        rows.append(row)

    month_name = datetime(year, month, 1).strftime('%B %Y')
    current_date = datetime(year, month, 1)
    prev_month = (current_date - relativedelta(months=1)).strftime('%Y-%m')
    next_month = (current_date + relativedelta(months=1)).strftime('%Y-%m')
    
    context = {
        'dates': dates,
        'db_columns': db_columns,
        'rows': rows,
        'title': f'График на {month_name}',
        'current_month': f'{year}-{month:02d}',
        'prev_month': prev_month,
        'next_month': next_month,
    }
    
    return render(request, 'full_grafic_for_employee.html', context)

@staff_member_required
@csrf_exempt
def grafic_save_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        by_date = {}
        for item in data:
            date = item.get('date')
            column = item.get('column')
            value = item.get('value', '')
            
            if date not in by_date:
                by_date[date] = {}
            by_date[date][column] = value
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                for date, columns in by_date.items():
                    if not columns:
                        continue

                    cursor.execute('SELECT id FROM grafic WHERE date = %s', [date])
                    exists = cursor.fetchone()
                    
                    if exists:
                        set_clause = ', '.join([f'"{col}" = %s' for col in columns.keys()])
                        values = list(columns.values()) + [date]
                        cursor.execute(
                            f'UPDATE grafic SET {set_clause} WHERE date = %s',
                            values
                        )
                    else:
                        all_columns = ['date'] + list(columns.keys())
                        placeholders = ', '.join(['%s'] * len(all_columns))
                        values = [date] + list(columns.values())
                        
                        col_names = ', '.join([f'"{c}"' for c in all_columns])
                        cursor.execute(
                            f'INSERT INTO grafic ({col_names}) VALUES ({placeholders})',
                            values
                        )
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Сохранено {len(by_date)} дат ({len(data)} ячеек)'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=400)

#Молоко#

@api_view(['GET'])
def api_get_milk_products(request):
    try:
        milk_products = Milk.objects.all()
        serializer = MilkSerializer(milk_products, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
        })
    except Exception as e:
        return Response({
            'error': str(e)
        })


@api_view(['GET'])
def api_get_my_orders(request):
    try:
        tg_id = request.query_params.get('tg_id')
        messanger = request.query_params.get('messanger')
        
        if not tg_id:
            return Response({
                'status': 'error',
                'message': 'Требуется tg_id пользователя'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if messanger == 'telegram':
            employee = Employee.objects.get(user_id=tg_id)
        elif messanger == 'max':
            employee = Employee.objects.get(max_user_id=tg_id)

        date = datetime.now().date()
        
        try:
            shift = Shift.objects.filter(user_id=employee.user_id, date_shift=date).first()
        except Shift.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Смена на сегодня не найдена'
            }, status=status.HTTP_404_NOT_FOUND)

        cashier = get_object_or_404(Cashier, id=shift.cashier_id_id)

        orders = MilkOrder.objects.filter(
            cashier=cashier.short_name_point
        ).prefetch_related('items__milk').order_by('-created_at')
        
        serializer = MilkOrderSerializer(orders, many=True)
        
        return Response({
            'status': 'success',
            'data': serializer.data,
            'count': len(orders)
        })
        
    except Employee.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Сотрудник не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.info(f'Ошибка: {e}')
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def api_get_order_detail(request, order_id):
    try:
        employee = request.data.get('tg_id')
        messanger = request.data.get('messanger')
        if messanger == 'max':
            employee = Employee.objects.get(max_user_id=employee)
            employee = employee.user_id

        date = datetime.now().date()
        try:
            shift = Shift.objects.get(user_id=employee, date_shift=date)
        except Shift.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Смена на сегодня не найдена'
            })
        cashier = Cashier.objects.get(id=shift.cashier_id_id)
        order = get_object_or_404(
            MilkOrder.objects.prefetch_related('items__milk4'),
            id=order_id,
            cashier=cashier.short_name_point
        )
        
        serializer = MilkOrderSerializer(order)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'error': str(e)
        })


@api_view(['POST'])
@transaction.atomic
def api_create_order(request):
    try:
        employee = request.data.get('tg_id')
        messanger = request.data.get('messanger')
        if messanger == 'max':
            employee = Employee.objects.get(max_user_id=employee)
            employee = employee.user_id
        date = datetime.now().date()

        try:
            shift = Shift.objects.get(user_id=employee, date_shift=date)
        except Shift.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Смена на сегодня не найдена'
            })
        
        cashier = Cashier.objects.get(id=shift.cashier_id_id)
        
        if not employee:
            return Response({
                'status': 'error',
                'message': 'Требуется tg_id пользователя'
            })
        

        items = request.data.get('items', [])
        comment = request.data.get('comment', '')
        
        if not items:
            return Response({
                'status': 'error',
                'message': 'Добавьте хотя бы один товар'
            })

        amount = 0
        for item_data in items:
            milk_id = item_data.get('milk_id')
            try:
                milk_obj = Milk.objects.get(id=milk_id)
                milk_price = milk_obj.count
                quantity = item_data.get('quantity')

                amount += milk_price*quantity
            except:
                return Response({
                    'status': 'error',
                    'message': 'Не найден товар'
                })
            
        if amount < 5000:
            return Response({
                    'status': 'error',
                    'message': 'Сумма заказа меньше 5000, добавьте еще'
                })

        order_data = {
            'cashier': cashier.short_name_point,
            'cashier_address': cashier.adress,
            'status': 'pending',
            'comment': comment,
            'items': items
        }
        
        serializer = MilkOrderCreateSerializer(data=order_data)
        
        if serializer.is_valid():
            order = serializer.save()
            
            return Response({
                'status': 'success',
                'message': 'Заказ успешно создан',
                'data': {
                    'order_id': order.id,
                    'items': MilkOrderItemSerializer(order.items.all(), many=True).data
                }
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Ошибка валидации',
                'errors': serializer.errors
            })
        
    except Employee.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Сотрудник не найден'
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        })


@api_view(['POST'])
@transaction.atomic
def api_cancel_order(request):
    try:
        order_id = request.data.get('order_id')

        order = get_object_or_404(
            MilkOrder,
            id=order_id,
            status='pending'
        )
        
        order.status = 'cancelled'
        order.save()
        
        serializer = MilkOrderSerializer(order)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
        
    except MilkOrder.DoesNotExist:
        return Response({
            'error': 'Заказ не найден или уже обработан'
        })
    except Exception as e:
        return Response({
            'error': str(e)
        })
    
@api_view(['POST'])
@transaction.atomic
def api_complete_order(request):
    try:
        order_id = request.data.get('order_id')

        order = get_object_or_404(
            MilkOrder,
            id=order_id,
            status='confirmed'
        )
        
        order.status = 'completed'
        order.save()
        
        serializer = MilkOrderSerializer(order)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
        
    except MilkOrder.DoesNotExist:
        return Response({
            'error': 'Заказ не найден'
        })
    except Exception as e:
        return Response({
            'error': str(e)
        })
    

@api_view(['POST'])
@transaction.atomic
def api_problem_order(request):
    try:
        order_id = request.data.get('order_id')
        comment = request.data.get('comment')
        items_data = request.data.get('items')

        for item_data in items_data:            
            product_id = item_data.get('product_id')
            actual_qty = item_data.get('actual_quantity')

            milk_obj = Milk.objects.get(id=product_id)
            
            order_item = get_object_or_404(
                MilkOrderItem, 
                order_id=order_id,
                milk=milk_obj.name_product
            )

            order_item.quantity = actual_qty
            order_item.save()

        order = get_object_or_404(MilkOrder, id=order_id)
        order.status = 'problem'
        order.comment = comment
        order.save()

        return Response({
            'status': 'success',
            'message': 'Информация сохранена',
            'data': {
                'order_id': order.id,
                'status': order.status,
            }
        })

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)
    

@api_view(['GET'])
def api_admin_get_all_orders(request):
    try:
        status_filter = request.query_params.getlist('status')
        
        orders = MilkOrder.objects.select_related('cashier').prefetch_related('items__milk').all()

        if status_filter:
            orders = orders.filter(status__in=status_filter)

        orders = orders.order_by('-created_at')
        
        serializer = MilkOrderSerializer(orders, many=True)

        stats = {
            'total': MilkOrder.objects.count(),
            'pending': MilkOrder.objects.filter(status='pending').count(),
            'confirmed': MilkOrder.objects.filter(status='confirmed').count(),
            'completed': MilkOrder.objects.filter(status='completed').count(),
            'cancelled': MilkOrder.objects.filter(status='cancelled').count(),
        }

        return Response({
            'status': 'success',
            'data': serializer.data,
            'stats': stats
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def api_admin_update_order_status(request, order_id):
    try:
        order = MilkOrder.objects.get(id=order_id)
        
        new_status = request.data.get('status')
        
        if new_status not in ['pending', 'confirmed', 'completed', 'cancelled']:
            return Response({
                'status': 'error',
                'message': 'Неверный статус'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = order.status
        order.status = new_status
        order.save()
        
        serializer = MilkOrderSerializer(order)

        return Response({
            'status': 'success',
            'message': f'Статус заказа изменён на {new_status}',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except MilkOrder.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Заказ не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@transaction.atomic
def api_admin_bulk_update_status(request):
    try:
        order_ids = request.data.get('order_ids', [])
        new_status = request.data.get('status')
        
        if not order_ids:
            return Response({
                'error': 'Не указаны заказы'
            })
        
        if new_status not in ['pending', 'confirmed', 'completed', 'cancelled']:
            return Response({
                'error': 'Неверный статус'
            })
        
        count = MilkOrder.objects.filter(id__in=order_ids).update(status=new_status)
        
        return Response({
            'success': True,
            'data': {
                'updated_count': count,
                'new_status': new_status
            }
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        })


@api_view(['GET'])
def api_admin_get_statistics(request):
    try:
        stats = {
            'total_orders': MilkOrder.objects.count(),
            'by_status': {
                'pending': MilkOrder.objects.filter(status='pending').count(),
                'confirmed': MilkOrder.objects.filter(status='confirmed').count(),
                'completed': MilkOrder.objects.filter(status='completed').count(),
                'problem': MilkOrder.objects.filter(status='problem').count(),
                'cancelled': MilkOrder.objects.filter(status='cancelled').count(),
            },
            'total_items_ordered': MilkOrderItem.objects.count(),
        }

        employee_stats = Employee.objects.filter(
            milk_orders__isnull=False
        ).annotate(
            total_orders=Count('milk_orders'),
            total_items=Count('milk_orders__items')
        ).values(
            'id', 'full_name', 'total_orders', 'total_items'
        )
        
        stats['by_employee'] = list(employee_stats)
        
        return Response({
            'success':True,
            'data': stats
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    




@api_view(['POST'])
@permission_classes([AllowAny])
def save_month_preferences(request):
    try:
        tg_id = request.data.get('tg_id')
        messenger = request.data.get('messanger')
        year = request.data.get('year')
        month = request.data.get('month')
        
        if not all([tg_id, year, month]):
            return Response({'error': 'Отсутствуют обязательные поля'}, status=400)

        if messenger == 'telegram':
            emp = Employee.objects.get(user_id=tg_id)
        elif messenger == 'max':
            emp = Employee.objects.get(max_user_id=tg_id)
        else:
            return Response({'error': 'Неверный мессенджер'}, status=400)

        pref, _ = MonthPreference.objects.update_or_create(
            employee=emp, year=year, month=month,
            defaults={
                'availability': request.data.get('availability', {}),
                'priority_points': request.data.get('priority_points', []),
                'blocked_points': request.data.get('blocked_points', [])
            }
        )
        return Response({'status': 'success', 'message': 'Пожелания сохранены'})
    except Employee.DoesNotExist:
        return Response({'error': 'Сотрудник не найден'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    

@api_view(['POST'])
@permission_classes([AllowAny])
def run_schedule_optimization(request):
    year = request.data.get('year')
    month = request.data.get('month')
    if not all([year, month]):
        return Response({'error': 'Укажите год и месяц'}, status=400)
    
    result = run_month_optimization(year, month)
    return Response(result)


# ==================== GEOLOCATION & SHIFT API ====================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    
    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))
    
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def get_employee_by_platform(tg_id, messenger):
    """Get employee by Telegram ID or MAX ID."""
    if messenger == 'telegram':
        return Employee.objects.filter(user_id=tg_id).first()
    elif messenger == 'max':
        return Employee.objects.filter(max_user_id=tg_id).first()
    return None


def normalize_column_name(text):
    """Convert text to valid column name."""
    return text.lower().replace(' ', '_').replace('-', '_').replace('.', '')


# ==================== API ENDPOINTS ====================

@api_view(['POST'])
def api_detect_point(request):
    """
    Detect closest cashier point from employee's geolocation.
    
    Request body:
    {
        "latitude": 55.7558,
        "longitude": 37.6173
    }
    """
    try:
        latitude = float(request.data.get('latitude'))
        longitude = float(request.data.get('longitude'))
        
        if not all([latitude, longitude]):
            return Response({
                'status': 'error',
                'message': 'Missing latitude or longitude'
            }, status=status.HTTP_400_BAD_REQUEST)

        cashiers = Cashier.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).values('id', 'short_name_point', 'latitude', 'longitude')
        
        if not cashiers:
            return Response({
                'status': 'error',
                'message': 'No cashier points configured with coordinates'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        points_with_distance = []
        for cashier in cashiers:
            distance = calculate_distance(
                latitude, longitude,
                float(cashier['latitude']),
                float(cashier['longitude'])
            )
            points_with_distance.append({
                'id': cashier['id'],
                'name': cashier['short_name_point'],
                'distance': distance,
                'distance_formatted': f"{distance:.2f} km"
            })

        points_with_distance.sort(key=lambda x: x['distance'])
        
        closest = points_with_distance[0]
        is_within_range = closest['distance'] <= 5.0
        
        return Response({
            'status': 'success',
            'data': {
                'closest_point': {
                    'id': closest['id'],
                    'name': closest['name'],
                    'distance': closest['distance_formatted']
                },
                'all_points': points_with_distance,
                'is_within_range': is_within_range,
                'user_location': {
                    'latitude': latitude,
                    'longitude': longitude
                }
            }
        })
        
    except ValueError as e:
        return Response({
            'status': 'error',
            'message': f'Invalid coordinates: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def api_start_shift(request):
    try:
        tg_id = request.data.get('tg_id')
        messenger = request.data.get('messenger')
        latitude = float(request.data.get('latitude'))
        longitude = float(request.data.get('longitude'))
        cashier_id = request.data.get('cashier_id')
        role = request.data.get('role', 'employee')

        if not all([tg_id, latitude, longitude, cashier_id]):
            return Response({
                'status': 'error',
                'message': 'Missing required data'
            }, status=status.HTTP_400_BAD_REQUEST)

        employee = get_employee_by_platform(tg_id, messenger)
        if not employee:
            return Response({
                'status': 'error',
                'message': f'Employee not found {tg_id}, {messenger}'
            }, status=status.HTTP_404_NOT_FOUND)

        cashier = Cashier.objects.filter(id=cashier_id).first()
        if not cashier:
            return Response({
                'status': 'error',
                'message': 'Cashier point not found'
            }, status=status.HTTP_404_NOT_FOUND)

        distance = 0
        if cashier.latitude and cashier.longitude:
            distance = calculate_distance(
                latitude, longitude,
                float(cashier.latitude),
                float(cashier.longitude)
            )

        date = (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%d')
        time_send = datetime.now().strftime('%H:%M')
        work_username = employee.full_name
        point_name = cashier.short_name_point

        if role == 'helper':
            log_prefix = 'Помощник'
            date_control = f'{date} ПОМОЩНИКИ'
        elif role == 'change':
            log_prefix = 'Сменщик'
            date_control = f'{date} СМЕНЩИКИ'
        else:
            log_prefix = 'Сотрудник'
            date_control = date

        shift = None
        
        with transaction.atomic():
            Location.objects.create(
                user_id=tg_id,
                username=work_username,
                log_prefix=log_prefix,
                point=point_name,
                latitude=latitude,
                longitude=longitude,
                time_send=time_send,
                date=date
            )

            notice_text = f'{log_prefix} {work_username} в {time_send}'
            column_name = normalize_column_name(point_name)
            
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE control_of_delays SET {column_name} = %s WHERE date = %s",
                    [notice_text, date_control]
                )

                if cursor.rowcount == 0:
                    cursor.execute(
                        f"INSERT INTO control_of_delays (date, {column_name}) VALUES (%s, %s)",
                        [date_control, notice_text]
                    )

            if log_prefix == 'Сотрудник':
                try:
                    shift = Shift.objects.filter(
                        date_shift=date,
                        cashier_id=cashier
                    ).first()
                except Shift.DoesNotExist: 
                    shift = Shift.objects.create(
                        date_shift=date,
                        cashier_id=cashier,
                        user_id=employee,
                        active_status='начата'
                    )

                    _update_grafic_column(point_name.split('_')[0], employee.full_name, date)

                    return Response({
                        'status': 'success',
                        'message': 'Смена начата успешно',
                        'data': {
                            'distance': f'{distance:.2f} km',
                            'point': point_name,
                            'role': log_prefix,
                            'time': time_send,
                            'shift_id': shift.id
                        }
                    })

                if shift.user_id == employee:
                    shift.active_status = 'начата'
                    shift.save()
                else:
                    shift = Shift.objects.filter(
                        date_shift=date,
                        cashier_id=cashier
                    ).filter(
                        Q(active_status__isnull=True) | 
                        Q(active_status='') |
                       ~Q(active_status='закончена')
                    ).first()
                    
                    if not shift:
                        shift = Shift.objects.create(
                            user_id=employee,
                            date_shift=date,
                            cashier_id=cashier,
                            active_status='начата'
                        )
                        _update_grafic_column(point_name.split('_')[0], employee.full_name, date)
                    else:
                        if shift.user_id:
                            try:
                                employee_first = Employee.objects.get(user_id=shift.user_id_id)
                                
                                with connection.cursor() as cursor:
                                    cursor.execute(
                                        f'UPDATE grafic SET "{employee_first.full_name}" = %s, "{employee.full_name}" = %s WHERE date = %s',
                                        ['', cashier.short_name_point, date]
                                    )
                            except Employee.DoesNotExist:
                                pass
                        
                        shift.user_id = employee
                        shift.active_status = 'начата'
                        shift.save()

            elif log_prefix == 'Помощник':
                shift = Shift.objects.create(
                    user_id=employee,
                    date_shift=date,
                    cashier_id=cashier,
                    active_status='начата'
                )

            elif log_prefix == 'Сменщик':
                shift_first = Shift.objects.filter(
                    cashier_id=cashier,
                    date_shift=date,
                    active_status='начата'
                ).first()

                if shift_first:
                    if shift_first.user_id:
                        try:
                            employee_first = Employee.objects.get(user_id=shift_first.user_id_id)
                            
                            with connection.cursor() as cursor:
                                cursor.execute(
                                    f'UPDATE grafic SET "{employee_first.full_name}" = %s, "{employee.full_name}" = %s WHERE date = %s',
                                    ['', cashier.short_name_point, date]
                                )
                        except Employee.DoesNotExist:
                            pass
                    
                    shift_first.active_status = 'закончена'
                    shift_first.save()

                shift = Shift.objects.create(
                    user_id=employee,
                    date_shift=date,
                    cashier_id=cashier,
                    active_status='начата'
                )
        
        return Response({
            'status': 'success',
            'message': 'Смена начата успешно',
            'data': {
                'distance': f'{distance:.2f} km',
                'point': point_name,
                'role': log_prefix,
                'time': time_send,
                'shift_id': shift.id if shift else None
            }
        })
        
    except ValueError as e:
        return Response({
            'status': 'error',
            'message': f'Invalid  {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Ошибка сервера: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
def _update_grafic_column(point_name, employee_name, date):
    if not point_name:
        return
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'grafic'
            AND table_schema = 'public'
            AND column_name != 'date'
            AND column_name != 'id'
        """)
        columns = [col[0] for col in cursor.fetchall()]

        target_column = None
        for col in columns:
            if col == point_name or col.lower() == point_name.lower():
                target_column = col
                break

        if target_column:
            cursor.execute(
                f'UPDATE grafic SET "{target_column}" = %s WHERE date = %s',
                ['', date]
            )

            cursor.execute(
                f'UPDATE grafic SET "{employee_name}" = %s WHERE date = %s',
                [point_name, date]
            )
    
@api_view(['POST'])
def upload_avatar(request):
    try:
        tg_id = request.data.get('tg_id')
        messanger = request.data.get('messanger')
        employee = request.data.get('employee')
        avatar = request.data.get('avatar')

        if not tg_id:
            return Response(
                {'error': 'Поле tg_id обязательно', 'code': 'missing_tg_id'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not avatar:
            return Response(
                {'error': 'Поле avatar обязательно', 'code': 'missing_avatar'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not avatar.startswith('data:image/'):
            return Response(
                {'error': 'Неверный формат изображения. Ожидается Base64 (data:image/...)', 'code': 'invalid_format'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(avatar) > 7 * 1024 * 1024:
            return Response(
                {'error': 'Размер изображения превышает 5MB', 'code': 'file_too_large'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if employee == 'yes':
                if messanger == 'telegram':
                    card = Employee.objects.get(user_id=tg_id)
                elif messanger == 'max':
                    card = Employee.objects.get(max_user_id=tg_id)
            else:
                if messanger == 'telegram':
                    card = LoyaltyCard.objects.get(tg_id=tg_id)
                elif messanger == 'max':
                    card = LoyaltyCard.objects.get(max_id=tg_id)
        except LoyaltyCard.DoesNotExist:
            return Response(
                {'error': 'Пользователь с таким tg_id не найден', 'code': 'user_not_found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        card.avatar = avatar
        card.save()

        return Response(
            {
                'status': 'success',
                'message': 'Аватар успешно загружен',
                'data': {
                    'tg_id': tg_id,
                    'avatar_url': avatar[:50] + '...'
                }
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Ошибка при загрузке аватара: {str(e)}')
        
        return Response(
            {'error': 'Внутренняя ошибка сервера', 'details': str(e), 'code': 'server_error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['GET'])
def get_menu(request):
    categories = CategoryMenu.objects.filter(used_in_menu=True)
    
    result = {}
    
    for category in categories:
        menu_positions = Menu.objects.filter(category=category.category)

        user_agent = request.META.get('HTTP_USER_AGENT', '')
        supports_webp = 'WebP' in user_agent

        category_items = {}
        for item in menu_positions:
            if item.photo:
                photo_url = request.build_absolute_uri(item.photo.url)
                if supports_webp and photo_url.endswith('.jpg'):
                    photo_url = photo_url[:-4] + '.webp'
            else:
                photo_url = None
            category_items[item.name] = {
                'photo': photo_url,
                'description': item.description
            }

        result[category.category] = category_items
    
    return Response(result)

### Расходы ###
def api_get_expense_matrix(request):
    month_param = request.query_params.get('month', timezone.now().strftime('%Y-%m'))
    
    try:
        year, month = map(int, month_param.split('-'))
    except ValueError:
        return Response({'error': 'Неверный формат даты'}, status=400)

    cashiers = Cashier.objects.filter(active=True).order_by('short_name_point')
    point_codes = [c.short_name_point for c in cashiers]

    categories = ExpenseCategory.objects.all().order_by('name')
    
    matrix_data = []

    for category in categories:
        expenses = Expense.objects.filter(
            category=category,
            created_at__year=year,
            created_at__month=month
        )
        
        grouped_by_date = {}
        category_total = Decimal('0.00')
        
        for exp in expenses:
            date_key = exp.created_at.strftime('%Y-%m-%d')
            point_code = exp.cashier
            
            if date_key not in grouped_by_date:
                grouped_by_date[date_key] = {code: Decimal('0.00') for code in point_codes}
                grouped_by_date[date_key]['date'] = date_key
            
            grouped_by_date[date_key][point_code] = exp.amount
            category_total += exp.amount

        sorted_dates = sorted(grouped_by_date.values(), key=lambda x: x['date'])
        matrix_data.append({
            'category_id': category.id,
            'category_name': category.name,
            'total': float(category_total),
            'dates': sorted_dates
        })

    return Response({
        'month': month_param,
        'points': point_codes,
        'categories': matrix_data
    })

@api_view(['POST'])
def api_update_expense_cell(request):
    category_id = request.data.get('category_id')
    point_code = request.data.get('point_code')
    date_str = request.data.get('date')
    amount_str = request.data.get('amount')
    
    if not all([category_id, point_code, date_str]):
        return Response({'error': 'Missing fields'}, status=400)
        
    try:
        category = ExpenseCategory.objects.get(id=category_id)
        cashier = Cashier.objects.get(short_name_point=point_code)
        new_amount = Decimal(amount_str) if amount_str else Decimal('0.00')

        expense, created = Expense.objects.get_or_create(
            category=category,
            cashier=cashier,
            created_at__date=date_str,
            defaults={'amount': new_amount}
        )

        expense = Expense.objects.filter(
            category=category,
            cashier=cashier,
            created_at__date=date_str
        ).first()
        
        old_amount = Decimal('0.00')
        if expense:
            old_amount = expense.amount
            expense.amount = new_amount
            expense.save()
        else:
            expense = Expense.objects.create(
                category=category,
                cashier=cashier,
                created_at=date_str,
                amount=new_amount,
                created_by=request.user.employee_profile
            )

        ExpenseHistory.objects.create(
            category_name=category.name,
            point_name=point_code,
            date=date_str,
            old_amount=old_amount,
            new_amount=new_amount,
            changed_by=request.user
        )
        
        return Response({'status': 'success', 'new_amount': str(new_amount)})
        
    except ExpenseCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=404)
    except Cashier.DoesNotExist:
        return Response({'error': 'Cashier not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    

#Лотерея#

@api_view(['POST'])
@permission_classes([AllowAny])
def check_discount_30_eligibility(request):
    """Проверка доступности купона на скидку 30%"""
    try:
        tg_id = request.data.get('tg_id')
        messanger = request.data.get('messanger')
        type = request.data.get('type')
        
        if not all([tg_id, type]):
            return Response({
                'success': False,
                'error': 'Недостаточно данных'
            }, status=400)

        if LotteryParticipant.objects.filter(tg_id=tg_id).exists():
            participant = LotteryParticipant.objects.get(tg_id=tg_id)
            return Response({
                'success': False,
                'already_used': True,
                'used_at': participant.created_at.strftime('%d.%m.%Y %H:%M')
            })
        
        return Response({
            'success': True,
            'type': type
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_discount_qr(request):
    """Генерация QR-кода для скидки 30% с лотереей"""
    try:
        tg_id = request.data.get('tg_id')
        messanger = request.data.get('messanger')
        drink_name = request.data.get('drink_name')
        drink_category = request.data.get('drink_category', '')
        
        print(f"Получены данные: tg_id={tg_id}, drink_name={drink_name}, messanger={messanger}")
        
        if not all([tg_id, drink_name]):
            return Response({
                'success': False,
                'error': 'Недостаточно данных'
            }, status=400)

        if LotteryParticipant.objects.filter(tg_id=tg_id).exists():
            return Response({
                'success': False,
                'error': 'Вы уже участвовали в акции'
            }, status=400)

        lottery_number = ''.join(random.choices(string.digits, k=8))
        
        while LotteryParticipant.objects.filter(lottery_number=lottery_number).exists():
            lottery_number = ''.join(random.choices(string.digits, k=8))

        participant = LotteryParticipant.objects.create(
            tg_id=tg_id,
            lottery_number=lottery_number
        )

        qr_data = {
            'type': 'discount_30',
            'tg_id': tg_id,
            'messanger': messanger,
            'lottery_number': lottery_number,
            'drink_name': drink_name,
            'drink_category': drink_category,
            'discount': 30
        }

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_data, ensure_ascii=False))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({
            'success': True,
            'qr_code': f'data:image/png;base64,{qr_code_base64}',
            'lottery_number': lottery_number,
            'drink_name': drink_name,
            'discount': 30
        })
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)
    

@api_view(['POST'])
@permission_classes([AllowAny])
def process_discount_qr(request):
    """Обработка QR-кода скидки бариста"""
    try:
        qr_data_str = request.data.get('qr_data')
        
        if not qr_data_str:
            return Response({
                'success': False,
                'error': 'Нет данных QR-кода'
            }, status=400)
        
        try:
            qr_data = json.loads(qr_data_str)
        except json.JSONDecodeError:
            return Response({
                'success': False,
                'error': 'Неверный формат QR-кода'
            }, status=400)
        
        if qr_data.get('type') != 'discount_30':
            return Response({
                'success': False,
                'error': 'Неверный тип QR-кода'
            }, status=400)
        
        lottery_number = qr_data.get('lottery_number')
        
        try:
            participant = LotteryParticipant.objects.get(lottery_number=lottery_number)
        except LotteryParticipant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Участник не найден'
            }, status=404)
        
        if participant.notified:
            return Response({
                'success': False,
                'error': 'QR-код уже был обработан'
            }, status=400)
        
        participant.notified = True
        participant.save()
        
        return Response({
            'success': True,
            'lottery_number': lottery_number,
            'drink_name': qr_data.get('drink_name'),
            'discount': 30,
            'full_name': participant.full_name,
            'message': f'Скидка 30% применена. Лотерейный номер: {lottery_number}'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_lottery_winner(request):
    """Проверка победителя лотереи"""
    try:
        lottery_number = request.data.get('lottery_number')
        
        if not lottery_number:
            return Response({
                'success': False,
                'error': 'Укажите номер лотереи'
            }, status=400)
        
        try:
            participant = LotteryParticipant.objects.get(lottery_number=lottery_number)
        except LotteryParticipant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Номер не найден'
            }, status=404)
        
        if participant.is_winner:
            return Response({
                'success': True,
                'is_winner': True,
                'prize': participant.prize or 'Приз',
                'full_name': participant.full_name,
                'lottery_number': lottery_number
            })
        else:
            return Response({
                'success': True,
                'is_winner': False,
                'message': 'К сожалению, вы не победили'
            })
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

