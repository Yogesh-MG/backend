from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import DeliverySlot, DeliveryAddress, ServiceArea
from .serializers import DeliverySlotSerializer, DeliveryAddressSerializer, ServiceAreaSerializer


class DeliverySlotListView(APIView):
    """Get all available delivery slots."""
    
    def get(self, request):
        slots = DeliverySlot.objects.filter(available=True)
        serializer = DeliverySlotSerializer(slots, many=True)
        return Response(serializer.data)


class DeliveryAddressListView(APIView):
    """List user's saved delivery addresses."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        addresses = DeliveryAddress.objects.filter(user=request.user)
        serializer = DeliveryAddressSerializer(addresses, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Save a new delivery address."""
        serializer = DeliveryAddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeliveryAddressDetailView(APIView):
    """Update or delete a delivery address."""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, user, address_id):
        try:
            return DeliveryAddress.objects.get(id=address_id, user=user)
        except DeliveryAddress.DoesNotExist:
            return None
    
    def patch(self, request, address_id):
        address = self.get_object(request.user, address_id)
        if not address:
            return Response({'error': 'Address not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DeliveryAddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, address_id):
        address = self.get_object(request.user, address_id)
        if not address:
            return Response({'error': 'Address not found'}, status=status.HTTP_404_NOT_FOUND)
        
        address.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ValidateLocationView(APIView):
    """Validate if a delivery location is within service area."""
    
    def post(self, request):
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        address = request.data.get('address')
        
        if not all([latitude, longitude, address]):
            return Response(
                {'error': 'Missing latitude, longitude, or address'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid latitude or longitude'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if point is in any active service area
        service_areas = ServiceArea.objects.filter(is_active=True)
        
        for area in service_areas:
            if area.contains_point(latitude, longitude):
                return Response({
                    'valid': True,
                    'message': f'Delivery available in {area.name}',
                    'service_area': area.name,
                })
        
        # Not in any service area
        return Response({
            'valid': False,
            'message': 'Delivery not available at this location',
            'service_area': None,
        })
