"""
Banker's Algorithm Engine
=========================
Core logic for deadlock avoidance using the Banker's Algorithm.
Supports step-by-step visualization, all safe sequences, and resource-request simulation.

Zero external dependencies — uses only Python standard library.
"""

import copy
from dataclasses import dataclass, field
from typing import Optional


# ─── Data Structures ─────────────────────────────────────────────────────────

@dataclass
class StepSnapshot:
    """A single step in the safety algorithm visualization."""
    step_number: int
    action: str  # "start" | "pass_start" | "testing" | "granted" | "blocked" | "safe" | "unsafe"
    current_process: Optional[int]  # index of process being checked (None for summary steps)
    work_vector: list
    finish: list
    sequence_so_far: list
    explanation: str
    pass_number: int


@dataclass
class RequestResult:
    """Result of a resource-request simulation."""
    granted: bool
    reason: str
    safety_trace: list  # list[StepSnapshot]
    safe_sequence: list  # list[int]


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _vec_leq(a: list, b: list) -> bool:
    """Check if vector a <= vector b element-wise."""
    return all(ai <= bi for ai, bi in zip(a, b))


def _vec_add(a: list, b: list) -> list:
    """Element-wise vector addition."""
    return [ai + bi for ai, bi in zip(a, b)]


def _vec_sub(a: list, b: list) -> list:
    """Element-wise vector subtraction."""
    return [ai - bi for ai, bi in zip(a, b)]


def _fmt_vec(vec: list, names: list) -> str:
    """Format a resource vector with names for human-readable display."""
    parts = [f"{n}: {v}" for n, v in zip(names, vec)]
    return "[" + ", ".join(parts) + "]"


def _fmt_vec_short(vec: list) -> str:
    """Format a resource vector compactly (numbers only)."""
    return "[" + ", ".join(str(v) for v in vec) + "]"


# ─── Banker State ─────────────────────────────────────────────────────────────

class BankerState:
    """Holds all matrices and metadata for a Banker's Algorithm instance."""

    def __init__(self, n_processes: int, n_resources: int,
                 process_names: list = None, resource_names: list = None,
                 allocation: list = None, max_matrix: list = None,
                 total_resources: list = None):
        self.n_processes = n_processes
        self.n_resources = n_resources
        self.process_names = process_names or [f"P{i}" for i in range(n_processes)]
        self.resource_names = resource_names or [chr(65 + i) for i in range(n_resources)]
        self.allocation = allocation or [[0] * n_resources for _ in range(n_processes)]
        self.max_matrix = max_matrix or [[0] * n_resources for _ in range(n_processes)]
        self.total_resources = total_resources or [0] * n_resources

    def compute_need(self) -> list:
        """Need[i][j] = Max[i][j] - Allocation[i][j]"""
        return [
            [self.max_matrix[i][j] - self.allocation[i][j]
             for j in range(self.n_resources)]
            for i in range(self.n_processes)
        ]

    def compute_available(self) -> list:
        """Available[j] = Total[j] - Σ Allocation[i][j]"""
        avail = list(self.total_resources)
        for i in range(self.n_processes):
            for j in range(self.n_resources):
                avail[j] -= self.allocation[i][j]
        return avail

    def validate(self) -> list:
        """Validate all inputs. Returns list of error strings (empty = valid)."""
        errors = []
        if self.n_processes <= 0:
            errors.append("Number of processes must be positive.")
            return errors
        if self.n_resources <= 0:
            errors.append("Number of resources must be positive.")
            return errors

        for i in range(self.n_processes):
            pn = self.process_names[i]
            for j in range(self.n_resources):
                rn = self.resource_names[j]
                a = self.allocation[i][j]
                m = self.max_matrix[i][j]
                if a < 0:
                    errors.append(f"'{pn}': Allocation for '{rn}' is negative ({a}).")
                if m < 0:
                    errors.append(f"'{pn}': Max for '{rn}' is negative ({m}).")
                if a > m:
                    errors.append(f"'{pn}': Allocation ({a}) > Max ({m}) for '{rn}'.")

        avail = self.compute_available()
        for j in range(self.n_resources):
            if avail[j] < 0:
                total_alloc = sum(self.allocation[i][j] for i in range(self.n_processes))
                errors.append(
                    f"Total allocation for '{self.resource_names[j]}' ({total_alloc}) "
                    f"exceeds total resources ({self.total_resources[j]})."
                )
        return errors


