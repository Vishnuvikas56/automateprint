from itertools import combinations
import json
def order_combinations(order_type_supported: list, printers_data: dict):
    result = {}
    n = len(order_type_supported)
    for r in range(1, n + 1):
        for combo in combinations(order_type_supported, r):
            key = ",".join(combo)
            ranked_printers = []
            for printer, supported in printers_data.items():
                if all(c in supported for c in combo):
                    extras = len(supported) - len(combo)
                    priority = (
                        extras,
                    )
                    ranked_printers.append((priority, printer))
            ranked_printers.sort(key=lambda x: x[0])
            result[key] = [printer for _, printer in ranked_printers]
    return result

# order_type_supported = ["color", "bw", "draft"]

# printers_data = {
#     "printer1": ["color", "bw"],
#     "printer2": ["bw", "draft"],
#     "printer3": ["color", "draft"],
#     "printer4": ["color", "bw", "draft"]
# }

# print(json.dumps(order_combinations(order_type_supported, printers_data), indent=4))

def prioritized_job_queue(default_priorities:dict, current_order:dict, printers_data, existing_queue):
    priorities = default_priorities[",".append(list(current_order.keys()))]
    printer_details = {
        "assigned_printer" : "",
        "message" : {
            "severity" : "",
            "info" : ""
        }
    }
    message = {}
    pcount_upd = 0
    for priority in priorities:
        pcount_upd += printers_data[priority]["paper_count"]
        ok = True
        for otype, req in current_order.items():
            if pcount_upd < req["paper_count"]:
                ok = False
                break
        if ok:
            assigned_printer = priority
            break
    if not assigned_printer:
        return {
                    "assigned_printer" : priorities[0], 
                    "message" : {
                        "severity" : "critical",
                        "info" : "PAPER REFILL NEEDED"
                    }
                }
    return {}


# printer_scheduler_complete.py
# Complete scheduler that:
# - Accepts an "order" as a dict with full requirements (paper_count per order type)
# - Splits order into optimal suborders if no single printer can do all
# - Scores printers with weighted factors (paper%, ink%, speed, queue, extras)
# - Returns a flat list of assigned printers in execution order (each suborder -> one printer)
#
# Usage:
#  - Provide `printers_data` (dict of printers with supported, paper_count, ink, speed, queue)
#  - Provide `order` (dict keyed by order type, each value {"paper_count": {ptype: count}})
#  - Call schedule_order(order, printers_data)
#
# Example provided at bottom.

from itertools import combinations
import copy

# ---------------------------
# Default scoring weights
# ---------------------------
DEFAULT_WEIGHTS = {
    "paper": 0.35,
    "ink": 0.30,
    "speed": 0.15,
    "queue": 0.10,
    "extras": 0.10
}

# ---------------------------
# Helpers
# ---------------------------
def _percent_score(pct):
    """Clamp 0..100 and normalize to 0..1"""
    p = max(0.0, min(100.0, pct))
    return p / 100.0

def _queue_score(queue):
    """Convert queue length (list or int) to score in (0,1], higher is better"""
    qlen = 0
    if queue is None:
        qlen = 0
    elif isinstance(queue, int):
        qlen = queue
    elif isinstance(queue, (list, tuple)):
        qlen = len(queue)
    else:
        qlen = int(queue)
    return 1.0 / (1.0 + qlen)

# ---------------------------
# PART 1: Supported combinations discovery & suborder splitting
# ---------------------------
def _valid_supported_combos(order_types, printers_data):
    """
    Return a list of sets, each set is a combo of order types supported by at least one printer.
    Larger combos first (useful for greedy covering).
    """
    order_types = list(order_types)
    combos = []
    for r in range(len(order_types), 0, -1):
        for combo in combinations(order_types, r):
            cset = set(combo)
            # check printers
            supported = False
            for pname, pinfo in printers_data.items():
                if not isinstance(pinfo, dict) or "supported" not in pinfo:
                    continue
                if cset.issubset(set(pinfo["supported"])):
                    supported = True
                    break
            if supported:
                combos.append(cset)
    # remove duplicates (same set) while preserving order
    uniq = []
    seen = set()
    for s in combos:
        key = tuple(sorted(s))
        if key not in seen:
            uniq.append(s)
            seen.add(key)
    return uniq

def generate_suborders_from_order(order, printers_data):
    """
    Input:
        order: dict mapping order_type -> {"paper_count": {ptype: count}}
    Returns:
        list of suborders (each suborder is a list of order_type strings)
    Algorithm:
        - Generate all supported combos (by printers)
        - Greedy cover: pick combo that covers the largest number of remaining order types
    Note: This is a greedy algorithm but works well for small order_type counts (typical use).
    """
    order_types = list(order.keys())
    supported_combos = _valid_supported_combos(order_types, printers_data)
    remaining = set(order_types)
    result = []

    while remaining:
        best = None
        for combo in supported_combos:
            overlap = len(combo & remaining)
            if overlap == 0:
                continue
            if best is None or overlap > len(best & remaining):
                best = combo
        if best is None:
            # No printer supports any of the remaining types => impossible to fulfill
            raise Exception(f"No printer supports remaining order types: {remaining}")
        result.append(list(best))
        remaining -= best

    return result

