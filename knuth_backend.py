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

# ---------------------------------------------------------------------------
# Flask Web Server (Asynchronous Startup)
# ---------------------------------------------------------------------------

from flask import Flask, jsonify, send_file, Response
import os
import threading
import json
import time
from collections import deque
import math
from flask_cors import CORS  # Add this import

app = Flask(__name__)
CORS(app)  # Add this line right after 'app' is defined

# Global state variables
solutions = {}
unsolved = []
is_computing = True

def run_background_solver():
    """Runs the heavy BFS calculation in the background so the server doesn't freeze."""
    global solutions, unsolved, is_computing
    print("\n [Background] Pre-computing all solutions (BFS running)...")
    
    # Assuming solve_all() is defined above in your file
    # We update the global dictionaries directly
    temp_solutions, temp_unsolved = solve_all()
    solutions.update(temp_solutions)
    unsolved.extend(temp_unsolved)
    
    is_computing = False
    print(f"\n [Background] ✓ Search complete! {len(solutions)}/100 targets solved.")

print("=" * 72)
print("  Donald Knuth Problem  —  LIMIT 100")
print("  Allowed operations:  n!   √n   ⌊n⌋")
print("  Using exact integer arithmetic (no float precision loss)")
print("=" * 72)
print("\n Server starting INSTANTLY on http://localhost:5000")
print(" Open knuth_frontend.html in your browser.\n")

@app.route('/')
def index():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knuth_frontend.html')
    if os.path.exists(html_path):
        return send_file(html_path)
    return "<h1>Please open knuth_frontend.html in your browser.</h1>"

@app.route('/api/solve/<int:target>')
def solve_target(target):
    if target < 1 or target > 100:
        return jsonify({'error': 'Target must be between 1 and 100'}), 400
    
    # If the background thread is still running and hasn't found it yet
    if target not in solutions and is_computing:
        return jsonify({'target': target, 'solution': None, 'found': False, 'message': 'Still computing in background...'})
        
    if target in solutions:
        return jsonify({'target': target, 'solution': solutions[target], 'found': True})
    else:
        return jsonify({'target': target, 'solution': None, 'found': False})

@app.route('/api/all')
def all_solutions():
    result = {}
    for t in range(1, 101):
        result[str(t)] = solutions.get(t, None)
    return jsonify(result)

@app.route('/api/status')
def status():
    # Frontend can use this to know if the backend is still thinking
    return jsonify({
        'ready': not is_computing, 
        'solved': len(solutions), 
        'total': 100
    })

# ---------------------------------------------------------------------------
# SSE streaming endpoint (Kept exactly as you had it)
# ---------------------------------------------------------------------------

@app.route('/api/stream')
def stream_solutions():
    """
    Server-Sent Events stream.  Re-runs the BFS and emits each solution
    as soon as it is found, so the frontend can display them live.
    """
    def generate():
        _targets_remaining = set(range(1, 101))
        _solutions = {}
        _visited = set()

        def _vkey(N, k):
            return (N, k)

        _start_N, _start_k = 4, 0
        _visited.add(_vkey(_start_N, _start_k))
        _queue = deque()
        _queue.append((_start_N, _start_k, "4"))

        if 4 in _targets_remaining:
            _solutions[4] = "4"
            _targets_remaining.discard(4)
            payload = json.dumps({'target': 4, 'solution': "4", 'remaining': len(_targets_remaining)})
            yield f"data: {payload}\n\n"

        _states_explored = 0
        _MAX_STATES = 30_000_000
        
        # NOTE: Make sure MAX_K, exact_value_is_integer, exact_integer_value, 
        # int_root_floor, MAX_FACTORIAL_ARG, MAX_N_BITS are defined globally!

        while _queue and _targets_remaining and _states_explored < _MAX_STATES:
            N, k, path = _queue.popleft()
            _states_explored += 1

            # 1. sqrt
            if k < MAX_K:
                nN, nk = N, k + 1
                key1 = _vkey(nN, nk)
                if key1 not in _visited:
                    _visited.add(key1)
                    np = f"√({path})"
                    if exact_value_is_integer(nN, nk):
                        val = exact_integer_value(nN, nk)
                        if val in _targets_remaining:
                            _solutions[val] = np
                            _targets_remaining.discard(val)
                            payload = json.dumps({'target': val, 'solution': np, 'remaining': len(_targets_remaining)})
                            yield f"data: {payload}\n\n"
                            if not _targets_remaining:
                                break
                    _queue.append((nN, nk, np))

            # 2. floor
            if k > 0:
                fv = int_root_floor(N, k)
                nN, nk = fv, 0
                key2 = _vkey(nN, nk)
                if key2 not in _visited:
                    _visited.add(key2)
                    np = f"⌊{path}⌋"
                    if fv in _targets_remaining:
                        _solutions[fv] = np
                        _targets_remaining.discard(fv)
                        payload = json.dumps({'target': fv, 'solution': np, 'remaining': len(_targets_remaining)})
                        yield f"data: {payload}\n\n"
                        if not _targets_remaining:
                            break
                    _queue.append((nN, nk, np))

            # 3. factorial
            if k == 0 and 0 <= N <= MAX_FACTORIAL_ARG:
                fval = math.factorial(N)
                nbits = fval.bit_length()
                if nbits <= MAX_N_BITS:
                    nN, nk = fval, 0
                    key3 = _vkey(nN, nk)
                    if key3 not in _visited:
                        _visited.add(key3)
                        np = f"({path})!"
                        if fval in _targets_remaining:
                            _solutions[fval] = np
                            _targets_remaining.discard(fval)
                            payload = json.dumps({'target': fval, 'solution': np, 'remaining': len(_targets_remaining)})
                            yield f"data: {payload}\n\n"
                            if not _targets_remaining:
                                break
                        _queue.append((nN, nk, np))

        # Signal done
        yield f"data: {json.dumps({'done': True, 'total_solved': len(_solutions)})}\n\n"

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no',
                             'Access-Control-Allow-Origin': '*'})

if __name__ == '__main__':
    import os
    # Use the PORT environment variable if available, otherwise default to 5000
    port = int(os.environ.get("PORT", 5000))

    solver_thread = threading.Thread(target=run_background_solver)
    solver_thread.daemon = True
    solver_thread.start()

    app.run(host='0.0.0.0', port=port, threaded=True)