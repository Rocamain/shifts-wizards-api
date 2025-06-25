### Shift Wizard API

A minimal Flask service that assigns employees to shifts using a mixed integer
programming model built with [OR-Tools](https://developers.google.com/optimization).
The API receives a week of shifts and available employees and returns a complete
7‑day schedule.

## Features
* **`/api/schedule`** &ndash; POST endpoint that calculates a schedule for the
  provided shifts and employees.
* Support for a `restPriority` parameter which influences the weighting of off-day
  bonuses in the model.
* Automatically fills any remaining unassigned slots with a greedy heuristic.

## Requirements
* Python 3.10 or higher.
* Packages listed in `requirements.txt`.

## Running Locally
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
The service will start on port 5000. You can then POST to
`http://localhost:5000/api/schedule`.

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
A `Procfile` is included for running with Gunicorn:
```bash
web: gunicorn --bind :$PORT "app:create_app()"
```

## Project Structure
- `app/__init__.py` &ndash; application factory and CORS configuration
- `app/api/routes.py` &ndash; defines the `/schedule` endpoint
- `app/api/services.py` &ndash; optimization and greedy fill-in logic
