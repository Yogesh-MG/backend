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
  GET    /api/delivery-partner/earnings/history/         — Earnings history
  GET    /api/delivery-partner/profile/                  — Get profile
  PATCH  /api/delivery-partner/profile/                  — Update profile
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
from .models import DeliveryPartnerProfile, DeliveryAssignment, DeliveryStop, ProofOfDelivery, DeliveryPartnerDocument
from .serializers import (
    DeliveryAssignmentSerializer, 
    DeliveryPartnerProfileSerializer,
    DeliveryPartnerDocumentSerializer,
)
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


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryEarningsHistoryView(APIView):
    """Get earnings history for a date range."""
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]

    def get(self, request):
        from datetime import datetime, timedelta
        
        # Get date range from query params (default: last 30 days)
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get all delivered assignments in date range
        assignments = DeliveryAssignment.objects.filter(
            partner=request.user,
            status='DELIVERED',
            delivered_at__date__gte=start_date,
            delivered_at__date__lte=end_date,
        ).order_by('-delivered_at')
        
        # Calculate daily breakdown
        daily_earnings = {}
        for assignment in assignments:
            date_key = assignment.delivered_at.date().isoformat()
            if date_key not in daily_earnings:
                daily_earnings[date_key] = {
                    'date': date_key,
                    'earnings': 0,
                    'deliveries': 0,
                    'distance': 0,
                }
            daily_earnings[date_key]['earnings'] += float(assignment.earnings)
            daily_earnings[date_key]['deliveries'] += 1
            daily_earnings[date_key]['distance'] += float(assignment.distance_km)
        
        # Get lifetime stats
        try:
            profile = request.user.delivery_partner_profile
            lifetime_stats = {
                'total_earnings': float(profile.total_earnings),
                'total_deliveries': profile.total_deliveries,
                'rating': float(profile.rating),
            }
        except DeliveryPartnerProfile.DoesNotExist:
            lifetime_stats = {
                'total_earnings': 0,
                'total_deliveries': 0,
                'rating': 5.0,
            }
        
        return Response({
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat(), 'days': days},
            'summary': {
                'total_earnings': sum(d['earnings'] for d in daily_earnings.values()),
                'total_deliveries': sum(d['deliveries'] for d in daily_earnings.values()),
                'total_distance': sum(d['distance'] for d in daily_earnings.values()),
            },
            'daily_breakdown': list(daily_earnings.values()),
            'lifetime': lifetime_stats,
            'recent_deliveries': [
                {
                    'id': str(a.id),
                    'date': a.delivered_at.isoformat(),
                    'earnings': float(a.earnings),
                    'distance': float(a.distance_km),
                    'service': a.service,
                }
                for a in assignments[:10]
            ],
        })


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryPartnerProfileView(APIView):
    """Get or update delivery partner profile."""
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]

    def get(self, request):
        try:
            profile = request.user.delivery_partner_profile
        except DeliveryPartnerProfile.DoesNotExist:
            profile = DeliveryPartnerProfile.objects.create(user=request.user)
        serializer = DeliveryPartnerProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        try:
            profile = request.user.delivery_partner_profile
        except DeliveryPartnerProfile.DoesNotExist:
            profile = DeliveryPartnerProfile.objects.create(user=request.user)
        
        # Update allowed fields
        allowed_fields = ['vehicle_type', 'vehicle_number']
        for field in allowed_fields:
            if field in request.data:
                setattr(profile, field, request.data[field])
        
        profile.save()
        serializer = DeliveryPartnerProfileSerializer(profile)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class DeliveryPartnerDocumentsView(APIView):
    """Get or upload KYC documents."""
    authentication_classes = [DeviceAuthKeyAuthentication, SessionAuthentication]
    permission_classes = [IsDeliveryPartner]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """List all documents for the partner."""
        documents = DeliveryPartnerDocument.objects.filter(partner=request.user)
        serializer = DeliveryPartnerDocumentSerializer(documents, many=True)
        return Response({
            'documents': serializer.data,
            'kyc_status': self._get_kyc_status(request.user),
        })

    def post(self, request):
        """Upload a new document."""
        doc_type = request.data.get('doc_type')
        doc_number = request.data.get('doc_number', '')
        file = request.FILES.get('file')

        if not doc_type or not file:
            return Response(
                {'error': 'doc_type and file are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if doc_type not in [choice[0] for choice in DeliveryPartnerDocument.DOC_TYPES]:
            return Response(
                {'error': f'Invalid doc_type. Must be one of: {[c[0] for c in DeliveryPartnerDocument.DOC_TYPES]}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update or create document
        document, created = DeliveryPartnerDocument.objects.update_or_create(
            partner=request.user,
            doc_type=doc_type,
            defaults={
                'doc_number': doc_number,
                'file': file,
                'status': 'pending',
                'verified_at': None,
                'rejection_reason': '',
            }
        )

        serializer = DeliveryPartnerDocumentSerializer(document)
        return Response({
            'message': 'Document uploaded successfully',
            'document': serializer.data,
            'kyc_status': self._get_kyc_status(request.user),
        })

    def _get_kyc_status(self, user):
        """Calculate KYC completion status."""
        required_docs = [choice[0] for choice in DeliveryPartnerDocument.DOC_TYPES]
        uploaded_docs = set(
            DeliveryPartnerDocument.objects.filter(partner=user).values_list('doc_type', flat=True)
        )
        
        return {
            'required_count': len(required_docs),
            'uploaded_count': len(uploaded_docs),
            'is_complete': len(uploaded_docs) >= len(required_docs),
            'missing_documents': [d for d in required_docs if d not in uploaded_docs],
        }
