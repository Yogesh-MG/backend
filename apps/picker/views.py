"""
Picker app views.

Endpoints:
  GET  /api/picker/queue/                        — Orders ready to pick
  POST /api/picker/queue/{order_id}/accept/       — Accept order
  POST /api/picker/queue/{order_id}/scan/         — QR scan verification
  POST /api/picker/queue/{order_id}/pack/         — Mark all items packed
  POST /api/picker/queue/{order_id}/handover/     — Hand to delivery
  POST /api/picker/geo-verify/                    — Verify picker at hub
  POST /api/picker/setup-pin/                     — Set quick access PIN
  POST /api/picker/login-pin/                     — Login using PIN
"""
import math
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import PickerProfile, PickerTask, PickerTaskItem
from .serializers import PickerTaskSerializer
from .permissions import IsPickerUser
from apps.accounts.views import _set_auth_cookies


@method_decorator(csrf_exempt, name='dispatch')
class PickerGeoVerifyView(APIView):
    """
    POST /api/picker/geo-verify/
    Verify that the picker is within the hub's geo-fence.
    """
    permission_classes = [IsPickerUser]

    def post(self, request):
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if latitude is None or longitude is None:
            return Response(
                {'error': 'latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat = float(latitude)
            lng = float(longitude)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid coordinates'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get picker's hub profile
        try:
            profile = request.user.picker_profile
        except PickerProfile.DoesNotExist:
            return Response(
                {'verified': False, 'message': 'Picker profile not found. Contact admin.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Determine hub coordinates (prefer Hub relation over deprecated fields)
        if profile.hub:
            hub_lat = float(profile.hub.latitude)
            hub_lng = float(profile.hub.longitude)
            hub_radius = profile.hub.radius_meters
            hub_name = profile.hub.name
        else:
            hub_lat = float(profile.hub_latitude)
            hub_lng = float(profile.hub_longitude)
            hub_radius = profile.hub_radius_meters
            hub_name = profile.hub_name

        R = 6371000  # Earth's radius in meters

        dlat = math.radians(lat - hub_lat)
        dlng = math.radians(lng - hub_lng)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(hub_lat)) *
             math.cos(math.radians(lat)) *
             math.sin(dlng / 2) ** 2)
        distance_m = R * 2 * math.asin(math.sqrt(a))

        if distance_m <= hub_radius:
            return Response({
                'verified': True,
                'message': f'Welcome to {hub_name}!',
                'hub_name': hub_name,
            })
        else:
            return Response({
                'verified': False,
                'message': f'You are {int(distance_m)}m away from {hub_name}. Please move closer.',
            })


@method_decorator(csrf_exempt, name='dispatch')
class PickerSetupPinView(APIView):
    """
    POST /api/picker/setup-pin/
    Set a numeric PIN for the authenticated picker.
    """
    permission_classes = [IsPickerUser]

    def post(self, request):
        pin = request.data.get('pin')
        if not pin or not str(pin).isdigit() or len(str(pin)) != 4:
            return Response({'error': 'A 4-digit numeric PIN is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        profile = request.user.picker_profile
        profile.pin = pin
        profile.save()
        
        return Response({'success': True, 'message': 'PIN setup successfully'})


@method_decorator(csrf_exempt, name='dispatch')
class PickerLoginPinView(APIView):
    """
    POST /api/picker/login-pin/
    Login using employee_id (username) and PIN.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        employee_id = request.data.get('employee_id')
        pin = request.data.get('pin')
        
        if not employee_id or not pin:
            return Response({'error': 'Employee ID and PIN are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            profile = PickerProfile.objects.get(user__username=employee_id, pin=pin, is_active=True)
            user = profile.user
        except PickerProfile.DoesNotExist:
            return Response({'error': 'Invalid ID or PIN'}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Operational apps get long-lived tokens (30 days)
        # We check for the app header
        platform = request.headers.get('X-App-Platform')
        is_app = platform in ['PickerApp', 'DeliveryApp', 'FarmerApp']
        
        from datetime import timedelta
        if is_app:
            refresh.set_exp(lifetime=timedelta(days=90))
            refresh.access_token.set_exp(lifetime=timedelta(days=30))
            
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        response = Response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'picker_profile': {
                'hub_name': profile.hub_name,
                'hub_latitude': float(profile.hub.latitude) if profile.hub else float(profile.hub_latitude),
                'hub_longitude': float(profile.hub.longitude) if profile.hub else float(profile.hub_longitude),
                'hub_radius_meters': profile.hub.radius_meters if profile.hub else profile.hub_radius_meters,
            }
        })
        
        _set_auth_cookies(response, access_token, refresh_token, is_app_request=is_app)
        return response


@method_decorator(csrf_exempt, name='dispatch')
class PickerQueueView(APIView):
    """
    GET /api/picker/queue/
    List all orders in the queue that are available to pick.
    """
    permission_classes = [IsPickerUser]

    def get(self, request):
        tasks = PickerTask.objects.filter(
            status__in=['QUEUED', 'IN_PROGRESS'],
        ).select_related('order', 'order__user').prefetch_related('items')

        # Filter: show queued (unassigned) tasks + tasks assigned to this picker
        from django.db.models import Q
        tasks = tasks.filter(
            Q(status='QUEUED', picker__isnull=True) | Q(picker=request.user)
        )

        serializer = PickerTaskSerializer(tasks, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class PickerAcceptView(APIView):
    """
    POST /api/picker/queue/{order_id}/accept/
    Accept a queued order.
    """
    permission_classes = [IsPickerUser]

    def post(self, request, order_id):
        try:
            task = PickerTask.objects.get(id=order_id)
        except PickerTask.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

        if task.status != 'QUEUED':
            return Response(
                {'error': f'Task is already {task.status}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if task.picker and task.picker != request.user:
            return Response(
                {'error': 'Task already accepted by another picker'},
                status=status.HTTP_409_CONFLICT,
            )

        task.picker = request.user
        task.status = 'IN_PROGRESS'
        task.accepted_at = timezone.now()
        task.save()

        # Update the parent order status
        task.order.status = 'PROCESSING'
        task.order.save()

        serializer = PickerTaskSerializer(task)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class PickerScanView(APIView):
    """
    POST /api/picker/queue/{order_id}/scan/
    Verify a scanned barcode against the expected item.
    """
    permission_classes = [IsPickerUser]

    def post(self, request, order_id):
        item_id = request.data.get('item_id')
        barcode = request.data.get('barcode')

        if not item_id or not barcode:
            return Response(
                {'error': 'item_id and barcode are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task = PickerTask.objects.get(id=order_id, picker=request.user)
        except PickerTask.DoesNotExist:
            return Response({'error': 'Task not found or not assigned to you'}, status=status.HTTP_404_NOT_FOUND)

        try:
            item = task.items.get(id=item_id)
        except PickerTaskItem.DoesNotExist:
            return Response({'error': 'Item not found in this task'}, status=status.HTTP_404_NOT_FOUND)

        item.scanned_barcode = barcode

        if (item.batch_code and barcode == item.batch_code) or (item.sku and barcode == item.sku):
            item.status = 'packed'
            item.save()
            return Response({'verified': True, 'message': 'Item verified and packed!'})
        else:
            item.status = 'issue'
            item.save()
            return Response({
                'verified': False,
                'message': f'Barcode mismatch. Expected: {item.batch_code or item.sku}, Got: {barcode}',
            })


@method_decorator(csrf_exempt, name='dispatch')
class PickerPackView(APIView):
    """
    POST /api/picker/queue/{order_id}/pack/
    Mark all items in the order as packed.
    """
    permission_classes = [IsPickerUser]

    def post(self, request, order_id):
        try:
            task = PickerTask.objects.get(id=order_id, picker=request.user)
        except PickerTask.DoesNotExist:
            return Response({'error': 'Task not found or not assigned to you'}, status=status.HTTP_404_NOT_FOUND)

        task.items.filter(status__in=['pending', 'scanning']).update(status='packed')
        task.status = 'PACKED'
        task.packed_at = timezone.now()
        task.save()

        return Response({'message': 'All items packed successfully!', 'status': task.status})


@method_decorator(csrf_exempt, name='dispatch')
class PickerHandoverView(APIView):
    """
    POST /api/picker/queue/{order_id}/handover/
    Hand over a packed order to a delivery partner.
    """
    permission_classes = [IsPickerUser]

    def post(self, request, order_id):
        try:
            task = PickerTask.objects.get(id=order_id, picker=request.user)
        except PickerTask.DoesNotExist:
            return Response({'error': 'Task not found or not assigned to you'}, status=status.HTTP_404_NOT_FOUND)

        task.status = 'HANDED_OVER'
        task.handed_over_at = timezone.now()
        task.save()

        task.order.status = 'SHIPPED'
        task.order.save()

        return Response({'message': 'Order handed over to delivery!'})
