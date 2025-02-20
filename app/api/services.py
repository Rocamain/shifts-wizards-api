from ortools.linear_solver import pywraplp
from math import floor, ceil

# Mapping solver status codes to descriptive labels.
SOLVER_STATUS_LABELS = {
    pywraplp.Solver.FEASIBLE: 'suboptimal',
    pywraplp.Solver.INFEASIBLE: 'infeasible',
    pywraplp.Solver.OPTIMAL: 'optimal',
    pywraplp.Solver.UNBOUNDED: 'unbounded'
}

def time_str_to_decimal(time_str):
    """Convert a time string in HH:MM format to a decimal hour value."""
    hours, minutes = map(int, time_str.split(":"))
    return hours + minutes / 60.0

def allocate_shifts(shift_schedule, staff_members):
    # Initialize the solver with the SCIP backend.
    solver_backend = 'SCIP'
    solver_instance = pywraplp.Solver.CreateSolver(solver_backend)
    if not solver_instance:
        raise ValueError("SCIP Solver could not be created!")

    # Add a placeholder staff member for shifts that cannot be covered by real staff.
    placeholder_staff = {
        "name": "Dummy",
        "id": "placeholder",
        "contractHours": float('inf'),
        "unavailableDates": [],
        "color": "bg-gray-500"
    }
    real_staff_count = len(staff_members)
    staff_members.append(placeholder_staff)
    placeholder_index = len(staff_members) - 1

    days_count = len(shift_schedule)
    total_shift_count = sum(len(day_shifts) for day_shifts in shift_schedule)
    staff_count = len(staff_members)
    if staff_count == 0:
        raise ValueError("No staff available for scheduling.")

    # Calculate the average length of a shift (subtracting a break for shifts lasting 8 hours or more).
    sum_shift_hours = sum(
        (time_str_to_decimal(shift_detail["endTime"]) - time_str_to_decimal(shift_detail["startTime"]) -
         (0.5 if (time_str_to_decimal(shift_detail["endTime"]) - time_str_to_decimal(shift_detail["startTime"])) >= 8 else 0))
        for day_shifts in shift_schedule for shift_detail in day_shifts
    )
    average_shift_length = sum_shift_hours / total_shift_count if total_shift_count > 0 else 7.5
    print(f"📊 Average Shift Length: {average_shift_length:.2f} hours")

    # Decision variables: assignment_vars[(day, shift_index, staff_index)] is 1 if the staff member is assigned that shift.
    assignment_vars = {}
    for day in range(days_count):
        for shift_index in range(len(shift_schedule[day])):
            for staff_index in range(staff_count):
                assignment_vars[(day, shift_index, staff_index)] = solver_instance.BoolVar(
                    f'shift_{day}_{shift_index}_{staff_index}'
                )

    # Limit assignments based on eligibility: if a staff member is not a candidate for a shift, force the assignment to 0.
    for day in range(days_count):
        for shift_index, shift_detail in enumerate(shift_schedule[day]):
            for staff_index, staff in enumerate(staff_members):
                if (staff["id"] not in shift_detail["candidates"]) and (staff["id"] != "placeholder"):
                    solver_instance.Add(assignment_vars[(day, shift_index, staff_index)] == 0)

    # Each actual staff member can work at most one shift per day.
    for staff_index in range(staff_count):
        if staff_index == placeholder_index:
            continue
        for day in range(days_count):
            solver_instance.Add(solver_instance.Sum(
                assignment_vars[(day, shift_index, staff_index)]
                for shift_index in range(len(shift_schedule[day]))
            ) <= 1)

    # Ensure every shift is covered by exactly one staff member (real or placeholder).
    for day in range(days_count):
        for shift_index in range(len(shift_schedule[day])):
            eligible_staff = [staff_index for staff_index, staff in enumerate(staff_members)
                              if (staff["id"] in shift_schedule[day][shift_index]["candidates"]) or (staff["id"] == "placeholder")]
            solver_instance.Add(solver_instance.Sum(assignment_vars[(day, shift_index, staff_index)]
                                                      for staff_index in eligible_staff) == 1)

    # Enforce a minimum of 11 hours of rest between shifts on consecutive days.
    for staff_index, staff in enumerate(staff_members):
        if staff_index == placeholder_index:
            continue
        for day in range(days_count - 1):
            for i, shift_current in enumerate(shift_schedule[day]):
                for j, shift_next in enumerate(shift_schedule[day+1]):
                    rest_period = (24 - time_str_to_decimal(shift_current["endTime"])) + time_str_to_decimal(shift_next["startTime"])
                    if rest_period < 11:
                        solver_instance.Add(assignment_vars[(day, i, staff_index)] +
                                            assignment_vars[(day+1, j, staff_index)] <= 1)

    # Enforce staff unavailability constraints.
    for staff_index, staff in enumerate(staff_members):
        if staff["id"] == "placeholder":
            continue
        for unavail_entry in staff.get("unavailableDates", []):
            unavailable_day = unavail_entry["day"]
            unavailable_start = time_str_to_decimal(unavail_entry["timeFrame"]["start"])
            unavailable_end = time_str_to_decimal(unavail_entry["timeFrame"]["end"])
            for shift_index, shift_detail in enumerate(shift_schedule[unavailable_day]):
                shift_start = time_str_to_decimal(shift_detail["startTime"])
                shift_end = time_str_to_decimal(shift_detail["endTime"])
                if shift_end > unavailable_start and shift_start < unavailable_end:
                    solver_instance.Add(assignment_vars[(unavailable_day, shift_index, staff_index)] == 0)

    # Define off-day indicators and bonuses for consecutive off days.
    day_off_indicator = {}
    for staff_index, staff in enumerate(staff_members):
        if staff_index == placeholder_index:
            continue
        for day in range(days_count):
            day_off_indicator[(day, staff_index)] = solver_instance.NumVar(0, 1, f'off_{day}_{staff_index}')
            solver_instance.Add(day_off_indicator[(day, staff_index)] == 1 - solver_instance.Sum(
                assignment_vars[(day, shift_index, staff_index)]
                for shift_index in range(len(shift_schedule[day]))
            ))
    triple_off_block = {}
    for staff_index, staff in enumerate(staff_members):
        if staff_index == placeholder_index:
            continue
        for day in range(days_count - 2):
            triple_off_block[(day, staff_index)] = solver_instance.BoolVar(f'block3_{day}_{staff_index}')
            solver_instance.Add(triple_off_block[(day, staff_index)] <= day_off_indicator[(day, staff_index)])
            solver_instance.Add(triple_off_block[(day, staff_index)] <= day_off_indicator[(day+1, staff_index)])
            solver_instance.Add(triple_off_block[(day, staff_index)] <= day_off_indicator[(day+2, staff_index)])
            solver_instance.Add(triple_off_block[(day, staff_index)] >= day_off_indicator[(day, staff_index)] +
                                day_off_indicator[(day+1, staff_index)] +
                                day_off_indicator[(day+2, staff_index)] - 2)
    double_off_block = {}
    for staff_index, staff in enumerate(staff_members):
        if staff_index == placeholder_index:
            continue
        for day in range(days_count - 1):
            double_off_block[(day, staff_index)] = solver_instance.BoolVar(f'block2_{day}_{staff_index}')
            solver_instance.Add(double_off_block[(day, staff_index)] <= day_off_indicator[(day, staff_index)])
            solver_instance.Add(double_off_block[(day, staff_index)] <= day_off_indicator[(day+1, staff_index)])
            solver_instance.Add(double_off_block[(day, staff_index)] >= day_off_indicator[(day, staff_index)] +
                                day_off_indicator[(day+1, staff_index)] - 1)

    # ---------------------------
    # Soft Balance & Contract Constraints
    #
    # Calculate the ideal number of shifts per real staff member.
    ideal_shift_count = total_shift_count / real_staff_count
    print(f"Balanced target (ignoring contracts): {ideal_shift_count:.2f} shifts per employee")

    # Determine the maximum number of shifts each staff member can work based on their contract hours.
    max_shifts_by_contract = {}
    for staff_index, staff in enumerate(staff_members[:real_staff_count]):
        max_shifts_by_contract[staff_index] = floor(staff["contractHours"] / average_shift_length)
        print(f"Employee {staff['id']} (contract {staff['contractHours']} hrs) allowed shifts: {max_shifts_by_contract[staff_index]}")

    # Introduce slack variables to softly enforce a balanced shift distribution.
    deviation_lower = {}
    deviation_upper = {}
    total_assigned_shifts = {}
    for staff_index in range(real_staff_count):
        total_assigned_shifts[staff_index] = solver_instance.Sum(
            assignment_vars[(day, shift_index, staff_index)]
            for day in range(days_count)
            for shift_index in range(len(shift_schedule[day]))
        )
        lower_target = min(floor(ideal_shift_count), max_shifts_by_contract[staff_index])
        upper_target = min(ceil(ideal_shift_count), max_shifts_by_contract[staff_index])
        deviation_lower[staff_index] = solver_instance.NumVar(0, days_count, f"dev_low_{staff_index}")
        deviation_upper[staff_index] = solver_instance.NumVar(0, days_count, f"dev_high_{staff_index}")
        # Soft constraints: total_assigned_shifts should ideally be between lower_target and upper_target,
        # while allowing some flexibility.
        solver_instance.Add(total_assigned_shifts[staff_index] + deviation_lower[staff_index] >= lower_target)
        solver_instance.Add(total_assigned_shifts[staff_index] - deviation_upper[staff_index] <= upper_target)
        # Hard cap based on contract limits.
        solver_instance.Add(total_assigned_shifts[staff_index] <= max_shifts_by_contract[staff_index])

    # Allow placeholder assignments when necessary, but heavily penalize them.
    placeholder_penalty = 10000  # High penalty to discourage placeholder usage.

    # ---------------------------
    # Objective: maximize real shift assignments and consecutive off-day bonuses,
    # while penalizing imbalances and placeholder usage.
    bonus_bonus_three_day = 100
    bonus_bonus_two_day = 50
    balance_penalty = 1000

    objective_func = solver_instance.Objective()
    # Reward each assignment to a real staff member.
    for day in range(days_count):
        for shift_index in range(len(shift_schedule[day])):
            for staff_index in range(staff_count):
                if staff_index != placeholder_index:
                    objective_func.SetCoefficient(assignment_vars[(day, shift_index, staff_index)], 1)
            # Apply a heavy penalty for assigning a shift to the placeholder.
            objective_func.SetCoefficient(assignment_vars[(day, shift_index, placeholder_index)], -placeholder_penalty)

    # Add bonuses for consecutive off-day blocks and penalize slack deviations.
    for staff_index in range(real_staff_count):
        for day in range(days_count - 2):
            objective_func.SetCoefficient(triple_off_block[(day, staff_index)], bonus_bonus_three_day)
        for day in range(days_count - 1):
            objective_func.SetCoefficient(double_off_block[(day, staff_index)], bonus_bonus_two_day)
        objective_func.SetCoefficient(deviation_lower[staff_index], -balance_penalty)
        objective_func.SetCoefficient(deviation_upper[staff_index], -balance_penalty)
    objective_func.SetMaximization()

    solution_status = solver_instance.Solve()

    if solution_status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        print("\n✅ Solver Found a Solution")
        for staff_index in range(real_staff_count):
            assigned_shifts = total_assigned_shifts[staff_index].solution_value()
            slack_lower = deviation_lower[staff_index].solution_value()
            slack_upper = deviation_upper[staff_index].solution_value()
            print(f"Employee {staff_members[staff_index]['id']} assigned: {assigned_shifts:.1f} shifts, "
                  f"dev_low: {slack_lower:.1f}, dev_high: {slack_upper:.1f}")
    else:
        print("\n❌ No solution found (INFEASIBLE or UNBOUNDED)")
        print("🛑 Potential Issues:")
        print("- Too many shifts vs. available working hours (given contract limitations)")
        print("- Staff candidate availability may be too restrictive")

    # Construct the final schedule based on the solver's assignments.
    final_schedule = {}
    if solution_status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        for day, day_shifts in enumerate(shift_schedule):
            final_schedule[day] = []
            for shift_index, shift_detail in enumerate(day_shifts):
                assignment_found = False
                for staff_index, staff in enumerate(staff_members):
                    key = (day, shift_index, staff_index)
                    if assignment_vars[key].solution_value() > 0.5:
                        if staff["id"] == "placeholder":
                            print(f"⚠️ No real staff assigned to shift {shift_detail['startTime']} - {shift_detail['endTime']} on day {day}")
                            final_schedule[day].append({
                                "id": shift_detail["id"],
                                "day": day,
                                "startTime": shift_detail["startTime"],
                                "endTime": shift_detail["endTime"],
                                "candidates": shift_detail["candidates"],
                                "finalCandidate": None,
                                "employee": None,
                                "color": "bg-gray-500"
                            })
                        else:
                            print(f"📌 Assigning {staff['id']} to shift {shift_detail['startTime']} - {shift_detail['endTime']} on day {day}")
                            final_schedule[day].append({
                                "id": shift_detail["id"],
                                "day": day,
                                "startTime": shift_detail["startTime"],
                                "endTime": shift_detail["endTime"],
                                "candidates": shift_detail["candidates"],
                                "finalCandidate": staff["id"],
                                "employee": staff["id"],
                                "color": staff.get("color", "bg-gray-500")
                            })
                        assignment_found = True
                        break
                if not assignment_found:
                    print(f"⚠️ No staff assigned to shift {shift_detail['startTime']} - {shift_detail['endTime']} on day {day}")
                    final_schedule[day].append({
                        "id": shift_detail["id"],
                        "day": day,
                        "startTime": shift_detail["startTime"],
                        "endTime": shift_detail["endTime"],
                        "candidates": shift_detail["candidates"],
                        "finalCandidate": None,
                        "employee": None,
                        "color": "bg-gray-500"
                    })
    return final_schedule
