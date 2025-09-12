from django.contrib import admin
from .models import Trip, LogEntry

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('pickup_location', 'dropoff_location', 'current_location', 'created_at')

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('trip', 'date', 'start_time', 'end_time', 'duty_status', 'location')
