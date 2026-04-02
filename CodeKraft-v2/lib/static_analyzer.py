"""
Layer 1: Static Analyzer — AST-based, zero-latency pre-analysis.

Parses student code using Python's built-in AST module and applies
pattern-matching heuristics to detect common bug categories BEFORE
any model inference. This gives us:
  - Instant feedback (< 5ms)
  - Structured findings that guide the classifier
  - Fallback diagnostics if the model is unavailable
"""

import ast
import re
import tokenize
import io
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Finding:
    """A single issue detected by static analysis."""
    rule_id: str               # e.g. "SA001"
    category: str              # maps to error_type labels from QuixBugs
    severity: str              # "error" | "warning" | "info"
    line: Optional[int]        # 1-indexed line number, if known
    col: Optional[int]         # 0-indexed column offset, if known
    message: str               # human-readable description
    suggestion: str            # short actionable fix hint
    confidence: float          # 0.0 – 1.0


@dataclass
class AnalysisResult:
    """Complete output of the static analysis layer."""
    parseable: bool            # did the code parse into a valid AST?
    syntax_error: Optional[str] = None
    syntax_error_line: Optional[int] = None
    findings: list = field(default_factory=list)
    defined_names: set = field(default_factory=set)
    used_names: set = field(default_factory=set)
    function_count: int = 0
    loop_count: int = 0
    branch_count: int = 0
    line_count: int = 0
    complexity_score: float = 0.0  # simple cyclomatic proxy

    @property
    def has_errors(self) -> bool:
        return any(f.severity == "error" for f in self.findings)

    @property
    def top_category(self) -> Optional[str]:
        """Highest-confidence finding category, or None."""
        if not self.findings:
            return None
        return max(self.findings, key=lambda f: f.confidence).category

    def to_dict(self):
        return {
            "parseable": self.parseable,
            "syntax_error": self.syntax_error,
            "syntax_error_line": self.syntax_error_line,
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "category": f.category,
                    "severity": f.severity,
                    "line": f.line,
                    "col": f.col,
                    "message": f.message,
                    "suggestion": f.suggestion,
                    "confidence": round(f.confidence, 3),
                }
                for f in self.findings
            ],
            "stats": {
                "line_count": self.line_count,
                "function_count": self.function_count,
                "loop_count": self.loop_count,
                "branch_count": self.branch_count,
                "complexity_score": round(self.complexity_score, 2),
            },
            "top_category": self.top_category,
        }


class _NameCollector(ast.NodeVisitor):
    """Walks the AST to collect defined vs. used names."""

    def __init__(self):
        self.defined: set = set()
        self.used: set = set()
        self.imported: set = set()

    def visit_FunctionDef(self, node):
        self.defined.add(node.name)
        for arg in node.args.args:
            self.defined.add(arg.arg)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.defined.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.defined.add(target.id)
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        self.defined.add(elt.id)
        self.generic_visit(node)

    def visit_For(self, node):
        if isinstance(node.target, ast.Name):
            self.defined.add(node.target.id)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.imported.add(name)
            self.defined.add(name)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imported.add(name)
            self.defined.add(name)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used.add(node.id)
        self.generic_visit(node)


