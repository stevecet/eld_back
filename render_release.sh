#!/bin/bash
echo "=== Running release phase on Render ==="
python manage.py migrate
python manage.py collectstatic --noinput
