from ortools.linear_solver import pywraplp
from math import floor, ceil
from typing import List, Dict, Any
import json
# other imports as needed...

def allocate_shifts(shifts_input: List[List[Dict[str, Any]]], employees: List[Dict[str, Any]], rest_priority: int):
    '''Example allocate_shifts function: assign shifts respecting contract-hour caps.'''
    # ---- Begin actual allocation logic ----
    # (Placeholder logic - replace with real MIP solver logic)
    # For demonstration, assign no one (all unassigned)
    days = len(shifts_input)
    schedule = {day: [] for day in range(days)}
    for day_idx in range(days):
        for shift in shifts_input[day_idx]:
            rec = {
                'id': shift.get('id'),
                'startTime': shift.get('startTime'),
                'endTime': shift.get('endTime'),
                'employee': None,
                'finalCandidate': None,
                'color': None
            }
            schedule[day_idx].append(rec)
    # ---- End actual allocation logic ----

    # Log input and output to file
    try:
        record = {
            'function': 'allocate_shifts',
            'input': {
                'shifts': shifts_input,
                'employees': employees,
                'restPriority': rest_priority
            },
            'output': schedule
        }
        with open('result.json', 'a') as f:
            json.dump(record, f)
            f.write("\n")
    except Exception as e:
        print(f"⚠️ Failed to write allocate_shifts log: {e}")

    return schedule


def fill_in_unassigned(
    final_schedule: Dict[int, List[Dict[str, Any]]],
    shift_schedule: List[List[Dict[str, Any]]],
    staff_members: List[Dict[str, Any]]
) -> Dict[int, List[Dict[str, Any]]]:
    '''Take the MIP output (some shifts marked 'unassigned') and greedily assign them.'''
    # ---- Begin fill logic ----
    num_real_staff  = len(staff_members)
    days = len(shift_schedule)

    # Build current_hours & assigned_shifts
    current_hours   = {j: 0.0 for j in range(num_real_staff)}
    assigned_shifts = {j: [] for j in range(num_real_staff)}
    for d in range(days):
        for sh in final_schedule.get(d, []):
            emp = sh.get('employee')
            if emp and emp != 'unassigned':
                for j, staff in enumerate(staff_members):
                    if staff.get('id') == emp:
                        assigned_shifts[j].append(sh)
                        try:
                            h1, m1 = map(int, sh.get('startTime', '0:00').split(':'))
                            h2, m2 = map(int, sh.get('endTime', '0:00').split(':'))
                            duration = (h2 + m2/60) - (h1 + m1/60)
                            current_hours[j] += duration
                        except:
                            pass
                        break

    # Assign unassigned
    for d in range(days):
        for sh in shift_schedule[d]:
            already = any(rec.get('id') == sh.get('id') for rec in final_schedule.get(d, []))
            if already:
                continue
            best_j = None
            min_hours = float('inf')
            for j in range(num_real_staff):
                if current_hours[j] < min_hours:
                    best_j = j
                    min_hours = current_hours[j]
            if best_j is not None:
                staff_rec = staff_members[best_j]
                rec = dict(sh)
                rec.update(
                    employee=staff_rec.get('id'),
                    finalCandidate=staff_rec.get('id'),
                    color=staff_rec.get('color', 'bg-gray-500')
                )
                try:
                    h1, m1 = map(int, sh.get('startTime', '0:00').split(':'))
                    h2, m2 = map(int, sh.get('endTime', '0:00').split(':'))
                    duration = (h2 + m2/60) - (h1 + m1/60)
                    current_hours[best_j] += duration
                except:
                    pass
                final_schedule.setdefault(d, []).append(rec)
            else:
                rec = dict(sh)
                rec.update(
                    employee='unassigned',
                    finalCandidate='unassigned',
                    color='bg-gray-500'
                )
                final_schedule.setdefault(d, []).append(rec)
    # ---- End fill logic ----

    # Log input and output to file
    try:
        record = {
            'function': 'fill_in_unassigned',
            'input': {
                'final_schedule': final_schedule,
                'shift_schedule': shift_schedule,
                'staff_members': staff_members
            },
            'output': final_schedule
        }
        with open('result.json', 'a') as f:
            json.dump(record, f)
            f.write("\n")
    except Exception as e:
        print(f"⚠️ Failed to write fill_in_unassigned log: {e}")


# restPriority → big weights
REST_PRIORITY = {
    1: {"assign_w":    4_000, "placeholder_p": 10_000, "bonus_3d":  500, "bonus_2d":  500},
    2: {"assign_w":    4_000, "placeholder_p": 10_000, "bonus_3d":1_000, "bonus_2d":  500},
    3: {"assign_w":    4_000, "placeholder_p": 10_000, "bonus_3d":1_500, "bonus_2d":1_000},
    4: {"assign_w":    4_000, "placeholder_p": 10_000, "bonus_3d":2_500, "bonus_2d":1_250},
    5: {"assign_w":    4_000, "placeholder_p": 10_000, "bonus_3d":3_500, "bonus_2d":1_250},
}


