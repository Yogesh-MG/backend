"""Delivery Partner app URL configuration."""
from django.urls import path
from .views import (
    DeliveryPartnerStatusView,
    DeliveryAssignmentsView,
    DeliveryAcceptView,
    DeliveryPickupView,
    DeliveryTransitView,
    DeliveryDeliverView,
    DeliveryProofUploadView,
    DeliveryEarningsView,
)

urlpatterns = [
    path('status/', DeliveryPartnerStatusView.as_view(), name='dp_status'),
    path('assignments/', DeliveryAssignmentsView.as_view(), name='dp_assignments'),
    path('assignments/<uuid:assignment_id>/accept/', DeliveryAcceptView.as_view(), name='dp_accept'),
    path('assignments/<uuid:assignment_id>/pickup/', DeliveryPickupView.as_view(), name='dp_pickup'),
    path('assignments/<uuid:assignment_id>/transit/', DeliveryTransitView.as_view(), name='dp_transit'),
    path('assignments/<uuid:assignment_id>/deliver/', DeliveryDeliverView.as_view(), name='dp_deliver'),
    path('proof/', DeliveryProofUploadView.as_view(), name='dp_proof_upload'),
    path('earnings/', DeliveryEarningsView.as_view(), name='dp_earnings'),
]
