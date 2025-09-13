# ELD Backend

A Django REST API that plans trucking trips and generates DOT-compliant Electronic Logging Device (ELD) log sheets.

---

## Features

- Accepts trip details (current, pickup, dropoff locations and hours left)
- Calculates route and driving/rest schedule based on FMCSA rules
- Outputs:
  - Route segments with distances & durations
  - `log_entries` for each duty status change
  - `daily_logs` grouped per day (FMCSA log sheets format)
- Serves data to the React frontend

---

## Setup

### 1. Clone and enter the backend folder

git clone <your-repo-url>
cd eld_project_files

### 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows

#### 3. Install dependencies
pip install -r requirements.txt

#### 4. Set environment variables

Create a .env file:

SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3        

### 5. Database Setup

Run migrations:

python manage.py migrate

### 6. Running locally
python manage.py runserver


API will be available at http://127.0.0.1:8000/