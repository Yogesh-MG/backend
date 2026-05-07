"""Picker app URL configuration."""
from django.urls import path
from .views import (
    PickerGeoVerifyView,
    PickerQueueView,
    PickerAcceptView,
    PickerScanView,
    PickerPackView,
    PickerHandoverView,
)

urlpatterns = [
    path('geo-verify/', PickerGeoVerifyView.as_view(), name='picker_geo_verify'),
    path('queue/', PickerQueueView.as_view(), name='picker_queue'),
    path('queue/<uuid:order_id>/accept/', PickerAcceptView.as_view(), name='picker_accept'),
    path('queue/<uuid:order_id>/scan/', PickerScanView.as_view(), name='picker_scan'),
    path('queue/<uuid:order_id>/pack/', PickerPackView.as_view(), name='picker_pack'),
    path('queue/<uuid:order_id>/handover/', PickerHandoverView.as_view(), name='picker_handover'),
]
