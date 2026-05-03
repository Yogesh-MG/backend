from django.urls import path
from . import views

urlpatterns = [
    path('slots/', views.DeliverySlotListView.as_view(), name='delivery-slots'),
    path('addresses/', views.DeliveryAddressListView.as_view(), name='delivery-addresses'),
    path('addresses/<int:address_id>/', views.DeliveryAddressDetailView.as_view(), name='delivery-address-detail'),
    path('validate-location/', views.ValidateLocationView.as_view(), name='validate-location'),
]