# ---------------------------
# PART 2: Scoring printers for a single suborder (uses full order requirements)
# ---------------------------
def score_printer_for_suborder(printer_info, suborder_req, weights):
    """
    printer_info: dict for a printer (supported, paper_count, ink, speed, queue)
    suborder_req: dict mapping order_type -> {"paper_count": {ptype: count}}
                 (this is a subset of the full order, only for the suborder's types)
    weights: scoring weights dict
    Returns:
        score (float 0..1). Returns 0 if hard-failed (insufficient paper or empty required ink channel).
    """
    # PAPER: compute remaining percentage (after allocating required papers)
    paper_remaining_pcts = []
    for otype, req in suborder_req.items():
        required_papers = req.get("paper_count", {})
        for ptype, need in required_papers.items():
            available = printer_info.get("paper_count", {}).get(ptype, 0)
            if available < need:
                # hard fail: cannot fulfill required paper
                return 0.0
            # remaining percent after consuming 'need'
            remaining_pct = (available - need) / available * 100.0 if available > 0 else 0.0
            paper_remaining_pcts.append(remaining_pct)
    paper_min_pct = min(paper_remaining_pcts) if paper_remaining_pcts else 100.0
    paper_score = _percent_score(paper_min_pct)

    # INK: evaluate required channels
    ink_info = printer_info.get("ink", {})
    ink_pcts = []
    for otype in suborder_req.keys():
        if otype == "bw":
            bl = ink_info.get("black", 0.0)
            if bl <= 0:
                return 0.0
            ink_pcts.append(bl)
        if otype == "color":
            c = ink_info.get("C", 0.0)
            m = ink_info.get("M", 0.0)
            y = ink_info.get("Y", 0.0)
            if c <= 0 or m <= 0 or y <= 0:
                return 0.0
            ink_pcts.append(min(c, m, y))
        # other order types typically don't require ink channels beyond bw/color;
        # if you have specific inks for e.g. photo black, extend here.
    ink_min_pct = min(ink_pcts) if ink_pcts else 100.0
    ink_score = _percent_score(ink_min_pct)

    # SPEED: normalize to 0..1 using cap 100 ppm. None -> neutral 0.5
    speed = printer_info.get("speed", None)
    if speed is None:
        speed_score = 0.5
    else:
        speed_score = _percent_score(min(float(speed), 100.0))

    # QUEUE: fewer is better
    queue = printer_info.get("queue", [])
    queue_score = _queue_score(queue)

    # EXTRAS: penalty for extra supported types beyond required
    supported_set = set(printer_info.get("supported", []))
    required_set = set(suborder_req.keys())
    extras_count = len(supported_set - required_set)
    extras_penalty = 1.0 - min(extras_count, 10) / 10.0  # 1.0 best, 0.0 worst

    # Weighted sum
    w_p = weights.get("paper", DEFAULT_WEIGHTS["paper"])
    w_i = weights.get("ink", DEFAULT_WEIGHTS["ink"])
    w_s = weights.get("speed", DEFAULT_WEIGHTS["speed"])
    w_q = weights.get("queue", DEFAULT_WEIGHTS["queue"])
    w_e = weights.get("extras", DEFAULT_WEIGHTS["extras"])

    score = (
        w_p * paper_score +
        w_i * ink_score +
        w_s * speed_score +
        w_q * queue_score +
        w_e * extras_penalty
    )

    # score in 0..1 range
    return float(score)

# ---------------------------
# PART 3: Assign best printer for one suborder
# ---------------------------
def assign_printer_for_suborder(suborder_types, order, printers_data, weights=DEFAULT_WEIGHTS, default_priorities=None):
    """
    suborder_types: list of order type strings (e.g. ["bw","color"])
    order: the full order dict; we will extract requirements for the suborder types
    printers_data: dict of printers
    default_priorities: optional list ordering (for tie-breaker). If None, printer alphabetical order used.
    Returns: printer name string (best match) or raises Exception if none
    """
    # Build suborder_req from order for only these types
    suborder_req = {}
    for t in suborder_types:
        if t not in order:
            raise Exception(f"Order missing requirements for type '{t}'")
        suborder_req[t] = order[t]

    candidates = []
    for pname, pinfo in printers_data.items():
        # skip non-printer meta entries (e.g., "requirements" or others)
        if not isinstance(pinfo, dict) or "supported" not in pinfo:
            continue
        # must support all types in suborder
        if not set(suborder_types).issubset(set(pinfo.get("supported", []))):
            continue
        # compute score (score=0 means cannot fulfill due to hard fail)
        s = score_printer_for_suborder(pinfo, suborder_req, weights)
        if s > 0.0:
            candidates.append((s, pname))

    if not candidates:
        raise Exception(f"No printer can handle suborder {suborder_types}")

    # sort by score desc, tie-break by default_priorities order if provided, else by name
    if default_priorities:
        # default_priorities is expected as a list of names in priority order
        candidates.sort(key=lambda x: (-x[0], default_priorities.index(x[1]) if x[1] in default_priorities else 9999))
    else:
        candidates.sort(key=lambda x: (-x[0], x[1]))

    best_printer = candidates[0][1]
    return best_printer

