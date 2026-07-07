from django.urls import path 
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'employees', views.EmployeeViewSet)
router.register(r'loyalty-cards', views.LoyaltyCardViewSet)
router.register(r'drinks', views.DrinkViewSet)
router.register(r'cashiers', views.CashierViewSet)
router.register(r'syrups', views.SyrupViewSet)
router.register(r'coupons', views.CouponViewSet)
router.register(r'receipts', views.ReceiptViewSet)

urlpatterns = [
    path('authenticate/', views.authenticate_user),
    path('receipts/scan-qr/', views.scan_qr),
    path('history/', views.history),
    path('stats/employee-daily/', views.employee_daily_stats),
    path('coupons/flyer/check/', views.check_flyer_coupon_eligibility, name='check-flyer-coupon'),
    path('grafic/', views.employee_grafic),
    path('loyalty-cards/spend/', views.added_bonuses),
    path('loyalty-cards/user_info/', views.get_user_info),
    path('create-loyalty-qr/', views.create_loyalty_qr),

    path('milk/', views.api_get_milk_products, name='api-milk-products'),
    path('milk-orders/my/', views.api_get_my_orders, name='api-my-orders'),
    path('milk-orders/<int:order_id>/', views.api_get_order_detail, name='api-order-detail'),
    path('milk-orders/create/', views.api_create_order, name='api-create-order'),
    path('milk-orders/cancel/', views.api_cancel_order, name='api-cancel-order'),
    path('milk-orders/complete/', views.api_complete_order, name='api-cancel-order'),
    path('milk-orders/problem/', views.api_problem_order, name='api-cancel-order'),

    path('admin/milk-orders/', views.api_admin_get_all_orders, name='api-admin-orders'),
    path('admin/milk-orders/<int:order_id>/status/', views.api_admin_update_order_status, name='api-admin-update-status'),
    path('admin/milk-orders/bulk-status/', views.api_admin_bulk_update_status, name='api-admin-bulk-status'),
    path('admin/milk-orders/statistics/', views.api_admin_get_statistics, name='api-admin-statistics'),

    path('full-grafic/', views.grafic_for_employee_sheet_view),
    
    path('detect-point/', views.api_detect_point, name='api_detect_point'),
    path('start-shift/', views.api_start_shift, name='api_start_shift'),

    path('upload-avatar/', views.upload_avatar, name='upload-avatar'),

    path('get_menu/', views.get_menu, name='get-menu'),

    path('preferences/', views.save_month_preferences, name='save_prefs'),
    path('optimize/', views.run_schedule_optimization, name='optimize_schedule'),

    path('expense-matrix/', views.api_get_expense_matrix, name='expense-options'),
    path('expenses-update/', views.api_update_expense_cell, name='expenses-table'),

    path('discount-30/check/', views.check_discount_30_eligibility, name='check_discount_30'),
    path('discount-30/generate-qr/', views.generate_discount_qr, name='generate_discount_qr'),
    path('discount-30/process/', views.process_discount_qr, name='process_discount_qr'),

    path('lottery/check-winner/', views.check_lottery_winner, name='check_lottery_winner'),

] + router.urls

