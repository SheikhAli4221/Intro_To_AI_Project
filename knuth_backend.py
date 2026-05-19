"""
Donald Knuth Problem Solver — Exact Arithmetic BFS
===================================================
Starting from 4, reach every integer from 1 to 100 using only:
  • Factorial  n!     (integers only)
  • Square root  √n
  • Floor  ⌊n⌋

Key insight: numbers in this search are of the form
    ⌊ √^k(N) ⌋   where N is some huge integer and k counts sqrt applications.

We represent every value EXACTLY as a pair  (N, k)  meaning  √^k(N):
  • If k=0  → value is exactly the integer N
  • If k>0  → value is the real number  N^(1/2^k)

Floor of √^k(N) = ⌊ N^(1/2^k) ⌋
  = largest integer m such that m^(2^k) ≤ N

This can be computed exactly with integer arithmetic (no floats!).

Transitions from state (N, k):
  1. sqrt:   (N, k) → (N, k+1)          [always valid]
  2. floor:  (N, k) → (floor_val, 0)    [only when k>0; result is exact int]
  3. fact:   (N, 0) → (N!, 0)           [only when k=0 and N is a small int]

Starting state: (4, 0)  representing the integer 4.
Goal: reach state whose exact value equals the target integer.
"""

import math
from collections import deque

# ---------------------------------------------------------------------------
# Integer nth-root floor  ⌊ N^(1/2^k) ⌋  using pure integer arithmetic
# ---------------------------------------------------------------------------

def int_root_floor(N: int, k: int) -> int:
    """
    Compute ⌊ N^(1/2^k) ⌋ exactly using repeated integer square roots.
    E.g. k=1 → isqrt(N),  k=2 → isqrt(isqrt(N)),  etc.
    """
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
    """Return the exact integer value when exact_value_is_integer is True."""
    v = N
    for _ in range(k):
        v = math.isqrt(v)
    return v

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

MAX_N_BITS        = 200_000   # discard N if it has more than this many bits
MAX_FACTORIAL_ARG = 100_000   # don't take factorial of numbers larger than this
MAX_K             = 300       # don't apply sqrt more than this many times in a row

# ---------------------------------------------------------------------------
# BFS
# ---------------------------------------------------------------------------

def solve_all():
    """
    Single BFS from (4, 0) that records the first path reaching each target 1-100.
    Returns dict  target -> path_string.
    """
    targets_remaining = set(range(1, 101))
    solutions = {}

    # visited: set of (N, k)  — but N can be huge, so we use id tricks.
    # Since N is always derived from 4 via factorial, we can use N itself as key.
    # To avoid hashing huge ints repeatedly we cap N bits.
    visited = set()

    def vkey(N, k):
        # For large N we only need to distinguish (N, k) pairs reachable from 4.
        # Python hashes big ints efficiently so this is fine.
        return (N, k)

    start_N, start_k = 4, 0
    visited.add(vkey(start_N, start_k))

    queue = deque()
    queue.append((start_N, start_k, "4"))

    # Check start against targets
    if 4 in targets_remaining:
        solutions[4] = "4"
        targets_remaining.discard(4)

    states_explored = 0
    MAX_STATES = 30_000_000

    while queue and targets_remaining and states_explored < MAX_STATES:
        N, k, path = queue.popleft()
        states_explored += 1

        # ---- Generate successors ----

        # 1. Apply sqrt:  (N, k) → (N, k+1)
        if k < MAX_K:
            nN, nk = N, k + 1
            key1 = vkey(nN, nk)
            if key1 not in visited:
                visited.add(key1)
                np = f"√({path})"
                # Check if this state equals any target (only if it's exact int)
                if exact_value_is_integer(nN, nk):
                    val = exact_integer_value(nN, nk)
                    if val in targets_remaining:
                        solutions[val] = np
                        targets_remaining.discard(val)
                        if not targets_remaining:
                            break
                queue.append((nN, nk, np))

        # 2. Apply floor (only useful when k > 0, otherwise it's a no-op)
        if k > 0:
            fv = int_root_floor(N, k)   # exact integer
            nN, nk = fv, 0
            key2 = vkey(nN, nk)
            if key2 not in visited:
                visited.add(key2)
                np = f"⌊{path}⌋"
                if fv in targets_remaining:
                    solutions[fv] = np
                    targets_remaining.discard(fv)
                    if not targets_remaining:
                        break
                queue.append((nN, nk, np))

        # 3. Apply factorial (only when k=0 and N is a manageable integer)
        if k == 0 and 0 <= N <= MAX_FACTORIAL_ARG:
            fval = math.factorial(N)
            nbits = fval.bit_length()
            if nbits <= MAX_N_BITS:
                nN, nk = fval, 0
                key3 = vkey(nN, nk)
                if key3 not in visited:
                    visited.add(key3)
                    np = f"({path})!"
                    if fval in targets_remaining:
                        solutions[fval] = np
                        targets_remaining.discard(fval)
                        if not targets_remaining:
                            break
                    queue.append((nN, nk, np))

    return solutions, targets_remaining

from flask import Flask, jsonify, send_file
from flask_cors import CORS
import threading
import json
import time
from collections import deque
import math

app = Flask(__name__)
CORS(app)

# Global thread-safe states
solutions = {}
is_computing = False
new_solutions_queue = [] # Jo naye solutions milenge, yahan temporary store honge
states_explored = 0

def run_bfs_solver():
    """Heavy BFS runs safely in this isolated background thread."""
    global solutions, is_computing, new_solutions_queue, states_explored
    
    _targets_remaining = set(range(1, 101))
    _visited = set()
    _queue = deque()

    _start_N, _start_k = 4, 0
    _visited.add((_start_N, _start_k))
    _queue.append((_start_N, _start_k, "4"))

    if 4 in _targets_remaining:
        solutions[4] = "4"
        _targets_remaining.discard(4)
        new_solutions_queue.append({'target': 4, 'solution': "4"})

    _MAX_STATES = 30_000_000

    while _queue and _targets_remaining and states_explored < _MAX_STATES:
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
                        new_solutions_queue.append({'target': val, 'solution': np})
                _queue.append((nN, nk, np))

        # 2. FLOOR
        if k > 0:
            if hasattr(N, 'bit_length') and N.bit_length() > 500000:
                continue
            fv = int_root_floor(N, k)
            nN, nk = fv, 0
            if (nN, nk) not in _visited:
                _visited.add((nN, nk))
                np = f"⌊{path}⌋"
                if fv in _targets_remaining:
                    solutions[fv] = np
                    _targets_remaining.discard(fv)
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
                        new_solutions_queue.append({'target': fval, 'solution': np})
                _queue.append((nN, nk, np))

        if not _targets_remaining:
            break

        # CPU Throttling for cloud stability
        if states_explored % 2000 == 0:
            time.sleep(0.001)

    is_computing = False

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
        new_solutions_queue.clear()
        states_explored = 0
        is_computing = True
        
        # Trigger the thread
        t = threading.Thread(target=run_bfs_solver)
        t.daemon = True
        t.start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/api/poll_progress')
def poll_progress():
    global new_solutions_queue, is_computing, states_explored
    # Jitne naye solutions mile hain unhein nikal kar frontend ko dein aur queue khali karein
    batch = list(new_solutions_queue)
    new_solutions_queue.clear()
    
    return jsonify({
        'new_solutions': batch,
        'done': not is_computing and len(batch) == 0,
        'states_explored': states_explored,
        'total_solved': len(solutions)
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)