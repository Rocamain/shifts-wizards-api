# Shift Wizard API

A minimal Flask service that assigns employees to shifts using a mixed integer programming model built with [OR-Tools](https://developers.google.com/optimization). The API receives a week of shifts and available employees and returns a complete 7-day schedule.

## Features
- **`/api/schedule`** – POST endpoint that calculates a schedule for the provided shifts and employees.
- Supports a `restPriority` parameter which influences the weighting of off-day bonuses in the model.
- Swagger UI available at `/apidocs/` for interactive documentation and testing.
- Automatically fills any remaining unassigned slots with a greedy heuristic.

## Requirements
- Python 3.10 or higher
- Docker (optional, for containerized deployment)
- Packages listed in `requirements.txt`

## Running Locally (Without Docker)
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
The service will start on port 5000. You can then POST to `http://localhost:5000/api/schedule` or browse `http://localhost:5000/apidocs/`.

## Running with Docker
1. **Build the image**
   ```bash
   docker build -t shift-wizard-api .
   ```
2. **Run the container**
   ```bash
   docker run --rm -p 5000:5000 shift-wizard-api
   ```
3. Visit `http://localhost:5000/` (redirects to `/apidocs/`).

## Example Request
```json
{
  "shifts": [
    [
      {
        "id": "s1",
        "startTime": "09:00",
        "endTime": "17:00",
        "employeeRole": "cashier",
        "candidates": ["e1", "e2"]
      }
    ]
  ],
  "employees": [
    {
      "id": "e1",
      "name": "Alice",
      "contractHours": 40,
      "unavailableDates": []
    }
  ],
  "restPriority": 3
}
```

## Deployment
A `Procfile` is included for platforms like Heroku:
```bash
web: gunicorn --bind :$PORT wsgi:app
```

For Docker-based deployment (e.g., Fly.io, Render, Docker Hub):

1. **Build your Docker image** (tag as desired):
   ```bash
   docker build -t shift-wizard-api .
   ```
2. **Run the container locally**:
   ```bash
   docker run --rm -p 5000:5000 shift-wizard-api
   ```
3. **Push to your registry** (optional, if using remote):
   ```bash
   docker tag shift-wizard-api your-username/shift-wizard-api:latest
   docker push your-username/shift-wizard-api:latest
   ```
4. **Deploy** with your host (Fly.io auto-deploy, Render uses Dockerfile, etc.).

Ensure `wsgi.py` and `Dockerfile` are present in the project root.

## Project Structure
```
├── Dockerfile          # Container configuration
├── Procfile            # Heroku/Gunicorn process file
├── README.md           # Project documentation
├── requirements.txt    # Python dependencies
├── wsgi.py             # Gunicorn entrypoint
├── app.py              # Local development runner
└── app/                # Flask application package
    ├── __init__.py     # App factory & Swagger/CORS config
    ├── api/
    │   ├── routes.py   # `/schedule` endpoint
    │   ├── schedule.yml # Swagger spec
    │   └── services.py # Scheduling logic
    └── ...
```
