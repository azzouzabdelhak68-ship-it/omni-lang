# Benchmark Reasoning: PROJECT_11_COLLECTIONS_LOG_ANALYZER

## Project Overview
Implement a log analysis and data processing engine using OMNISYS.collections (Map, List, Set, Deque).

## Investigation Log

### 2026-08-18: Initial Investigation
- **Status**: Starting investigation
- **Task**: Implement log analysis engine with collection operations

### OMNISYS.collections Module Analysis
Found in `omnisys/registry.py`:
- **List operations**: push, pop, get, set, slice, append, contains, index_of, remove, sort, reverse, fold, map, filter, join, zip
- **Map operations**: get, set, remove, has, keys, values, size
- **Set operations**: add, remove, has, size, union, intersection, difference
- **Deque operations**: push_front, push_back, pop_front, pop_back, size
- **Heap operations**: push, pop, peek, size
- **RingBuffer operations**: new, push, pop, size

### Key Design Decisions
1. **Log Record Model**: Use Map objects with timestamp, severity, source, message fields
2. **Collection Operations**: Leverage OMNISYS.collections for filtering, grouping, aggregation, sorting
3. **Effect Declarations**: Use `uses collections` for collection operations
4. **Entry Point**: `when app starts:` block for demonstration

### Implementation Plan
1. Define LogRecord type as Map
2. Implement log ingestion and filtering functions
3. Implement grouping and aggregation functions
4. Implement sorting and top-N reporting
5. Create formatted summary output
6. Demo in `when app starts:` showing all features

### Probes Needed
1. Test basic OMNISYS.collections import and List operations
2. Test Map operations (set/get/remove/size)
3. Test filtering by severity
4. Test grouping by source
5. Test sorting and aggregation
6. Test summary report generation

### Acceptance Criteria
- `omni check source/log_analyzer.omni` exits with code 0
- `omni run source/log_analyzer.omni` outputs summary report
- All tests in `tests/` pass

## Next Steps
1. Create probe files to verify collections API behavior
2. Implement log_analyzer.omni
3. Create test suite
4. Verify with `omni check` and `omni run`
5. Create RESULTS.md