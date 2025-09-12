from datetime import datetime, timedelta, time
import math
import requests
from requests.exceptions import RequestException
from .models import LogEntry

class RouteService:
    """Service for geocoding locations and calculating driving routes using OSRM and OpenStreetMap APIs."""
    def __init__(self):
        self.base_url = "https://router.project-osrm.org/route/v1/driving"
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
    
    def geocode_location(self, location):
        """Geocodes a location string to latitude and longitude using Nominatim."""
        params = {
            'q': location,
            'format': 'json',
            'limit': 1
        }
        try:
            response = requests.get(self.nominatim_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data and 'lat' in data[0] and 'lon' in data[0]:
                return float(data[0]['lat']), float(data[0]['lon'])
        except (RequestException, IndexError, ValueError) as e:
            print(f"Geocoding failed for '{location}': {e}")
            return None, None
        return None, None

    def calculate_route(self, current_loc, pickup_loc, dropoff_loc):
        """Calculates a driving route with waypoints and returns route data."""
        try:
            locations = []
            for loc_str in [current_loc, pickup_loc, dropoff_loc]:
                lat, lon = self.geocode_location(loc_str)
                if lat is None or lon is None:
                    raise ValueError(f"Geocoding failed for: {loc_str}")
                locations.append(f"{lon},{lat}")

            coordinates = ";".join(locations)
            url = f"{self.base_url}/{coordinates}"
            params = {
                'overview': 'full',
                'geometries': 'geojson'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            route_data = response.json()

            if route_data.get('code') != 'Ok' or not route_data.get('routes'):
                raise ValueError("OSRM route calculation failed or no route found.")
            
            route = route_data['routes'][0]
            total_distance_miles = route['distance'] / 1609.34
            total_duration_hours = route['duration'] / 3600
            
            # This is a bit of a hack to get segment durations,
            # but it's more accurate than a simple percentage.
            segments = []
            for leg in route['legs']:
                segments.append({
                    'duration_hours': leg['duration'] / 3600,
                    'distance_miles': leg['distance'] / 1609.34
                })

            return {
                'total_distance': round(total_distance_miles, 1),
                'total_duration': round(total_duration_hours, 1),
                'geometry': route['geometry'],
                'segments': segments,
                'waypoints': [
                    {'name': current_loc, 'coordinates': [locations[0].split(',')[1], locations[0].split(',')[0]]},
                    {'name': pickup_loc, 'coordinates': [locations[1].split(',')[1], locations[1].split(',')[0]]},
                    {'name': dropoff_loc, 'coordinates': [locations[2].split(',')[1], locations[2].split(',')[0]]},
                ]
            }

        except (RequestException, ValueError, KeyError) as e:
            print(f"Route calculation error: {e}. Falling back to mock data.")
            return self._get_mock_route(current_loc, pickup_loc, dropoff_loc)

    def _get_mock_route(self, current_loc, pickup_loc, dropoff_loc):
        """Provides a static, mock route for offline or failed API calls."""
        return {
            'total_distance': 100,
            'total_duration': 2,
            'geometry': {'type': 'LineString', 'coordinates': []},
            'segments': [
                {'duration_hours': 0.8, 'distance_miles': 40},
                {'duration_hours': 1.2, 'distance_miles': 60}
            ],
            'waypoints': [
                {'name': current_loc, 'coordinates': [39.7392, -104.9903]},
                {'name': pickup_loc, 'coordinates': [39.0997, -94.5786]},
                {'name': dropoff_loc, 'coordinates': [41.8781, -87.6298]},
            ]
        }


class ELDService:
    """Service for generating ELD-compliant log entries and daily log sheets."""
    def __init__(self):
        self.max_drive_hours = 11
        self.max_duty_hours = 14
        self.required_break_after_drive = 8
        self.break_duration = 0.5
        self.off_duty_required = 10
        self.pickup_dropoff_duration = 1

    def generate_log_entries(self, trip, route_data, current_cycle_hours):
        """Generate log entries based on route and HOS regulations."""
        log_entries = []
        current_date = datetime.now().date()
        current_time_decimal = datetime.now().hour + datetime.now().minute / 60

        # Initial Off-Duty segment
        if current_time_decimal > 0:
            log_entries.append(self._create_log_entry(trip, 'off_duty', current_date, 0, current_time_decimal, trip.current_location, 'Off duty before trip start'))

        daily_drive_hours = 0
        daily_duty_hours = 0
        hours_since_break = 0
        total_trip_duration = 0
        
        # Process each route segment (current->pickup, pickup->dropoff)
        for i, segment in enumerate(route_data['segments']):
            is_first_segment = (i == 0)
            
            # On-duty not driving for loading/unloading
            if not is_first_segment:
                log_entries.append(self._create_log_entry(trip, 'on_duty_not_driving', current_date, current_time_decimal, current_time_decimal + self.pickup_dropoff_duration, route_data['waypoints'][i]['name'], 'Loading/unloading activities'))
                current_time_decimal += self.pickup_dropoff_duration
                daily_duty_hours += self.pickup_dropoff_duration
            
            drive_time_to_add = segment['duration_hours']
            
            # Split driving time to respect 8-hour break rule
            while drive_time_to_add > 0:
                hours_until_break = self.required_break_after_drive - hours_since_break
                drive_segment_duration = min(drive_time_to_add, hours_until_break)

                # Check for day change or HOS limits
                if (current_time_decimal + drive_segment_duration > 24 or
                    daily_drive_hours + drive_segment_duration > self.max_drive_hours or
                    daily_duty_hours + drive_segment_duration > self.max_duty_hours):
                    
                    # Log remaining hours of current day and transition
                    time_to_midnight = 24 - current_time_decimal
                    
                    if time_to_midnight > 0:
                        log_entries.append(self._create_log_entry(trip, 'driving', current_date, current_time_decimal, 24, route_data['waypoints'][i]['name'], 'Driving towards ' + route_data['waypoints'][i+1]['name']))
                        daily_drive_hours += time_to_midnight
                        daily_duty_hours += time_to_midnight
                        drive_time_to_add -= time_to_midnight
                        
                    # Transition to next day with mandatory off-duty/sleeper berth time
                    current_date += timedelta(days=1)
                    current_time_decimal = 0
                    daily_drive_hours = 0
                    daily_duty_hours = 0
                    hours_since_break = 0
                    
                    log_entries.append(self._create_log_entry(trip, 'off_duty', current_date, 0, self.off_duty_required, route_data['waypoints'][i+1]['name'], 'Required 10-hour rest period'))
                    current_time_decimal += self.off_duty_required
                    
                    # Continue loop with remaining time
                    continue

                # Log driving segment
                log_entries.append(self._create_log_entry(trip, 'driving', current_date, current_time_decimal, current_time_decimal + drive_segment_duration, route_data['waypoints'][i]['name'], 'Driving towards ' + route_data['waypoints'][i+1]['name']))
                
                current_time_decimal += drive_segment_duration
                daily_drive_hours += drive_segment_duration
                daily_duty_hours += drive_segment_duration
                hours_since_break += drive_segment_duration
                drive_time_to_add -= drive_segment_duration
                
                # Add a 30-minute break if needed
                if hours_since_break >= self.required_break_after_drive:
                    log_entries.append(self._create_log_entry(trip, 'off_duty', current_date, current_time_decimal, current_time_decimal + self.break_duration, "Rest Area", 'Required 30-minute break'))
                    current_time_decimal += self.break_duration
                    daily_duty_hours += self.break_duration
                    hours_since_break = 0

        # Log final off-duty time at dropoff
        if current_time_decimal < 24:
            log_entries.append(self._create_log_entry(trip, 'off_duty', current_date, current_time_decimal, 24, trip.dropoff_location, 'Trip completed, off duty'))

        for entry in log_entries:
            entry.save()
        
        return log_entries

    def _create_log_entry(self, trip, status, date, start_decimal, end_decimal, location, remarks):
        """Helper function to create a LogEntry object."""
        start_time = self._decimal_to_time(start_decimal)
        end_time = self._decimal_to_time(end_decimal)
        return LogEntry(
            trip=trip,
            date=date,
            start_time=start_time,
            end_time=end_time,
            duty_status=status,
            location=location,
            remarks=remarks
        )

    def _decimal_to_time(self, decimal_hour):
        """Convert decimal hour to time object."""
        hour = int(decimal_hour)
        minute = int((decimal_hour - hour) * 60)
        return time(hour % 24, minute)

    def generate_daily_log_sheets(self, log_entries):
        """Generate daily log sheet data for visualization."""
        daily_logs = {}

        for entry in log_entries:
            date_str = entry.date.strftime('%Y-%m-%d')
            if date_str not in daily_logs:
                daily_logs[date_str] = {
                    'date_start': date_str,
                    'segments': [],
                    'totals': {
                        'off_duty': 0,
                        'sleeper_berth': 0,
                        'driving': 0,
                        'on_duty_not_driving': 0
                    }
                }

            start_minutes = entry.start_time.hour * 60 + entry.start_time.minute
            end_minutes = entry.end_time.hour * 60 + entry.end_time.minute
            if end_minutes < start_minutes:
                # crossed midnight → add 24 hours
                end_minutes += 24 * 60
            duration = (end_minutes - start_minutes) / 60

            daily_logs[date_str]['segments'].append({
                'id': len(daily_logs[date_str]['segments']),
                'status': entry.duty_status,
                'note': entry.remarks,
                'start_time': entry.start_time.strftime('%H:%M'),
                'end_time': entry.end_time.strftime('%H:%M'),
                'duration_hours': round(duration, 2)
            })

            daily_logs[date_str]['totals'][entry.duty_status] += duration
        
        return list(daily_logs.values())