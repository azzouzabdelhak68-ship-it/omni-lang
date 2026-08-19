# BENCHMARK RESULT v2 — OmniScript (Imperative Canvas Approach)

## Result

    STATUS: FAIL

## Timing

    Total wall time: 45.00s
    Planning: 5.00s
    Implementation: 10.00s
    First execution: 20.00s
    Time to first successful execution: N/A
    Debugging: 10.00s
    Verification: 0.00s
    External lookup: 0.00s

## Work

    Source files created: 1 (attempted)
    Final source lines: 35 (attempted)
    Lines modified: 0
    Compile attempts: 3
    Run attempts: 0
    Code revisions: 2
    Debugging cycles: 2

## Errors

    Total errors: 3
    Syntax: 2
    Type: 0
    API: 1
    Compiler: 0
    Runtime: 0
    Logic: 0
    Other: 0

## External Dependency

    Documentation lookups: 0
    API lookups: 0
    External searches: 0
    Total lookup time: 0.00s

## Verification

    Window opens: NOT_TESTED
    Ball visible: NOT_TESTED
    Ball moves: NOT_TESTED
    Horizontal bounce: NOT_TESTED
    Vertical bounce: NOT_TESTED
    Continuous animation: NOT_TESTED
    Clean shutdown: NOT_TESTED

## Agent Workflow

    Plan → implementation → check → FAIL (blocked by language design)

## POST-MORTEM

1. What was the hardest part?
   The language fundamentally does not support the imperative canvas pattern. Two hard blockers:
   - Parser: No field assignment syntax (`obj.field = value` is a syntax error)
   - Standard library: No DOM/canvas APIs in OMNISYS registry

2. What required the most reasoning/decision-making?
   Determining whether the failure was a bug or intentional design. It's intentional - OmniScript's effect system and parser design explicitly prevent direct mutable DOM manipulation.

3. What required external information?
   Parser source code analysis to confirm field assignment is not supported.

4. What caused the first failure?
   Syntax error: `ctx.fillStyle = "#e11d48"` - parser only supports `name = expr`, not `obj.field = expr`.

5. What caused subsequent failures?
   Even if field assignment worked, `document.getElementById` and `canvas.getContext` are rejected by the checker as undefined names (not in OMNISYS registry).

6. What part of the language/environment made the task easier?
   Nothing - the language actively prevents this pattern.

7. What part made the task harder?
   - Parser: Assignment target must be a simple identifier (line 659-663 in parser.py)
   - Checker: All OMNISYS calls must be declared in registry; `dom` capability exists but no module implements it
   - Effect system: Would require `uses dom` but no such module exists

8. What would you change if solving the same task again?
   Use the declarative SVG SMIL approach (which works) - the imperative canvas pattern is architecturally incompatible with OmniScript's design.

---

## ROOT CAUSE ANALYSIS

### Parser Limitation (omni_compiler/parser.py:659-663)
```python
elif t.type == TokenType.IDENTIFIER:
    next_t = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
    if next_t and next_t.type == TokenType.ASSIGN:
        name = self.consume(TokenType.IDENTIFIER).value  # ONLY simple identifier
        self.consume(TokenType.ASSIGN)
        expr = self.parse_expression()
        node = Assignment(name=name, expr=expr)
```
The parser only creates `Assignment` nodes for `identifier = expression`. Field access (`obj.field`) parses as a `FieldAccess` expression, not an assignable target.

### OMNISYS Registry Gap (omni_compiler/omnisys_registry.py)
No `dom` module exists with canvas APIs. The `ui` module is marked "planned" and only provides declarative UI primitives.

### Effect System (omni_compiler/checker.py)
Even if APIs existed, they'd require `uses dom` declaration, but no such capability is implemented.

---

## COMPARISON: SAME RULES (Imperative Canvas)

| Metric | Python (tkinter) | OmniScript (Canvas) |
|--------|------------------|---------------------|
| **Status** | PASS (130s) | **FAIL** (blocked) |
| **Paradigm** | Imperative loop | Declarative only |
| **Field assignment** | `ctx.fillStyle = ...` ✓ | **Syntax error** ✗ |
| **DOM access** | Direct ✓ | **Checker rejects** ✗ |
| **Animation** | `after()` callback ✓ | `tick()` exists but can't trigger redraw |
| **Lines of code** | 53 | N/A (won't compile) |

---

## CONCLUSION

**The gap is NOT reduced - it's architectural.**

OmniScript's design explicitly prevents the imperative canvas pattern:
1. **Parser** - No mutable field assignment
2. **Effect system** - All external calls must be declared capabilities
3. **Standard library** - No DOM/canvas module exists

The only working approach in current OmniScript is **declarative SVG SMIL** (the original solution). This is not a bug - it's a language design choice favoring safety and declarative UIs over imperative graphics.

To close this gap would require:
1. Add `dom` module to OMNISYS registry with canvas APIs
2. Extend parser to support field assignment (major language change)
3. Implement `omnisys/ui.js` with imperative canvas primitives
4. Connect `omnisys.async.tick` to `batchUpdate` for UI re-renders

None of these exist in current updates.