# ─── Safety Algorithm (Step-by-Step) ─────────────────────────────────────────

def safety_check(state: BankerState) -> list:
    """
    Run the Banker's Safety Algorithm, recording every decision as a StepSnapshot.
    Returns: list[StepSnapshot]
    """
    need = state.compute_need()
    work = list(state.compute_available())
    finish = [False] * state.n_processes
    sequence = []
    steps = []
    step_num = 0
    rn = state.resource_names
    pn = state.process_names

    # ── Initial state ──
    steps.append(StepSnapshot(
        step_number=step_num, action="start", current_process=None,
        work_vector=list(work), finish=list(finish),
        sequence_so_far=[], explanation=(
            f"Starting Safety Algorithm.\n"
            f"Initial Work (Available) = {_fmt_vec(work, rn)}"
        ), pass_number=0
    ))
    step_num += 1

    pass_number = 0
    while True:
        found_in_pass = False
        pass_number += 1

        steps.append(StepSnapshot(
            step_number=step_num, action="pass_start", current_process=None,
            work_vector=list(work), finish=list(finish),
            sequence_so_far=list(sequence),
            explanation=f"─── Pass {pass_number} through the process list ───",
            pass_number=pass_number
        ))
        step_num += 1

        for i in range(state.n_processes):
            if finish[i]:
                continue

            need_s = _fmt_vec(need[i], rn)
            work_s = _fmt_vec(work, rn)

            # ── Testing step ──
            steps.append(StepSnapshot(
                step_number=step_num, action="testing", current_process=i,
                work_vector=list(work), finish=list(finish),
                sequence_so_far=list(sequence),
                explanation=f"Checking '{pn[i]}':  Need {need_s}  ≤  Work {work_s}  ?",
                pass_number=pass_number
            ))
            step_num += 1

            if _vec_leq(need[i], work):
                # ── Granted ──
                old_work = list(work)
                work = _vec_add(work, state.allocation[i])
                finish[i] = True
                sequence.append(i)
                found_in_pass = True

                steps.append(StepSnapshot(
                    step_number=step_num, action="granted", current_process=i,
                    work_vector=list(work), finish=list(finish),
                    sequence_so_far=list(sequence),
                    explanation=(
                        f"✅ YES — '{pn[i]}' CAN execute and release resources.\n"
                        f"   Work = {_fmt_vec(old_work, rn)}  +  Alloc {_fmt_vec(state.allocation[i], rn)}\n"
                        f"       = {_fmt_vec(work, rn)}"
                    ), pass_number=pass_number
                ))
                step_num += 1
            else:
                # ── Blocked ──
                blocking = []
                for j in range(state.n_resources):
                    if need[i][j] > work[j]:
                        blocking.append(f"{rn[j]}: need {need[i][j]} > avail {work[j]}")

                steps.append(StepSnapshot(
                    step_number=step_num, action="blocked", current_process=i,
                    work_vector=list(work), finish=list(finish),
                    sequence_so_far=list(sequence),
                    explanation=(
                        f"❌ NO — '{pn[i]}' cannot proceed.\n"
                        f"   Insufficient: {'; '.join(blocking)}"
                    ), pass_number=pass_number
                ))
                step_num += 1

        if not found_in_pass:
            break

    # ── Final verdict ──
    if all(finish):
        seq_str = "  →  ".join(pn[i] for i in sequence)
        steps.append(StepSnapshot(
            step_number=step_num, action="safe", current_process=None,
            work_vector=list(work), finish=list(finish),
            sequence_so_far=list(sequence),
            explanation=(
                f"🟢  SYSTEM IS IN A SAFE STATE\n"
                f"Safe Sequence:  {seq_str}"
            ), pass_number=pass_number
        ))
    else:
        blocked = [pn[i] for i in range(state.n_processes) if not finish[i]]
        detail_lines = []
        for i in range(state.n_processes):
            if not finish[i]:
                shortages = []
                for j in range(state.n_resources):
                    if need[i][j] > work[j]:
                        shortages.append(f"{rn[j]}: need {need[i][j]}, avail {work[j]}")
                if shortages:
                    detail_lines.append(f"  • '{pn[i]}' waiting for: {'; '.join(shortages)}")
                else:
                    detail_lines.append(f"  • '{pn[i]}' could run but is stuck behind others")

        steps.append(StepSnapshot(
            step_number=step_num, action="unsafe", current_process=None,
            work_vector=list(work), finish=list(finish),
            sequence_so_far=list(sequence),
            explanation=(
                f"🔴  SYSTEM IS IN AN UNSAFE STATE — DEADLOCK RISK!\n"
                f"Blocked processes: {', '.join(blocked)}\n"
                + "\n".join(detail_lines) + "\n"
                f"No remaining process can have its needs met."
            ), pass_number=pass_number
        ))

    return steps


