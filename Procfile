release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn eld_project.wsgi --log-file -
