from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import DeliverySlot, DeliveryAddress, ServiceArea
from .serializers import DeliverySlotSerializer, DeliveryAddressSerializer, ServiceAreaSerializer


class DeliverySlotListView(APIView):
    """Get all available delivery slots based on customer coordinates (radius validation)."""
    
    def get(self, request):
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        
        # Fallback to user's default address coordinates
        if not latitude or not longitude:
            if request.user.is_authenticated:
                default_addr = request.user.delivery_addresses.filter(is_default=True).first()
                if default_addr and default_addr.latitude and default_addr.longitude:
                    latitude = default_addr.latitude
                    longitude = default_addr.longitude
                    
        out_of_radius = False
        if latitude and longitude:
            try:
                lat = float(latitude)
                lng = float(longitude)
                out_of_radius = not ServiceArea.is_in_any_active_service_area(lat, lng)
            except (ValueError, TypeError):
                pass
                
        if out_of_radius:
            # Only return OUT_OF_RADIUS slots
            slots = DeliverySlot.objects.filter(available=True, slot_type='OUT_OF_RADIUS')
            # Fallback: if admin hasn't created one, create it
            if not slots.exists():
                default_slot, _ = DeliverySlot.objects.get_or_create(
                    id='2-4-days',
                    defaults={
                        'title': '2-4 Days Standard Delivery',
                        'description': 'Standard delivery for out-of-radius areas',
                        'slot_type': 'OUT_OF_RADIUS',
                        'delivery_fee': 50.00,
                        'weight_charge': 15.00,  # 15 rupees per kg
                        'available': True
                    }
                )
                slots = DeliverySlot.objects.filter(id=default_slot.id)
        else:
            # In radius: exclude OUT_OF_RADIUS slots
            slots = DeliverySlot.objects.filter(available=True).exclude(slot_type='OUT_OF_RADIUS')
            
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
