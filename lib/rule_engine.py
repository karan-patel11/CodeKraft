"""
Layer 3: Rule Engine — pre-computed mentor hints for every known error type.

Maps error_type labels (from CodeBERT classification + static analysis)
to curated, pedagogical hints. This eliminates the need to call an LLM
for the 80% of cases that match known patterns.

Response time: < 1ms (dictionary lookup).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RuleHint:
    """A pre-crafted mentor hint for a specific error category."""
    category: str
    hint: str
    follow_up: str       # deeper "think about this" prompt
    difficulty: str      # "beginner" | "intermediate" | "advanced"
    common_fix: str      # generic fix pattern (not the actual fix)


# ══════════════════════════════════════════════════════════════════════════════
#  HINT DATABASE — curated from QuixBugs error patterns
# ══════════════════════════════════════════════════════════════════════════════

_HINTS: dict[str, RuleHint] = {

    # ── Name / Identifier Errors ──────────────────────────────────────────
    "NameError": RuleHint(
        category="NameError",
        hint="A variable or function name is being used that doesn't exist in the current scope. "
             "This usually means a typo, a missing import, or a variable defined inside a different block.",
        follow_up="Compare each variable name character-by-character with where it was first assigned. "
                   "Python is case-sensitive — 'Result' and 'result' are different names.",
        difficulty="beginner",
        common_fix="Check spelling of variable names and ensure they are defined before use.",
    ),

    # ── Off-By-One ────────────────────────────────────────────────────────
    "OffByOneError": RuleHint(
        category="OffByOneError",
        hint="The loop or index boundary is off by exactly one position. "
             "This is one of the most common bugs in programming — the loop runs one iteration too many or too few.",
        follow_up="Trace through your loop manually with a small input (e.g., a list of 3 elements). "
                   "Write down the index at each step. Does it access all elements? Does it go past the end?",
        difficulty="intermediate",
        common_fix="Adjust range bounds: range(n) gives [0..n-1], range(1, n+1) gives [1..n].",
    ),

    # ── Wrong Operator ────────────────────────────────────────────────────
    "WrongOperator": RuleHint(
        category="WrongOperator",
        hint="An arithmetic, comparison, or logical operator is incorrect. "
             "A '+' might need to be '-', or a '<' might need to be '<='.",
        follow_up="Focus on the operator that combines or compares two values. "
                   "Ask yourself: what should this operation produce for a known input?",
        difficulty="intermediate",
        common_fix="Verify each operator against the algorithm's mathematical definition.",
    ),

    # ── Wrong Comparator ──────────────────────────────────────────────────
    "WrongComparator": RuleHint(
        category="WrongComparator",
        hint="A comparison boundary is using the wrong inequality. "
             "The difference between '<' and '<=' can change whether the edge case is included.",
        follow_up="Test your condition with the boundary value itself. "
                   "If your list has 5 items, what happens when the index equals 5?",
        difficulty="intermediate",
        common_fix="Check < vs <= and > vs >= at every boundary condition.",
    ),

    # ── Syntax Error ──────────────────────────────────────────────────────
    "SyntaxError": RuleHint(
        category="SyntaxError",
        hint="The code has a syntax error — Python cannot parse it at all. "
             "Look for missing colons, unmatched parentheses, or incorrect indentation.",
        follow_up="Start from the line number in the error message and work backwards. "
                   "The actual mistake is often on the line BEFORE the one Python points to.",
        difficulty="beginner",
        common_fix="Check for missing ':', unmatched brackets, or invalid indentation.",
    ),

    # ── Missing Return ────────────────────────────────────────────────────
    "MissingReturn": RuleHint(
        category="MissingReturn",
        hint="A function computes a result but never returns it. "
             "In Python, functions without a return statement implicitly return None.",
        follow_up="Trace the function: what value should the caller receive? "
                   "Is that value being stored in a variable but never returned?",
        difficulty="beginner",
        common_fix="Add 'return result_variable' at the end of the function.",
    ),

    # ── Zero Division ─────────────────────────────────────────────────────
    "ZeroDivisionError": RuleHint(
        category="ZeroDivisionError",
        hint="A division operation may receive zero as a divisor. "
             "This crashes at runtime with ZeroDivisionError.",
        follow_up="Under what input conditions could the denominator become zero? "
                   "Add a guard clause to handle that edge case.",
        difficulty="beginner",
        common_fix="Add 'if divisor != 0:' before the division.",
    ),

    # ── Infinite Loop ─────────────────────────────────────────────────────
    "InfiniteLoop": RuleHint(
        category="InfiniteLoop",
        hint="A loop may run forever because its exit condition is never satisfied. "
             "This typically happens with 'while True' without a 'break', or a loop variable that never changes.",
        follow_up="Ask yourself: what makes this loop stop? Is that condition actually reachable? "
                   "Add a print inside the loop to trace the loop variable.",
        difficulty="intermediate",
        common_fix="Ensure the loop variable is modified inside the loop body to eventually meet the exit condition.",
    ),

    # ── Wrong Variable / Swapped Args ────────────────────────────────────
    "WrongVariable": RuleHint(
        category="WrongVariable",
        hint="A variable is being used in a place where a different variable was intended. "
             "The names might be similar (e.g., 'left' vs 'right', 'i' vs 'j').",
        follow_up="In functions with multiple similar variables, label each one with a comment "
                   "describing its role. Then verify each usage matches the correct role.",
        difficulty="intermediate",
        common_fix="Double-check which variable should be used at each point in the algorithm.",
    ),

    # ── Incorrect Base Case (recursion) ──────────────────────────────────
    "WrongBaseCase": RuleHint(
        category="WrongBaseCase",
        hint="The base case of a recursive function may be incorrect — either it triggers too early, "
             "too late, or returns the wrong value.",
        follow_up="Test your base case with the smallest valid inputs (0, 1, empty list). "
                   "Does the function return the correct answer for those without recursing?",
        difficulty="advanced",
        common_fix="Verify the base case condition and its return value against the problem specification.",
    ),

    # ── Wrong Accumulator Init ────────────────────────────────────────────
    "WrongInitialization": RuleHint(
        category="WrongInitialization",
        hint="A variable is initialized to the wrong starting value. "
             "For example, initializing a 'max' tracker to 0 when the input could contain negative numbers.",
        follow_up="Ask: what should this variable's value be BEFORE the first iteration? "
                   "For max: use float('-inf'). For min: use float('inf'). For sums: use 0.",
        difficulty="intermediate",
        common_fix="Set the initial value to the identity element for the operation (0 for sum, 1 for product, etc.).",
    ),
}

# ── Aliases: map static-analysis categories to hint keys ──────────────────
_ALIASES = {
    "CHANGE_IDENTIFIER": "NameError",
    "CHANGE_OPERATOR": "WrongOperator",
    "CHANGE_NUMERIC_LITERAL": "OffByOneError",
    "CHANGE_BOOLEAN_LITERAL": "WrongOperator",
    "CHANGE_STRING_LITERAL": "NameError",
    "ADD_METHOD_CALL": "MissingReturn",
    "DELETE_METHOD_CALL": "WrongVariable",
    "CHANGE_ATTRIBUTE": "WrongVariable",
}


# ══════════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════════

def get_hint(category: str) -> Optional[RuleHint]:
    """
    Look up the pre-computed hint for a given error category.
    Supports both direct category names and SStuB pattern aliases.
    Returns None if no matching hint exists.
    """
    # Direct match
    if category in _HINTS:
        return _HINTS[category]
    # Alias match
    resolved = _ALIASES.get(category)
    if resolved and resolved in _HINTS:
        return _HINTS[resolved]
    return None


def get_all_categories() -> list[str]:
    """Return all supported error categories."""
    return sorted(_HINTS.keys())


def get_hint_dict(category: str) -> Optional[dict]:
    """Return hint as a JSON-serializable dict, or None."""
    h = get_hint(category)
    if not h:
        return None
    return {
        "category": h.category,
        "hint": h.hint,
        "follow_up": h.follow_up,
        "difficulty": h.difficulty,
        "common_fix": h.common_fix,
    }