# ─── Find ALL Safe Sequences (DFS Backtracking) ─────────────────────────────

def find_all_sequences(state: BankerState, max_results: int = 500) -> list:
    """
    Enumerate all possible safe sequences using DFS/backtracking.
    Returns: list[list[int]] — each inner list is a sequence of process indices.
    Caps at max_results to avoid combinatorial explosion on large inputs.
    """
    need = state.compute_need()
    avail = state.compute_available()
    all_seqs = []

    def backtrack(work, finish, seq):
        if len(all_seqs) >= max_results:
            return
        if len(seq) == state.n_processes:
            all_seqs.append(list(seq))
            return
        for i in range(state.n_processes):
            if not finish[i] and _vec_leq(need[i], work):
                finish[i] = True
                seq.append(i)
                backtrack(_vec_add(work, state.allocation[i]), finish, seq)
                finish[i] = False
                seq.pop()

    backtrack(list(avail), [False] * state.n_processes, [])
    return all_seqs


# ─── Resource-Request Algorithm ──────────────────────────────────────────────

def request_resources(state: BankerState, process_id: int, request: list) -> RequestResult:
    """
    Simulate a resource request: Process `process_id` asks for `request` resources.
    Performs the three-stage check (Request ≤ Need, Request ≤ Available, Safety check).
    """
    need = state.compute_need()
    avail = state.compute_available()
    pname = state.process_names[process_id]
    rn = state.resource_names

    # Stage 1: Request ≤ Need[process_id]
    if not _vec_leq(request, need[process_id]):
        violations = []
        for j in range(state.n_resources):
            if request[j] > need[process_id][j]:
                violations.append(f"{rn[j]}: requested {request[j]} > remaining need {need[process_id][j]}")
        return RequestResult(
            granted=False,
            reason=(
                f"⛔ ERROR: '{pname}' exceeded its maximum claim!\n"
                f"{'; '.join(violations)}\n"
                f"A process cannot request more than its declared remaining need."
            ),
            safety_trace=[], safe_sequence=[]
        )

    # Stage 2: Request ≤ Available
    if not _vec_leq(request, avail):
        shortages = []
        for j in range(state.n_resources):
            if request[j] > avail[j]:
                shortages.append(f"{rn[j]}: requested {request[j]} > available {avail[j]}")
        return RequestResult(
            granted=False,
            reason=(
                f"⏳ '{pname}' must WAIT — resources not currently available.\n"
                f"{'; '.join(shortages)}"
            ),
            safety_trace=[], safe_sequence=[]
        )

    # Stage 3: Tentative allocation → Safety check
    temp = copy.deepcopy(state)
    for j in range(state.n_resources):
        temp.allocation[process_id][j] += request[j]
    # Available will auto-recalculate in compute_available()

    trace = safety_check(temp)
    final = trace[-1]

    if final.action == "safe":
        seq_str = "  →  ".join(temp.process_names[i] for i in final.sequence_so_far)
        return RequestResult(
            granted=True,
            reason=(
                f"✅ Request GRANTED!\n"
                f"Allocating {_fmt_vec(request, rn)} to '{pname}' keeps the system safe.\n"
                f"Safe Sequence: {seq_str}"
            ),
            safety_trace=trace,
            safe_sequence=final.sequence_so_far
        )
    else:
        return RequestResult(
            granted=False,
            reason=(
                f"❌ Request DENIED!\n"
                f"Granting {_fmt_vec(request, rn)} to '{pname}' would leave the system UNSAFE.\n"
                f"The request is rolled back — '{pname}' must wait."
            ),
            safety_trace=trace,
            safe_sequence=[]
        )