def time_str_to_decimal(time_str: str) -> float:
    """Convert a time string in HH:MM or HH.MM format to decimal hours."""
    sep = "." if "." in time_str and ":" not in time_str else ":"
    hours, minutes = map(int, time_str.split(sep))
    return hours + minutes / 60.0

def allocate_shifts(
    shift_schedule,
    staff_members,
    rest_priority: int = 3,
):
    print(shift_schedule)
    params        = REST_PRIORITY.get(rest_priority, REST_PRIORITY[3])
    assign_w      = params["assign_w"]
    placeholder_p = params["placeholder_p"]
    bonus_3d      = params["bonus_3d"]
    bonus_2d      = params["bonus_2d"]

    # 1. Every shift must list at least one candidate
    missing = []
    for d, day in enumerate(shift_schedule):
        for sh in day:
            if not sh.get("candidates"):
                missing.append({"day": d, "shiftId": sh.get("id"), "role": sh.get("employeeRole")})
    if missing:
        raise ValueError(f"No candidates provided for shifts: {missing}")

    # 2. Create SCIP solver
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        raise RuntimeError("Could not create SCIP solver")
    solver.set_time_limit(20_000)

    # 3. Placeholder “dummy” staff
    placeholder = {
        "id": "placeholder", "name": "Dummy",
        "contractHours": float("inf"), "unavailableDates": [],
        "color": "bg-gray-500", "role": None,
    }
    num_real_staff  = len(staff_members)
    staff           = staff_members + [placeholder]
    placeholder_idx = len(staff) - 1
    days            = len(shift_schedule)

    # 4. Decision variables x[(day_idx, shift_idx, emp_idx)]
    x = {}
    for day_idx in range(days):
        for shift_idx, shift in enumerate(shift_schedule[day_idx]):
            cands = shift["candidates"]
            # one BoolVar for each real candidate
            for emp_idx, emp in enumerate(staff_members):
                if emp["id"] in cands:
                    x[(day_idx, shift_idx, emp_idx)] = solver.BoolVar(f"x_{day_idx}_{shift_idx}_{emp_idx}")
            # always one BoolVar for the placeholder
            x[(day_idx, shift_idx, placeholder_idx)] = solver.BoolVar(f"x_{day_idx}_{shift_idx}_{placeholder_idx}")

     # 5. At most one shift per real staff per day
    for emp_idx in range(num_real_staff):
        for day_idx in range(days):
             # collect every BoolVar for (day_idx, *, emp_idx)
            daily_vars = [
                 x_var
                 for shift_idx in range(len(shift_schedule[day_idx]))
                 if (day_idx, shift_idx, emp_idx) in x
                 for x_var in [ x.get((day_idx, shift_idx, emp_idx)) ]
             ]

                     # enforce sum(daily_vars) <= 1
            solver.Add(sum(daily_vars) <= 1)


    # 6. Cover every shift exactly once
    for day_idx in range(days):
        for shift_idx, sh in enumerate(shift_schedule[day_idx]):
            eligibility = [
                key
                for key in x
                if key[0] == day_idx and key[1] == shift_idx
            ]
            solver.Add(sum(x[k] for k in eligibility) == 1)

    # 7. Enforce 11h rest between consecutive days
    for emp_idx in range(num_real_staff):
        for day_idx in range(days - 1):
            for shift_idx, shift in enumerate(shift_schedule[day_idx]):
                today_var = x.get((day_idx, shift_idx, emp_idx))
                if not today_var:
                    continue
                end_time = time_str_to_decimal(shift["endTime"])
                for next_idx, next_shift in enumerate(shift_schedule[day_idx + 1]):
                    tomorrow_var = x.get((day_idx + 1, next_idx, emp_idx))
                    if not tomorrow_var:
                        continue
                    start_time = time_str_to_decimal(next_shift["startTime"])
                    if (24 - end_time + start_time) < 11:
                        solver.Add(today_var + tomorrow_var <= 1)

    # 8. Honor unavailability
    for emp_idx, emp in enumerate(staff_members):
        for un in emp.get("unavailableDates", []):
            d_off = un["day"]
            start = time_str_to_decimal(un["timeFrame"]["start"])
            end   = time_str_to_decimal(un["timeFrame"]["end"])
            for shift_idx, shift in enumerate(shift_schedule[d_off]):
                var = x.get((d_off, shift_idx, emp_idx))
                if var:
                    ss = time_str_to_decimal(shift["startTime"])
                    se = time_str_to_decimal(shift["endTime"])
                    if se > start and ss < end:
                        solver.Add(var == 0)

    # 9. Track hours per staff
    h = {}
    for emp_idx, emp in enumerate(staff_members):
        h_var = solver.NumVar(0, emp["contractHours"], f"h_{emp_idx}")
        terms = []
        for day_idx in range(days):
            for shift_idx, shift in enumerate(shift_schedule[day_idx]):
                var = x.get((day_idx, shift_idx, emp_idx))
                if var:
                    raw = (time_str_to_decimal(shift["endTime"])
                         - time_str_to_decimal(shift["startTime"]))
                    length = raw - 0.5 if raw >= 8 else raw
                    terms.append(length * var)
        solver.Add(h_var == sum(terms))
        h[emp_idx] = h_var

    # 10. Off‐day indicators & bonuses (2‐day & 3‐day)
    off_day    = {}
    two_day    = {}
    three_day  = {}
    for emp_idx in range(num_real_staff):
        for day_idx in range(days):
            v = solver.NumVar(0, 1, f"off_{day_idx}_{emp_idx}")
            off_day[(day_idx, emp_idx)] = v
            work_vars = [
                x[(day_idx, sidx, emp_idx)]
                for sidx in range(len(shift_schedule[day_idx]))
                if (day_idx, sidx, emp_idx) in x
            ]
            solver.Add(v + sum(work_vars) == 1)

        for day_idx in range(days - 1):
            t2 = solver.BoolVar(f"two_{day_idx}_{emp_idx}")
            two_day[(day_idx, emp_idx)] = t2
            solver.Add(t2 <= off_day[(day_idx,    emp_idx)])
            solver.Add(t2 <= off_day[(day_idx+1,  emp_idx)])
            solver.Add(t2 >= off_day[(day_idx,    emp_idx)]
                            + off_day[(day_idx+1,emp_idx)] - 1)

        for day_idx in range(days - 2):
            t3 = solver.BoolVar(f"three_{day_idx}_{emp_idx}")
            three_day[(day_idx, emp_idx)] = t3
            solver.Add(t3 <= off_day[(day_idx,    emp_idx)])
            solver.Add(t3 <= off_day[(day_idx+1,  emp_idx)])
            solver.Add(t3 <= off_day[(day_idx+2,  emp_idx)])
            solver.Add(t3 >= (off_day[(day_idx,   emp_idx)]
                            + off_day[(day_idx+1,emp_idx)]
                            + off_day[(day_idx+2,emp_idx)] - 2))

    # 11. Objective: assign_w + ranking bonus, minus placeholder_p, plus off‐block bonuses
    obj = solver.Objective()
    # 11a) assignment & placeholder
    for day_idx in range(days):
        for shift_idx, shift in enumerate(shift_schedule[day_idx]):
            cands   = shift["candidates"]
            n_c     = len(cands)
            for emp_idx in range(num_real_staff):
                key = (day_idx, shift_idx, emp_idx)
                if key in x:
                    try:
                        rank  = cands.index(staff_members[emp_idx]["id"])
                        bonus = n_c - rank
                    except ValueError:
                        bonus = 0
                    obj.SetCoefficient(x[key], assign_w + bonus)
            # placeholder penalty
            plc_key = (day_idx, shift_idx, placeholder_idx)
            obj.SetCoefficient(x[plc_key], -placeholder_p)

    # 11b) off‐block bonuses
    for emp_idx in range(num_real_staff):
        for day_idx in range(days - 2):
            obj.SetCoefficient(three_day[(day_idx, emp_idx)], bonus_3d)
        for day_idx in range(days - 1):
            obj.SetCoefficient(two_day[(day_idx, emp_idx)],   bonus_2d)

    obj.SetMaximization()

    # 12. Solve & extract
    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        raise RuntimeError(f"Solver failed with status {status}")

    final_schedule = {d: [] for d in range(days)}
    for day_idx in range(days):
        for shift_idx, shift in enumerate(shift_schedule[day_idx]):
            # find which var won
            for key in x:
                d, s, emp_idx = key
                if d == day_idx and s == shift_idx and x[key].solution_value() > 0.5:
                    rec = dict(shift)
                    staff_rec = staff[emp_idx]
                    if staff_rec["id"] == "placeholder":
                        rec.update(employee="unassigned", finalCandidate="unassigned", color="bg-gray-500")
                    else:
                        rec.update(employee=staff_rec["id"], finalCandidate=staff_rec["id"],
                                   color=staff_rec.get("color", "bg-gray-500"))
                    final_schedule[day_idx].append(rec)
                    break

    return final_schedule