# ---------------------------
# PART 4: Main scheduler
# ---------------------------
def schedule_order(order, printers_data, weights=DEFAULT_WEIGHTS, default_priorities_map=None):
    # Step 1 — split into suborders
    suborders = generate_suborders_from_order(order, printers_data)

    assignments = []

    # Step 2 — assign printer for each suborder
    for s in suborders:
        combo_key = ",".join(s)
        default_priorities = None
        if default_priorities_map:
            default_priorities = default_priorities_map.get(combo_key)

        printer = assign_printer_for_suborder(
            s,
            order,
            printers_data,
            weights,
            default_priorities
        )
        assignments.append(printer)

    return assignments

def order_combinations(order_type_supported: list, printers_data: dict):
    result = {}
    n = len(order_type_supported)
    for r in range(1, n + 1):
        for combo in combinations(order_type_supported, r):
            key = ",".join(combo)
            ranked_printers = []
            for printer, pdata in printers_data.items():
                supported = pdata["supported"]
                if all(c in supported for c in combo):
                    extras = len(supported) - len(combo)
                    priority = (
                        extras,
                    )
                    ranked_printers.append((priority, printer))
            ranked_printers.sort(key=lambda x: x[0])
            result[key] = [printer for _, printer in ranked_printers]
    return result

# ---------------------------
# Example dataset and test call
# ---------------------------
if __name__ == "__main__":
    # Six printers (one with full capability) with realistic random-ish params
    printers_data = {
        "P1": {
            "supported": ["bw", "color"],
            "paper_count": {"A4": 180, "A3": 50},
            "ink": {"black": 70, "C": 60, "M": 55, "Y": 50},
            "speed": 35,
            "queue": ["job1", "job2"]
        },
        "P2": {
            "supported": ["bw", "thick"],
            "paper_count": {"A4": 90, "Thick": 40},
            "ink": {"black": 80},
            "speed": 25,
            "queue": []
        },
        "P3": {
            "supported": ["color", "glossy"],
            "paper_count": {"Glossy": 30, "A4": 70},
            "ink": {"black": 50, "C": 45, "M": 46, "Y": 42},
            "speed": 20,
            "queue": ["jobA"]
        },
        "P4": {
            "supported": ["postersize"],
            "paper_count": {"Poster": 15},
            "ink": {"black": 40, "C": 30, "M": 32, "Y": 28},
            "speed": 15,
            "queue": ["p1", "p2", "p3"]
        },
        "P5": {
            "supported": ["bw", "color", "glossy"],
            "paper_count": {"A4": 200, "Glossy": 60},
            "ink": {"black": 85, "C": 80, "M": 79, "Y": 78},
            "speed": 50,
            "queue": []
        },
        "P6": {
            "supported": ["bw", "color", "thick", "glossy", "postersize"],  # full capability
            "paper_count": {"A4": 300, "Thick": 80, "Glossy": 100, "Poster": 40},
            "ink": {"black": 95, "C": 92, "M": 93, "Y": 94},
            "speed": 65,
            "queue": []
        }
    }

    # Order must be a dict: each order type maps to its paper_count requirements
    # (you can change counts to simulate bigger/smaller jobs)
    order = {
        "bw": {"paper_count": {"A4": 2}},          # 2 A4 pages bw
        "color": {"paper_count": {"A4": 1}},       # 1 A4 color
        "glossy": {"paper_count": {"Glossy": 2}},  # 2 glossy sheets
        "postersize": {"paper_count": {"Poster": 1}}  # 1 poster sheet
    }

    # Optional: default priority map for tie-breaking (combo_key -> list)
    default_priorities_map = order_combinations(["bw", "color", "thick", "glossy", "postersize"], printers_data)

    # Run scheduler
    assigned = schedule_order(order, printers_data, weights=DEFAULT_WEIGHTS, default_priorities_map=default_priorities_map)
    print("Assigned printers (sequence):", assigned)

    # Try a single-suborder order (should likely pick P6 or P5)
    order2 = {"bw": {"paper_count": {"A4": 1}}, "color": {"paper_count": {"A4": 1}}}
    print("Assigned for simple bw+color:", schedule_order(order2, printers_data))
