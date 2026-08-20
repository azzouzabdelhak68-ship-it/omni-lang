#!/usr/bin/env python3
"""
Phase Verification Script for OmniScript v1.0

Enforces quality gates per phase. Must pass before phase checkbox can be ticked.

Usage:
  python scripts/verify_phase.py --phase 1    # Verify Phase 1
  python scripts/verify_phase.py --phase all  # Verify all phases
  python scripts/verify_phase.py --list       # List all phase requirements
"""

import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

class Phase(Enum):
    PHASE_0 = "phase_0"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"
    PHASE_4 = "phase_4"
    PHASE_5 = "phase_5"
    PHASE_6 = "phase_6"
    PHASE_7 = "phase_7"

@dataclass
class QualityGate:
    name: str
    command: List[str]
    description: str
    required: bool = True

@dataclass
class PhaseRequirement:
    phase: Phase
    name: str
    gates: List[QualityGate]
    description: str = ""

PHASE_REQUIREMENTS: Dict[Phase, PhaseRequirement] = {
    Phase.PHASE_0: PhaseRequirement(
        phase=Phase.PHASE_0,
        name="Specification & Harness Setup",
        gates=[
            QualityGate("spec_exists", ["test", "-f", "OMNI_SPEC.md"], "Spec file exists"),
            QualityGate("todo_exists", ["test", "-f", "TODO.md"], "TODO.md exists"),
        ],
        description="Specification and harness setup complete"
    ),
    Phase.PHASE_1: PhaseRequirement(
        phase=Phase.PHASE_1,
        name="Lexer & Tokenizer",
        gates=[
            QualityGate("pytest_lexer", ["pytest", "tests/test_lexer.py", "-v"], "Lexer unit tests pass"),
            QualityGate("mypy", ["mypy", "--strict", "omni_compiler/lexer.py"], "Type checking passes"),
            QualityGate("ruff", ["ruff", "check", "omni_compiler/lexer.py", "tests/test_lexer.py"], "Linting passes"),
            QualityGate("coverage", ["pytest", "--cov=omni_compiler.lexer", "--cov-fail-under=90", "--cov-branch", "tests/test_lexer.py"], "Coverage >= 90%"),
            QualityGate("bandit", ["bandit", "-r", "omni_compiler/lexer.py", "--severity-level", "medium"], "Security scan clean"),
        ],
        description="Lexer with universal ':' token, no fused UI:/scene:"
    ),
    Phase.PHASE_2: PhaseRequirement(
        phase=Phase.PHASE_2,
        name="Parser & AST",
        gates=[
            QualityGate("pytest_parser", ["pytest", "tests/test_parser.py", "-v"], "Parser unit tests pass"),
            QualityGate("mypy", ["mypy", "--strict", "omni_compiler/parser.py"], "Type checking passes"),
            QualityGate("ruff", ["ruff", "check", "omni_compiler/parser.py", "tests/test_parser.py"], "Linting passes"),
            QualityGate("coverage", ["pytest", "--cov=omni_compiler.parser", "--cov-fail-under=90", "--cov-branch", "tests/test_parser.py"], "Coverage >= 90%"),
            QualityGate("hypothesis", ["pytest", "tests/test_parser.py::test_round_trip", "-v"], "Property-based round-trip tests"),
        ],
        description="Parser with universal block rule and AST"
    ),
    Phase.PHASE_3: PhaseRequirement(
        phase=Phase.PHASE_3,
        name="Semantic Analysis & Symbol Table",
        gates=[
            QualityGate("pytest_checker", ["pytest", "tests/test_checker.py", "-v"], "Semantic analysis tests pass"),
            QualityGate("mypy", ["mypy", "--strict", "omni_compiler/checker.py"], "Type checking passes"),
            QualityGate("ruff", ["ruff", "check", "omni_compiler/checker.py", "tests/test_checker.py"], "Linting passes"),
            QualityGate("coverage", ["pytest", "--cov=omni_compiler.checker", "--cov-fail-under=90", "--cov-branch", "tests/test_checker.py"], "Coverage >= 90%"),
        ],
        description="Name resolution, scopes, and symbol table"
    ),
    Phase.PHASE_4: PhaseRequirement(
        phase=Phase.PHASE_4,
        name="Static Type Checker & Effect Enforcement",
        gates=[
            QualityGate("pytest_checker", ["pytest", "tests/test_checker.py", "-v"], "Type & effect checker tests pass"),
            QualityGate("mypy", ["mypy", "--strict", "omni_compiler/checker.py"], "Type checking passes"),
            QualityGate("ruff", ["ruff", "check", "omni_compiler/checker.py", "tests/test_checker.py"], "Linting passes"),
            QualityGate("coverage", ["pytest", "--cov=omni_compiler.checker", "--cov-fail-under=90", "--cov-branch", "tests/test_checker.py"], "Coverage >= 90%"),
            QualityGate("effect_soundness", ["pytest", "tests/test_checker.py::test_effect_soundness", "-v"], "Effect soundness property tests"),
        ],
        description="Static types, effects (uses/reads/writes/pure), require/ensure"
    ),
    Phase.PHASE_5: PhaseRequirement(
        phase=Phase.PHASE_5,
        name="OMNI MIR Generator",
        gates=[
            QualityGate("pytest_mir", ["pytest", "tests/test_mir.py", "-v"], "MIR generation tests pass"),
            QualityGate("mypy", ["mypy", "--strict", "omni_compiler/mir.py"], "Type checking passes"),
            QualityGate("ruff", ["ruff", "check", "omni_compiler/mir.py", "tests/test_mir.py"], "Linting passes"),
            QualityGate("coverage", ["pytest", "--cov=omni_compiler.mir", "--cov-fail-under=90", "--cov-branch", "tests/test_mir.py"], "Coverage >= 90%"),
        ],
        description="AST-to-MIR lowering, JSON/CBOR serialization"
    ),
    Phase.PHASE_6: PhaseRequirement(
        phase=Phase.PHASE_6,
        name="JS Emitter & Runtime Boilerplate",
        gates=[
            QualityGate("pytest_emitter", ["pytest", "tests/test_emitter.py", "-v"], "Emitter tests pass"),
            QualityGate("mypy", ["mypy", "--strict", "omni_compiler/emitter.py"], "Type checking passes"),
            QualityGate("ruff", ["ruff", "check", "omni_compiler/emitter.py", "tests/test_emitter.py"], "Linting passes"),
            QualityGate("coverage", ["pytest", "--cov=omni_compiler.emitter", "--cov-fail-under=90", "--cov-branch", "tests/test_emitter.py"], "Coverage >= 90%"),
            QualityGate("snapshot", ["pytest", "tests/test_emitter.py::test_batching", "-v"], "Deterministic batching snapshot tests"),
            QualityGate("bundle_size", ["python", "scripts/check_bundle_size.py"], "JS bundle < 50KB gzipped"),
        ],
        description="ES6 JS emitter, live-link batching, HTML wrapper"
    ),
    Phase.PHASE_7: PhaseRequirement(
        phase=Phase.PHASE_7,
        name="CLI Tool & Conformance Suite",
        gates=[
            QualityGate("pytest_cli", ["pytest", "tests/test_cli.py", "-v"], "CLI tests pass"),
            QualityGate("mypy", ["mypy", "--strict", "omni_compiler/cli.py"], "Type checking passes"),
            QualityGate("ruff", ["ruff", "check", "omni_compiler/cli.py", "tests/test_cli.py"], "Linting passes"),
            QualityGate("coverage", ["pytest", "--cov=omni_compiler.cli", "--cov-fail-under=90", "--cov-branch", "tests/test_cli.py"], "Coverage >= 90%"),
            QualityGate("conformance", ["pytest", "tests/conformance/", "-v"], "Conformance suite passes"),
            QualityGate("perf_check", ["python", "scripts/check_performance.py"], "Performance gates: check <200ms, startup <500ms"),
        ],
        description="CLI tool, conformance suite, final integration"
    ),
}

