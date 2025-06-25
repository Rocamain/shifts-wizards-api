from flask import Blueprint, request, jsonify
import psutil, os
from flasgger import swag_from
from app.api.services import allocate_shifts, fill_in_unassigned

api = Blueprint("api", __name__)

@api.route("/schedule", methods=["POST"])
@swag_from("schedule.yml")
def schedule():
    print("🔄 Received request to /schedule", request.json)
    try:
        data = request.json or {}
        shifts_input = data.get("shifts")      # list[list[shift]]
        employees = data.get("employees")      # list[staff]
        rest_priority = data.get("restPriority", 3)

        # Basic payload validation
        if shifts_input is None or employees is None:
            return jsonify({"error": "Missing required fields: 'shifts' and 'employees'"}), 400

        # restPriority must be an int 1–5
        if not isinstance(rest_priority, int) or not (1 <= rest_priority <= 5):
            return jsonify({"error": "'restPriority' must be an integer between 1 and 5"}), 400

        # Capture metadata for re-injection
        id_lookup = {}
        for day_list in shifts_input:
            for sh in day_list:
                id_lookup[sh["id"]] = {
                    "employeeRole": sh["employeeRole"],
                    "candidates":   sh.get("candidates"),
                }

        # Run solver
        mip_schedule = allocate_shifts(shifts_input, employees, rest_priority)
        full_schedule = fill_in_unassigned(mip_schedule, shifts_input, employees)

        # Format output
        formatted = [[] for _ in range(7)]
        for day in range(7):
            for sh in full_schedule.get(day, []):
                formatted[day].append({
                    "id":             sh["id"],
                    "day":            day,
                    "startTime":      sh["startTime"],
                    "endTime":        sh["endTime"],
                    "employeeRole":   sh["employeeRole"],
                    "candidates":     sh["candidates"],
                    "employee":       sh.get("employee"),
                    "finalCandidate": sh.get("finalCandidate"),
                    "color":          sh.get("color", "bg-gray-500"),
                })

        print("🔍 Memory usage (MB):", psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2)
        return jsonify({"shifts": formatted}), 200

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return jsonify({"error": str(e)}), 500
