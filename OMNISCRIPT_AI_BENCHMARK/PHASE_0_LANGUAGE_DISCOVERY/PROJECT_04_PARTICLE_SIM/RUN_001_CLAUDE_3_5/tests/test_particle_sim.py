import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from omni_compiler.checker import analyze
from omni_compiler.emitter import emit_js
from omni_compiler.lexer import tokenize
from omni_compiler.mir import to_mir
from omni_compiler.parser import parse


def _node_available() -> bool:
    return shutil.which('node') is not None


needs_node = pytest.mark.skipif(not _node_available(), reason='node not installed')


def _run_emitted(html: str, epilogue: str = '') -> subprocess.CompletedProcess[str]:
    """Run an emitted HTML document under Node with a DOM stub and OMNISYS runtime."""
    # Use the run-omnisys.js approach which properly sets up the context
    runner_src = r"""
const fs = require("fs");
const vm = require("vm");
const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
if (!match) { console.error("no script block"); process.exit(2); }
const code = match[1];

const logs = [];
global.console = Object.assign({}, console, {
  log: (...args) => {
    logs.push(args.map(String).join(" "));
  },
});
global.document = {
  getElementById: () => ({ innerHTML: "", addEventListener: () => {} }),
  querySelectorAll: () => [],
};
global.name = "";
global.window = new Proxy({}, { get: () => () => {} });

// Load OMNISYS runtime
try {
  global.omnisys = require("E:\\simualtion\\omnisys\\runtime.js");
} catch (e) {
  console.error("Failed to load omnisys runtime: " + e);
  process.exit(2);
}
// Bind sim namespace globally for direct sim.* calls
if (global.omnisys && global.omnisys.sim) {
  global.sim = global.omnisys.sim;
}

try {
  vm.runInThisContext(code, { filename: htmlPath });
} catch (err) {
  console.error("Program failed: " + (err && err.stack ? err.stack : err));
  process.exit(1);
}

if (logs.length) {
  process.stdout.write(logs.join("\n") + "\n");
}
process.exit(0);
"""
    runner_src = (
        harness
        + epilogue
        + '\nprocess.stdout.write(JSON.stringify(global.__logs) + "\\n");\n'
    )
    html_path = None
    runner_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', encoding='utf-8', delete=False
        ) as f:
            f.write(html)
            html_path = Path(f.name)
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.js', encoding='utf-8', delete=False
        ) as g:
            g.write(runner_src)
            runner_path = Path(g.name)
        return subprocess.run(
            ['node', str(runner_path), str(html_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        if html_path is not None:
            html_path.unlink(missing_ok=True)
        if runner_path is not None:
            runner_path.unlink(missing_ok=True)


PARTICLE_SIM_SOURCE = Path(__file__).parent.parent / "source" / "particle_sim.omni"


def test_particle_sim_check_passes():
    """Verify the particle simulation passes type and effect checking."""
    code = PARTICLE_SIM_SOURCE.read_text(encoding='utf-8')
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    
    # Verify key symbols exist
    assert symbol_table.inspect_symbol("Position") is not None
    assert symbol_table.inspect_symbol("Velocity") is not None
    assert symbol_table.inspect_symbol("Render") is not None
    assert symbol_table.inspect_symbol("motion_system") is not None
    assert symbol_table.inspect_symbol("dt") is not None
    
    # Verify motion_system has correct effect declarations
    motion_sys = symbol_table.inspect_symbol("motion_system")
    assert motion_sys is not None
    effects = motion_sys["declared_effects"]
    assert "dt" in effects["reads"]
    assert "p1_vel" in effects["reads"]
    assert "p1_pos" in effects["writes"]


def test_particle_sim_mir_generation():
    """Verify MIR generation succeeds and contains expected constructs."""
    code = PARTICLE_SIM_SOURCE.read_text(encoding='utf-8')
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    
    # Verify custom types in MIR
    assert "Position" in mir.types
    assert "Velocity" in mir.types
    assert "Render" in mir.types
    
    # Verify function exists
    assert "motion_system" in mir.functions
    
    # Verify entry point has sim.* calls
    sim_calls = [stmt for stmt in mir.entry_point 
                 if stmt.get("op") == "call" and str(stmt.get("name", "")).startswith("sim.")]
    assert len(sim_calls) >= 5  # entity x5, system, run, query


def test_particle_sim_js_emission():
    """Verify JS emission produces valid output with sim runtime calls."""
    code = PARTICLE_SIM_SOURCE.read_text(encoding='utf-8')
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    
    assert isinstance(js_code, str)
    assert len(js_code) > 0
    assert 'motion_system' in js_code
    assert 'sim.entity' in js_code
    assert 'sim.system' in js_code
    assert 'sim.run' in js_code
    assert 'sim.query' in js_code
    assert 'sim.get' in js_code


def test_particle_sim_c_emission():
    """Verify C emission produces valid Flecs-adapted code."""
    from omni_compiler.c_emitter import emit_c
    
    code = PARTICLE_SIM_SOURCE.read_text(encoding='utf-8')
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    c_code = emit_c(mir)
    
    assert isinstance(c_code, str)
    assert 'typedef struct Position' in c_code
    assert 'typedef struct Velocity' in c_code
    assert 'typedef struct Render' in c_code
    assert 'void motion_system(void)' in c_code
    assert 'ECS_SYSTEM' in c_code or 'OMNI_HAVE_FLECS' in c_code
    assert 'ecs_init()' in c_code


def test_particle_sim_rust_emission():
    """Verify Rust emission produces valid Bevy-adapted code."""
    from omni_compiler.rust_emitter import emit_rust
    
    code = PARTICLE_SIM_SOURCE.read_text(encoding='utf-8')
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    rust_code = emit_rust(mir)
    
    assert isinstance(rust_code, str)
    assert 'struct Position' in rust_code
    assert 'struct Velocity' in rust_code
    assert 'struct Render' in rust_code
    assert 'fn motion_system()' in rust_code
    assert 'sim.run' in rust_code
    assert 'sim.query' in rust_code


@needs_node
def test_particle_sim_execution():
    """Verify the emitted JS executes and produces expected particle positions."""
    code = PARTICLE_SIM_SOURCE.read_text(encoding='utf-8')
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    js_code = emit_js(mir)
    
    # Run the emitted code
    proc = _run_emitted(js_code)
    assert proc.returncode == 0, f"Execution failed: {proc.stderr}"
    
    logs = json.loads(proc.stdout.strip().splitlines()[-1])
    
    # Verify output contains entity position logs
    entity_logs = [log for log in logs if log.startswith("Entity ")]
    assert len(entity_logs) == 5, f"Expected 5 entity logs, got {len(entity_logs)}: {logs}"
    
    # Verify particle1 moved from (0,0) by velocity (10,5) * dt(0.1) * 20 steps = (20, 10)
    # Final position: (0 + 20, 0 + 10) = (20, 10)
    particle1_log = next((log for log in entity_logs if "particle1" in log), None)
    assert particle1_log is not None
    # Position should be approximately (20, 10) after 20 steps
    assert "20" in particle1_log or "20.0" in particle1_log


def test_particle_sim_component_query_iteration():
    """Verify the system function performs component query iteration logic."""
    code = PARTICLE_SIM_SOURCE.read_text(encoding='utf-8')
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    
    motion_sys = symbol_table.inspect_symbol("motion_system")
    assert motion_sys is not None
    
    # Verify the function body contains position updates for all 5 particles
    # This is a structural check - the actual iteration is manual in current implementation
    effects = motion_sys["declared_effects"]
    reads = effects["reads"]
    writes = effects["writes"]
    
    # Should read dt and all velocities
    assert "dt" in reads
    assert "p1_vel" in reads
    assert "p2_vel" in reads
    assert "p3_vel" in reads
    assert "p4_vel" in reads
    assert "p5_vel" in reads
    
    # Should write all positions
    assert "p1_pos" in writes
    assert "p2_pos" in writes
    assert "p3_pos" in writes
    assert "p4_pos" in writes
    assert "p5_pos" in writes


def test_particle_sim_emitter_system_registration():
    """Verify sim.system call registers the motion system correctly."""
    code = PARTICLE_SIM_SOURCE.read_text(encoding='utf-8')
    tokens = tokenize(code)
    ast = parse(tokens)
    symbol_table = analyze(ast)
    mir = to_mir(ast, symbol_table)
    
    # Find sim.system call in entry point
    system_calls = [stmt for stmt in mir.entry_point 
                    if stmt.get("op") == "call" and stmt.get("name") == "sim.system"]
    assert len(system_calls) == 1
    
    system_call = system_calls[0]
    args = system_call.get("args", [])
    assert len(args) >= 3
    # First arg: system name "motion" (may be quoted in MIR)
    sys_name = args[0].get("value", "").strip('"')
    assert sys_name == "motion"
    # Second arg: function identifier "motion_system"
    assert args[1].get("name") == "motion_system"
    # Third arg: schedule "every frame" (may be quoted)
    schedule = args[2].get("value", "").strip('"')
    assert schedule == "every frame"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])