PHASE_ORDER = [
    Phase.PHASE_0,
    Phase.PHASE_1,
    Phase.PHASE_2,
    Phase.PHASE_3,
    Phase.PHASE_4,
    Phase.PHASE_5,
    Phase.PHASE_6,
    Phase.PHASE_7,
]

def run_command(cmd: List[str], cwd: Path = None, timeout: int = 300) -> Tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def run_gate(gate: QualityGate, cwd: Path) -> Tuple[bool, str]:
    """Run a single quality gate. Returns (success, output)"""
    code, stdout, stderr = run_command(gate.command, cwd=cwd)
    success = code == 0
    output = stdout if success else stderr
    return success, output


def verify_phase(phase: Phase, cwd: Path) -> Tuple[bool, Dict]:
    """Verify all gates for a phase. Returns (all_passed, results_dict)"""
    if phase not in PHASE_REQUIREMENTS:
        return False, {"error": f"No requirements defined for {phase.value}"}
    
    req = PHASE_REQUIREMENTS[phase]
    results = {}
    all_passed = True
    
    print(f"\n{'='*60}")
    print(f"Verifying Phase {phase.value}: {req.name}")
    print(f"Description: {req.description}")
    print(f"{'='*60}")
    
    for gate in req.gates:
        print(f"\n  Running: {gate.name} ({gate.description})")
        print(f"  Command: {' '.join(gate.command)}")
        
        success, output = run_gate(gate, Path.cwd())
        
        results[gate.name] = {
            "passed": success,
            "output": output[:500] if output else "",
            "required": gate.required
        }
        
        if success:
            print(f"  ✅ PASSED")
        else:
            print(f"  ❌ FAILED")
            print(f"  Output: {output[:200]}")
            if gate.required:
                all_passed = False
    
    return all_passed, results


