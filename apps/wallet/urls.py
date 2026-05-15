from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import WalletViewSet, PartnershipViewSet, ReferralViewSet

router = SimpleRouter()
router.register('', WalletViewSet, basename='wallet')
router.register('partnerships', PartnershipViewSet, basename='partnership')
router.register('referrals', ReferralViewSet, basename='referral')

urlpatterns = router.urls
