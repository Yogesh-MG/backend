"""
Delivery Partner app views.

Endpoints:
  GET    /api/delivery-partner/assignments/              — Active deliveries
  POST   /api/delivery-partner/assignments/{id}/accept/  — Accept assignment
  POST   /api/delivery-partner/assignments/{id}/pickup/  — Picked up from hub
  POST   /api/delivery-partner/assignments/{id}/transit/ — Out for delivery
  POST   /api/delivery-partner/assignments/{id}/deliver/ — Proof of delivery
  POST   /api/delivery-partner/proof/                    — Photo upload
  PATCH  /api/delivery-partner/status/                   — Online/offline toggle
  GET    /api/delivery-partner/earnings/                 — Today's earnings
"""
from decimal import Decimal
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authentication import SessionAuthentication

from apps.accounts.auth import DeviceAuthKeyAuthentication
from .models import DeliveryPartnerProfile, DeliveryAssignment, DeliveryStop, ProofOfDelivery
from .serializers import DeliveryAssignmentSerializer
from .permissions import IsDeliveryPartner


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryPartnerStatusView(APIView):
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]

    def patch(self, request):
        profile, _ = DeliveryPartnerProfile.objects.get_or_create(user=request.user)
        online = request.data.get('online')
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        if online is not None:
            profile.is_online = bool(online)
        if lat is not None and lng is not None:
            try:
                profile.current_latitude = Decimal(str(lat))
                profile.current_longitude = Decimal(str(lng))
                profile.last_location_update = timezone.now()
            except Exception:
                pass
        profile.save()
        return Response({'message': f'Status: {"Online" if profile.is_online else "Offline"}', 'online': profile.is_online})


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryAssignmentsView(APIView):
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]

    def get(self, request):
        assignments = DeliveryAssignment.objects.filter(
            partner=request.user,
            status__in=['PENDING', 'ACCEPTED', 'PICKED_UP', 'IN_TRANSIT'],
        ).select_related('order', 'order__user').prefetch_related('stops')
        serializer = DeliveryAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryAcceptView(APIView):
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]

    def post(self, request, assignment_id):
        try:
            a = DeliveryAssignment.objects.get(id=assignment_id)
        except DeliveryAssignment.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        if a.status != 'PENDING':
            return Response({'error': f'Already {a.status}'}, status=status.HTTP_400_BAD_REQUEST)
        a.partner = request.user
        a.status = 'ACCEPTED'
        a.accepted_at = timezone.now()
        a.save()
        return Response(DeliveryAssignmentSerializer(a).data)


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryPickupView(APIView):
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]

    def post(self, request, assignment_id):
        try:
            a = DeliveryAssignment.objects.get(id=assignment_id, partner=request.user)
        except DeliveryAssignment.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        if a.status != 'ACCEPTED':
            return Response({'error': f'Cannot pickup from {a.status}'}, status=status.HTTP_400_BAD_REQUEST)
        a.status = 'PICKED_UP'
        a.picked_up_at = timezone.now()
        a.save()
        a.stops.filter(type='pickup').update(is_completed=True, completed_at=timezone.now())
        return Response({'message': 'Order picked up from hub!'})


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryTransitView(APIView):
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]

    def post(self, request, assignment_id):
        try:
            a = DeliveryAssignment.objects.get(id=assignment_id, partner=request.user)
        except DeliveryAssignment.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        if a.status not in ['PICKED_UP', 'ACCEPTED']:
            return Response({'error': f'Cannot transit from {a.status}'}, status=status.HTTP_400_BAD_REQUEST)
        a.status = 'IN_TRANSIT'
        a.in_transit_at = timezone.now()
        a.save()
        lat, lng = request.data.get('latitude'), request.data.get('longitude')
        if lat and lng:
            try:
                p = request.user.delivery_partner_profile
                p.current_latitude = Decimal(str(lat))
                p.current_longitude = Decimal(str(lng))
                p.last_location_update = timezone.now()
                p.save()
            except DeliveryPartnerProfile.DoesNotExist:
                pass
        a.order.status = 'SHIPPED'
        a.order.save()
        return Response({'message': 'Out for delivery!'})


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryDeliverView(APIView):
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]

    def post(self, request, assignment_id):
        try:
            a = DeliveryAssignment.objects.get(id=assignment_id, partner=request.user)
        except DeliveryAssignment.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        if a.status not in ['IN_TRANSIT', 'PICKED_UP']:
            return Response({'error': f'Cannot deliver from {a.status}'}, status=status.HTTP_400_BAD_REQUEST)
        proof_type = request.data.get('type', 'otp')
        otp_code = request.data.get('otp_code', '')
        stop_id = request.data.get('stop_id')
        stop = None
        if stop_id:
            try:
                stop = a.stops.get(id=stop_id)
            except DeliveryStop.DoesNotExist:
                pass
        ProofOfDelivery.objects.create(
            assignment=a, stop=stop, type=proof_type,
            otp_code=otp_code, otp_verified=(proof_type == 'otp' and bool(otp_code)),
        )
        if stop:
            stop.is_completed = True
            stop.completed_at = timezone.now()
            stop.save()
        dropoffs = a.stops.filter(type='dropoff')
        if dropoffs.exists() and not dropoffs.filter(is_completed=False).exists():
            a.status = 'DELIVERED'
            a.delivered_at = timezone.now()
            a.save()
            a.order.status = 'DELIVERED'
            a.order.save()
            try:
                p = request.user.delivery_partner_profile
                p.total_deliveries += 1
                p.total_earnings += a.earnings
                p.save()
            except DeliveryPartnerProfile.DoesNotExist:
                pass
        return Response({'message': 'Delivery proof recorded!'})


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryProofUploadView(APIView):
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        mission_id = request.data.get('mission_id')
        photo = request.FILES.get('photo')
        if not mission_id or not photo:
            return Response({'error': 'mission_id and photo required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            a = DeliveryAssignment.objects.get(id=mission_id, partner=request.user)
        except DeliveryAssignment.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        proof = ProofOfDelivery.objects.create(assignment=a, type='photo', photo=photo)
        url = request.build_absolute_uri(proof.photo.url) if proof.photo else ''
        return Response({'url': url})


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryEarningsView(APIView):
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]

    def get(self, request):
        today = timezone.now().date()
        today_q = DeliveryAssignment.objects.filter(
            partner=request.user, delivered_at__date=today, status='DELIVERED',
        )
        earnings = today_q.aggregate(t=Sum('earnings'))['t'] or 0
        dist = today_q.aggregate(d=Sum('distance_km'))['d'] or 0
        try:
            rating = float(request.user.delivery_partner_profile.rating)
        except DeliveryPartnerProfile.DoesNotExist:
            rating = 5.0
        return Response({
            'earnings': float(earnings), 'goal': 1500.0,
            'deliveries': today_q.count(), 'distance': float(dist), 'rating': rating,
        })
