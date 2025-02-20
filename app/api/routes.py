from flask import Blueprint, request, jsonify
from app.api.services import distribute_shifts  # Ensure this module is correctly imported

api = Blueprint("api", __name__)

@api.route("/schedule", methods=["POST"])
def schedule():
    try:
        data = request.json

        # Ensure JSON data is received
        if not data:
            return jsonify({"error": "Missing JSON data"}), 400

        # Validate required fields
        if "shifts" not in data or "employees" not in data:
            return jsonify({"error": "Missing required fields: 'shifts' and 'employees'"}), 400

        shifts = data["shifts"]
        employees = data["employees"]

        # 🔵 Debugging: Print the received input data
        print("\n📥 Received shifts:", shifts)
        print("\n📥 Received employees:", employees)

        # Validate input types
        if not isinstance(shifts, list) or not isinstance(employees, list):
            return jsonify({"error": "'shifts' and 'employees' must be lists"}), 400

        # Call shift distribution function with correct argument order
        schedule = distribute_shifts(shifts, employees)

        # 🔵 Debugging: Print the result before sending it back
        print("\n🔵 Generated Schedule:", schedule)


        formatted_schedule = [[] for _ in range(7)]  # 7 empty lists for each day of the week

        for day in range(7):  # Loop through Sunday (0) to Saturday (6)
            if day in schedule:
                formatted_schedule[day] = [
                    {   "id": shift["id"],
                        "day": day,
                        "startTime": shift["startTime"],
                        "endTime": shift["endTime"],
                        "employee": shift["employee"],  # This will be None if unassigned
                        "finalCandidate": shift["employee"],  # For frontend compatibility
                        'color': shift["color"]
                    }
                    for shift in schedule[day]
                ]


        response = {
            "shifts": formatted_schedule,
        }


        print('res:', response)
        return jsonify(response), 200

    except KeyError as e:
        print(f"❌ Missing Key Error: {e}")
        return jsonify({"error": f"Missing key: {str(e)}"}), 400

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return jsonify({"error": str(e)}), 500