class _PatternDetector(ast.NodeVisitor):
    """Detects common bug patterns via AST heuristics."""

    BUILTINS = frozenset({
        "print", "len", "range", "int", "str", "float", "list", "dict",
        "set", "tuple", "bool", "type", "isinstance", "sorted", "reversed",
        "enumerate", "zip", "map", "filter", "sum", "min", "max", "abs",
        "input", "open", "super", "True", "False", "None", "Exception",
        "ValueError", "TypeError", "KeyError", "IndexError", "StopIteration",
        "iter", "next", "hasattr", "getattr", "setattr", "any", "all",
    })

    def __init__(self, defined_names: set):
        self.defined = defined_names | self.BUILTINS
        self.findings: list[Finding] = []
        self._functions: list[ast.FunctionDef] = []
        self.loop_count = 0
        self.branch_count = 0
        self.function_count = 0

    # ── Undefined name detection ──────────────────────────────────────────
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id not in self.defined:
            self.findings.append(Finding(
                rule_id="SA001",
                category="NameError",
                severity="error",
                line=node.lineno,
                col=node.col_offset,
                message=f"Name '{node.id}' is used but never defined in this scope.",
                suggestion=f"Check the spelling of '{node.id}' — did you mean a similar variable?",
                confidence=0.92,
            ))
        self.generic_visit(node)

    # ── Off-by-one in range() ─────────────────────────────────────────────
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "range":
            # range(len(x)) inside for-loop indexing is a common OBO source
            if len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                inner = node.args[0]
                if isinstance(inner.func, ast.Name) and inner.func.id == "len":
                    self.findings.append(Finding(
                        rule_id="SA002",
                        category="OffByOneError",
                        severity="warning",
                        line=node.lineno,
                        col=node.col_offset,
                        message="range(len(...)) pattern detected — verify boundary conditions.",
                        suggestion="Off-by-one errors often hide here. Check if you need len(x)-1 or len(x)+1.",
                        confidence=0.65,
                    ))
        self.generic_visit(node)

    # ── Comparison operator patterns ──────────────────────────────────────
    def visit_Compare(self, node):
        for op in node.ops:
            # x < len(arr) vs x <= len(arr)  — common OBO
            if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                for comp in node.comparators:
                    if isinstance(comp, ast.Call) and isinstance(comp.func, ast.Name):
                        if comp.func.id == "len":
                            self.findings.append(Finding(
                                rule_id="SA003",
                                category="WrongComparator",
                                severity="warning",
                                line=node.lineno,
                                col=node.col_offset,
                                message="Boundary comparison with len() — verify < vs <= correctness.",
                                suggestion="Should this be '<' or '<='? Off-by-one errors are common here.",
                                confidence=0.60,
                            ))
        self.generic_visit(node)

    # ── Wrong operator detection ──────────────────────────────────────────
    def visit_BinOp(self, node):
        # Division by potential zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.findings.append(Finding(
                    rule_id="SA004",
                    category="ZeroDivisionError",
                    severity="error",
                    line=node.lineno,
                    col=node.col_offset,
                    message="Division by zero detected.",
                    suggestion="Add a guard: check if the divisor is zero before dividing.",
                    confidence=0.99,
                ))
        # Subtraction where addition might be intended (heuristic: negative index)
        self.generic_visit(node)

    # ── Missing return ────────────────────────────────────────────────────
    def visit_FunctionDef(self, node):
        self.function_count += 1
        self._functions.append(node)

        has_return = any(
            isinstance(n, ast.Return) and n.value is not None
            for n in ast.walk(node)
        )
        has_yield = any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node))

        # Heuristic: if the function has assignments but no return/yield, flag it
        has_assignments = any(isinstance(n, ast.Assign) for n in ast.walk(node))
        if has_assignments and not has_return and not has_yield:
            # Don't flag __init__ or simple print functions
            if node.name != "__init__":
                self.findings.append(Finding(
                    rule_id="SA005",
                    category="MissingReturn",
                    severity="warning",
                    line=node.lineno,
                    col=node.col_offset,
                    message=f"Function '{node.name}' computes values but never returns them.",
                    suggestion=f"Did you forget a 'return' statement at the end of '{node.name}'?",
                    confidence=0.55,
                ))
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    # ── Loop analysis ─────────────────────────────────────────────────────
    def visit_For(self, node):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.loop_count += 1
        # Infinite loop detection: while True without break
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
            if not has_break:
                self.findings.append(Finding(
                    rule_id="SA006",
                    category="InfiniteLoop",
                    severity="warning",
                    line=node.lineno,
                    col=node.col_offset,
                    message="'while True' without a 'break' statement — potential infinite loop.",
                    suggestion="Add a break condition or change the loop guard.",
                    confidence=0.80,
                ))
        self.generic_visit(node)

    # ── Branch counting ───────────────────────────────────────────────────
    def visit_If(self, node):
        self.branch_count += 1
        self.generic_visit(node)


# ══════════════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════════════

def analyze(code: str) -> AnalysisResult:
    """
    Run full static analysis on a Python code snippet.
    Guaranteed to return in < 5ms for typical student code.
    """
    result = AnalysisResult(parseable=True)
    result.line_count = len(code.splitlines())

    # ── Phase 1: syntax check ─────────────────────────────────────────────
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        result.parseable = False
        result.syntax_error = str(e.msg) if e.msg else str(e)
        result.syntax_error_line = e.lineno
        result.findings.append(Finding(
            rule_id="SA000",
            category="SyntaxError",
            severity="error",
            line=e.lineno,
            col=e.offset,
            message=f"SyntaxError: {e.msg}",
            suggestion="Fix the syntax error first — the code cannot be parsed as valid Python.",
            confidence=1.0,
        ))
        return result

    # ── Phase 2: name collection ──────────────────────────────────────────
    collector = _NameCollector()
    collector.visit(tree)
    result.defined_names = collector.defined
    result.used_names = collector.used

    # ── Phase 3: pattern detection ────────────────────────────────────────
    detector = _PatternDetector(collector.defined)
    detector.visit(tree)
    result.findings.extend(detector.findings)
    result.function_count = detector.function_count
    result.loop_count = detector.loop_count
    result.branch_count = detector.branch_count

    # ── Phase 4: complexity score (simplified cyclomatic) ─────────────────
    result.complexity_score = 1.0 + detector.branch_count + detector.loop_count

    # ── Phase 5: sort findings by confidence descending ───────────────────
    result.findings.sort(key=lambda f: -f.confidence)

    return result
