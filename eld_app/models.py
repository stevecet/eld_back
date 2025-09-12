from django.db import models
from datetime import datetime, timedelta

class Trip(models.Model):
    current_location = models.CharField(max_length=200)
    pickup_location = models.CharField(max_length=200)
    dropoff_location = models.CharField(max_length=200)
    current_cycle_hours = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip from {self.pickup_location} to {self.dropoff_location}"

class LogEntry(models.Model):
    DUTY_STATUS_CHOICES = [
        ('off_duty', 'Off Duty'),
        ('sleeper_berth', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('on_duty_not_driving', 'On Duty (Not Driving)'),
    ]

    trip = models.ForeignKey(Trip, related_name='log_entries', on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duty_status = models.CharField(max_length=20, choices=DUTY_STATUS_CHOICES)
    location = models.CharField(max_length=200)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['date', 'start_time']