# ─── Preset Scenarios ────────────────────────────────────────────────────────

def get_presets() -> dict:
    """Return all preset scenarios as a dict of name → BankerState."""
    presets = {}

    # 1. Gaming Session (SAFE)
    presets["🎮 Gaming Session"] = BankerState(
        n_processes=5, n_resources=4,
        process_names=["Game Engine", "Physics Thread", "Audio Manager",
                       "Asset Loader", "Network Sync"],
        resource_names=["CPU Cores", "RAM (GB)", "GPU Units", "Disk I/O"],
        allocation=[
            [2, 4, 1, 1], [1, 2, 1, 0], [0, 1, 0, 1],
            [1, 2, 0, 1], [1, 1, 0, 0],
        ],
        max_matrix=[
            [4, 8, 2, 2], [2, 4, 1, 1], [1, 2, 0, 1],
            [2, 3, 1, 1], [1, 2, 0, 1],
        ],
        total_resources=[8, 16, 4, 3],
    )

    # 2. Web Server Under Load (SAFE)
    presets["🌐 Web Server"] = BankerState(
        n_processes=5, n_resources=3,
        process_names=["Request Handler", "Auth Service", "DB Query Engine",
                       "Cache Manager", "Log Writer"],
        resource_names=["Threads", "DB Conns", "Memory (GB)"],
        allocation=[
            [3, 1, 2], [1, 1, 1], [1, 2, 1],
            [2, 0, 1], [1, 0, 1],
        ],
        max_matrix=[
            [5, 2, 4], [2, 2, 2], [3, 3, 2],
            [3, 1, 2], [2, 1, 1],
        ],
        total_resources=[10, 5, 8],
    )

    # 3. Deadlock — Video Editing (UNSAFE)
    presets["☠️ Deadlock! (Video Edit)"] = BankerState(
        n_processes=4, n_resources=3,
        process_names=["Timeline Renderer", "Export Encoder",
                       "Preview Player", "Audio Mixer"],
        resource_names=["CPU Cores", "RAM (GB)", "GPU Units"],
        allocation=[
            [2, 3, 1], [2, 2, 1], [1, 2, 1], [1, 1, 0],
        ],
        max_matrix=[
            [4, 6, 2], [3, 4, 2], [3, 4, 1], [2, 3, 1],
        ],
        total_resources=[6, 8, 3],
    )

    # 4. Classic Textbook — Silberschatz / Galvin (SAFE)
    presets["📚 Classic Textbook"] = BankerState(
        n_processes=5, n_resources=3,
        process_names=["P0", "P1", "P2", "P3", "P4"],
        resource_names=["A", "B", "C"],
        allocation=[
            [0, 1, 0], [2, 0, 0], [3, 0, 2],
            [2, 1, 1], [0, 0, 2],
        ],
        max_matrix=[
            [7, 5, 3], [3, 2, 2], [9, 0, 2],
            [2, 2, 2], [4, 3, 3],
        ],
        total_resources=[10, 5, 7],
    )

    # 5. Multiple Safe Sequences (SAFE, many orderings)
    presets["🔀 Multiple Sequences"] = BankerState(
        n_processes=4, n_resources=3,
        process_names=["P0", "P1", "P2", "P3"],
        resource_names=["R1", "R2", "R3"],
        allocation=[
            [1, 1, 1], [1, 1, 0], [1, 0, 1], [1, 1, 1],
        ],
        max_matrix=[
            [2, 2, 2], [2, 2, 1], [2, 1, 2], [2, 2, 2],
        ],
        total_resources=[6, 5, 4],
    )

    return presets