def fill_in_unassigned(
    final_schedule,
    shift_schedule,
    staff_members
):
    """
    Take the MIP output (some shifts marked “unassigned”) and greedily
    assign them to people even if it exceeds their contractHours—still
    enforcing 13h rest and trying to balance by giving to whoever has
    the fewest hours so far.
    """
    num_real_staff  = len(staff_members)
    days = len(shift_schedule)

    # 1. Build current_hours & assigned_shifts for each real staff
    current_hours   = {j: 0.0 for j in range(num_real_staff )}
    assigned_shifts = {j: [] for j in range(num_real_staff )}
    unassigned_list = []

    for d in range(days):
        for i, sh in enumerate(shift_schedule[d]):
            recs = final_schedule.get(d, [])
            assigned = next((r for r in recs if r["id"] == sh["id"]), None)
            if assigned is None or assigned.get("employee") == "unassigned":
                unassigned_list.append((d, i, sh))
            else:
                sid = assigned["employee"]
                for j_index, staff_j in enumerate(staff_members):
                    if staff_j["id"] == sid:
                        length = time_str_to_decimal(sh["endTime"]) - time_str_to_decimal(sh["startTime"])
                        if length >= 8:
                            length -= 0.5
                        current_hours[j_index] += length
                        assigned_shifts[j_index].append((d, sh["startTime"], sh["endTime"]))
                        break

    # 2. Helper to enforce 13h rest
    def can_rest(j, day, start_time):
        candidate_start = time_str_to_decimal(start_time)
        cand_abs        = day * 24 + candidate_start
        for (d2, _, e2) in assigned_shifts[j]:
            abs_end2 = d2 * 24 + time_str_to_decimal(e2)
            if abs_end2 + 13 > cand_abs and abs_end2 <= cand_abs:
                return False
        for (d2, s2, _) in assigned_shifts[j]:
            abs_start2 = d2 * 24 + time_str_to_decimal(s2)
            if cand_abs + 13 > abs_start2 and abs_start2 >= cand_abs:
                return False
        return True

    # 3. Helper to compute lost off-day bonus if forced to work “day”
    def lost_off_penalty(j, day):
        has_shift = {d: False for d in range(days)}
        for (d2, _, _) in assigned_shifts[j]:
            has_shift[d2] = True
        off_days = {d for d in range(days) if not has_shift[d]}

        if day not in off_days:
            return 0

        before_2 = 0
        before_3 = 0
        for start in range(max(0, day - 1), min(days - 1, day) + 1):
            if start + 1 < days and {start, start + 1}.issubset(off_days):
                before_2 += 1
        for start in range(max(0, day - 2), min(days - 3, day) + 1):
            if start + 2 < days and {start, start + 1, start + 2}.issubset(off_days):
                before_3 += 1

        off_days.remove(day)

        after_2 = 0
        after_3 = 0
        for start in range(max(0, day - 1), min(days - 1, day) + 1):
            if start + 1 < days and {start, start + 1}.issubset(off_days):
                after_2 += 1
        for start in range(max(0, day - 2), min(days - 3, day) + 1):
            if start + 2 < days and {start, start + 1, start + 2}.issubset(off_days):
                after_3 += 1

        params  = REST_PRIORITY[3]
        lost_2  = before_2 - after_2
        lost_3  = before_3 - after_3
        return lost_2 * params["bonus_2d"] + lost_3 * params["bonus_3d"]

    # 4. Greedily assign each unassigned shift
    for (d, i, sh) in unassigned_list:
        length = time_str_to_decimal(sh["endTime"]) - time_str_to_decimal(sh["startTime"])
        if length >= 8:
            length -= 0.5

        best_score = float("inf")
        best_j     = None
        candidates = sh["candidates"]

        for j_index, staff_j in enumerate(staff_members):
            if staff_j["id"] not in candidates:
                continue
            if not can_rest(j_index, d, sh["startTime"]):
                continue
            # NO contract‐hours check here (we allow exceeding)
            penalty = lost_off_penalty(j_index, d)
            # We simply prefer whoever has fewer hours so far, then break ties
            score   = (current_hours[j_index] + length) + penalty / (
                REST_PRIORITY[3]["bonus_3d"] + REST_PRIORITY[3]["bonus_2d"]
            )
            if score < best_score:
                best_score = score
                best_j     = j_index

        if best_j is not None:
            # assign to best_j, even if it pushes them past contractHours
            current_hours[best_j] += length
            assigned_shifts[best_j].append((d, sh["startTime"], sh["endTime"]))
            rec = dict(sh)
            rec.update(
                employee=staff_members[best_j]["id"],
                finalCandidate=staff_members[best_j]["id"],
                color=staff_members[best_j].get("color", "bg-gray-500")
            )
            final_schedule[d].append(rec)
        else:
            # Still unassignable: remain “unassigned”
            rec = dict(sh)
            rec.update(
                employee="unassigned",
                finalCandidate="unassigned",
                color="bg-gray-500"
            )
            final_schedule[d].append(rec)

    return final_schedule
