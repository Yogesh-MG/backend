"""
Django endpoint to validate if delivery location is within service area.
Place this in your delivery/orders app.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import json
import math

# Define your service areas (replace with actual data from DB)
SERVICE_AREAS = [
    {
        "name": "Koramangala",
        "center_lat": 12.9352,
        "center_lon": 77.6245,
        "radius_km": 2.5,  # 2.5km radius
    },
    {
        "name": "Indiranagar",
        "center_lat": 13.0016,
        "center_lon": 77.6412,
        "radius_km": 2.5,
    },
    {
        "name": "Whitefield",
        "center_lat": 12.9698,
        "center_lon": 77.7499,
        "radius_km": 2.0,
    },
]


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    distance = R * c

    return distance


def is_within_service_area(latitude, longitude):
    """
    Check if coordinates are within any service area.
    Returns (is_valid, service_area_name, distance_to_center)
    """
    for area in SERVICE_AREAS:
        distance = calculate_distance(
            latitude, longitude, area["center_lat"], area["center_lon"]
        )

        if distance <= area["radius_km"]:
            return True, area["name"], distance

    return False, None, None


@api_view(["POST"])
@permission_classes([AllowAny])
def validate_location(request):
    """
    Validate if delivery location is within service area.
    
    Request body:
    {
        "latitude": 12.9352,
        "longitude": 77.6245,
        "address": "Koramangala, Bangalore"
    }
    
    Response:
    {
        "valid": true,
        "message": "Location is within service area",
        "service_area": "Koramangala",
        "distance_km": 0.5
    }
    """
    try:
        data = request.data
        latitude = float(data.get("latitude", 0))
        longitude = float(data.get("longitude", 0))
        address = data.get("address", "")

        # Validate location
        is_valid, service_area, distance = is_within_service_area(
            latitude, longitude
        )

        if is_valid:
            return Response(
                {
                    "valid": True,
                    "message": f"Location is within {service_area} service area",
                    "service_area": service_area,
                    "distance_km": round(distance, 2),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "valid": False,
                    "message": "Location is outside our delivery area. Please select a location within: "
                    + ", ".join([area["name"] for area in SERVICE_AREAS]),
                    "service_area": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    except (ValueError, TypeError) as e:
        return Response(
            {
                "valid": False,
                "message": f"Invalid location data: {str(e)}",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {
                "valid": False,
                "message": "Error validating location",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