def update_todo_md(phase: Phase, passed: bool):
    """Update TODO.md with phase completion status"""
    todo_path = Path("TODO.md")
    if not todo_path.exists():
        return
    
    content = todo_path.read_text()
    
    phase_map = {
        Phase.PHASE_1: "Phase 1: Lexer & Tokenizer",
        Phase.PHASE_2: "Phase 2: Parser & AST",
        Phase.PHASE_3: "Phase 3: Semantic Analysis & Symbol Table",
        Phase.PHASE_4: "Phase 4: Static Type Checker & Effect Enforcement",
        Phase.PHASE_5: "Phase 5: OMNI MIR Generator",
        Phase.PHASE_6: "Phase 6: JS Emitter & Runtime Boilerplate",
        Phase.PHASE_7: "Phase 7: CLI Tool & Conformance Suite",
    }
    
    phase_name = phase_map.get(phase)
    if not phase_name:
        return
    
    # Update checkbox
    if passed:
        content = content.replace(f"- [ ] {phase_name}", f"- [x] {phase_name}")
        todo_path.write_text(content)
        print(f"\n✅ Updated TODO.md: {phase_name} marked complete")


def main():
    parser = argparse.ArgumentParser(description="Verify OmniScript phase quality gates")
    parser.add_argument("--phase", choices=[p.value for p in Phase] + ["all"], default="all",
                        help="Phase to verify (default: all)")
    parser.add_argument("--list", action="store_true", help="List all phases and their gates")
    parser.add_argument("--cwd", default=".", help="Working directory")
    
    args = parser.parse_args()
    
    cwd = Path(args.cwd).resolve()
    os.chdir(cwd)
    
    if args.list:
        print("Phase Requirements:")
        for phase, req in PHASE_REQUIREMENTS.items():
            print(f"\n  {phase.value}: {req.name}")
            for gate in req.gates:
                print(f"  - {gate.name}: {gate.description}")
        return 0
    
    if args.phase == "all":
        phases_to_verify = [p for p in PHASE_ORDER if p in PHASE_REQUIREMENTS]
    else:
        phases_to_verify = [Phase(args.phase)]
    
    all_results = {}
    all_passed = True
    
    for phase in phases_to_verify:
        passed, results = verify_phase(phase, Path.cwd())
        all_results[phase.value] = {"passed": passed, "results": results}
        
        if passed:
            print(f"\n✅ Phase {phase.value} PASSED")
            update_todo_md(phase, True)
        else:
            print(f"\n❌ Phase {phase.value} FAILED")
            all_passed = False
            # Don't continue to next phase if this one failed
            break
    
    # Save results
    results_file = Path("phase_verification_results.json")
    results_file.write_text(json.dumps(all_results, indent=2))
    print(f"\nResults saved to {results_file}")
    
    if all_passed:
        print("\n🎉 All phases passed!")
        return 0
    else:
        print("\n❌ Some phases failed. See results above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())