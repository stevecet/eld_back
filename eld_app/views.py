from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Trip, LogEntry
from .serializers import TripSerializer, LogEntrySerializer
from .services import RouteService, ELDService
import logging

logger = logging.getLogger(__name__)

class TripPlannerView(APIView):
    def post(self, request):
        try:
            data = request.data

            # Create trip record
            trip = Trip.objects.create(
                current_location=data['current_location'],
                pickup_location=data['pickup_location'],
                dropoff_location=data['dropoff_location'],
                current_cycle_hours=float(data['current_cycle_hours'])
            )

            # Get route information
            route_service = RouteService()
            route_data = route_service.calculate_route(
                data['current_location'],
                data['pickup_location'],
                data['dropoff_location']
            )

            if not route_data:
                return Response({
                    'error': 'Could not calculate route'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Generate ELD logs
            eld_service = ELDService()
            log_entries = eld_service.generate_log_entries(
                trip, route_data, float(data['current_cycle_hours'])
            )

            # Serialize response
            trip_serializer = TripSerializer(trip)
            log_serializer = LogEntrySerializer(log_entries, many=True)

            return Response({
                'trip': trip_serializer.data,
                'route': route_data,
                'log_entries': log_serializer.data,
                'daily_logs': eld_service.generate_daily_log_sheets(log_entries)
            })

        except Exception as e:
            logger.error(f"Error in TripPlannerView: {str(e)}")
            return Response({
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
