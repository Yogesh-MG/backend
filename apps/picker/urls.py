"""Picker app URL configuration."""
from django.urls import path
from .views import (
    PickerGeoVerifyView,
    PickerQueueView,
    PickerAcceptView,
    PickerScanView,
    PickerPackView,
    PickerHandoverView,
    PickerSetupPinView,
    PickerLoginPinView,
    # Shift Management
    PickerShiftStartView,
    PickerShiftEndView,
    PickerBreakStartView,
    PickerBreakEndView,
    PickerLocationCheckInView,
    PickerCurrentShiftView,
    PickerShiftHistoryView,
)

urlpatterns = [
    path('geo-verify/', PickerGeoVerifyView.as_view(), name='picker_geo_verify'),
    path('queue/', PickerQueueView.as_view(), name='picker_queue'),
    path('queue/<uuid:order_id>/accept/', PickerAcceptView.as_view(), name='picker_accept'),
    path('queue/<uuid:order_id>/scan/', PickerScanView.as_view(), name='picker_scan'),
    path('queue/<uuid:order_id>/pack/', PickerPackView.as_view(), name='picker_pack'),
    path('queue/<uuid:order_id>/handover/', PickerHandoverView.as_view(), name='picker_handover'),
    # PIN Authentication
    path('setup-pin/', PickerSetupPinView.as_view(), name='picker_setup_pin'),
    path('login-pin/', PickerLoginPinView.as_view(), name='picker_login_pin'),
    # Shift & Attendance
    path('shift-start/', PickerShiftStartView.as_view(), name='picker_shift_start'),
    path('shift-end/', PickerShiftEndView.as_view(), name='picker_shift_end'),
    path('break-start/', PickerBreakStartView.as_view(), name='picker_break_start'),
    path('break-end/', PickerBreakEndView.as_view(), name='picker_break_end'),
    path('location-checkin/', PickerLocationCheckInView.as_view(), name='picker_location_checkin'),
    path('current-shift/', PickerCurrentShiftView.as_view(), name='picker_current_shift'),
    path('shift-history/', PickerShiftHistoryView.as_view(), name='picker_shift_history'),
]
