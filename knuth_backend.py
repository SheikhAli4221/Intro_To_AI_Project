import math
import threading
import time
from collections import deque
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Exact arithmetic helpers
# ---------------------------------------------------------------------------

def int_root_floor(N: int, k: int) -> int:
    """Compute floor(N^(1/2^k)) exactly via repeated isqrt."""
    v = N
    for _ in range(k):
        v = math.isqrt(v)
    return v

def exact_value_is_integer(N: int, k: int) -> bool:
    """True if N^(1/2^k) is exactly an integer."""
    if k == 0:
        return True
    v = N
    for _ in range(k):
        r = math.isqrt(v)
        if r * r != v:
            return False
        v = r
    return True

def exact_integer_value(N: int, k: int) -> int:
    """Return exact integer value when exact_value_is_integer() is True."""
    v = N
    for _ in range(k):
        v = math.isqrt(v)
    return v

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------
MAX_N_BITS        = 200_000
MAX_FACTORIAL_ARG = 100_000
MAX_K             = 300

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
solutions           = {}
is_computing        = False
states_explored     = 0
new_solutions_queue = []
_lock               = threading.Lock()

# ---------------------------------------------------------------------------
# BFS — daemon thread
# ---------------------------------------------------------------------------

def run_bfs_solver():
    global solutions, is_computing, states_explored, new_solutions_queue

    _targets_remaining = set(range(1, 101))
    _visited           = set()
    _queue             = deque()

    _visited.add((4, 0))
    _queue.append((4, 0, "4"))

    if 4 in _targets_remaining:
        solutions[4] = "4"
        _targets_remaining.discard(4)
        with _lock:
            new_solutions_queue.append({'target': 4, 'solution': "4"})

    while _queue and _targets_remaining and states_explored < 30_000_000:
        N, k, path = _queue.popleft()
        states_explored += 1

        # 1. SQRT
        if k < MAX_K:
            nN, nk = N, k + 1
            if (nN, nk) not in _visited:
                _visited.add((nN, nk))
                np = f"√({path})"
                if exact_value_is_integer(nN, nk):
                    val = exact_integer_value(nN, nk)
                    if val in _targets_remaining:
                        solutions[val] = np
                        _targets_remaining.discard(val)
                        with _lock:
                            new_solutions_queue.append({'target': val, 'solution': np})
                _queue.append((nN, nk, np))

        # 2. FLOOR
        if k > 0:
            if N.bit_length() > MAX_N_BITS:
                continue
            fv = int_root_floor(N, k)
            nN, nk = fv, 0
            if (nN, nk) not in _visited:
                _visited.add((nN, nk))
                np = f"⌊{path}⌋"
                if fv in _targets_remaining:
                    solutions[fv] = np
                    _targets_remaining.discard(fv)
                    with _lock:
                        new_solutions_queue.append({'target': fv, 'solution': np})
                _queue.append((nN, nk, np))

        # 3. FACTORIAL
        if k == 0 and 0 <= N <= MAX_FACTORIAL_ARG:
            fval = math.factorial(N)
            if fval.bit_length() <= MAX_N_BITS:
                nN, nk = fval, 0
                if (nN, nk) not in _visited:
                    _visited.add((nN, nk))
                    np = f"({path})!"
                    if fval in _targets_remaining:
                        solutions[fval] = np
                        _targets_remaining.discard(fval)
                        with _lock:
                            new_solutions_queue.append({'target': fval, 'solution': np})
                    _queue.append((nN, nk, np))

        if not _targets_remaining:
            break

        if states_explored % 2000 == 0:
            time.sleep(0.001)

    is_computing = False

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/api/status')
def status():
    return jsonify({
        'ready': True,
        'solved': len(solutions),
        'total': 100,
        'is_computing': is_computing
    })

@app.route('/api/start_solve', methods=['GET', 'POST'])
def start_solve():
    global is_computing, solutions, new_solutions_queue, states_explored
    if not is_computing:
        solutions.clear()
        states_explored = 0
        is_computing = True
        with _lock:
            new_solutions_queue.clear()
        threading.Thread(target=run_bfs_solver, daemon=True).start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/api/poll_progress')
def poll_progress():
    with _lock:
        batch = list(new_solutions_queue)
        new_solutions_queue.clear()
    done = (not is_computing) and (len(batch) == 0)
    return jsonify({
        'new_solutions': batch,
        'done': done,
        'states_explored': states_explored,
        'total_solved': len(solutions)
    })
@app.route('/api/solve/<int:val>')
def solve_single(val):
    if not (1 <= val <= 100):
        return jsonify({'found': False, 'target': val}), 400
    if val in solutions:
        return jsonify({'found': True, 'target': val, 'solution': solutions[val]})
    return jsonify({'found': False, 'target': val})

@app.route('/api/all_solutions')
def all_solutions():
    return jsonify({
        'solutions': solutions,
        'total_solved': len(solutions),
        'is_computing': is_computing
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)