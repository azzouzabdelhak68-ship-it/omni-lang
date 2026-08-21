#!/usr/bin/env python3
from pathlib import Path


def read_md(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding='cp1252')

def generate_compiler_bundle():
    root = Path(__file__).resolve().parent.parent
    compiler_dir = root / 'omni_compiler'
    desktop = Path(r'C:\Users\tiamat\Desktop')
    
    files = sorted([f for f in compiler_dir.rglob('*.py') if f.is_file()])
    
    content = []
    content.append('# OmniScript Compiler Bundle\n')
    content.append(f'> Generated from monorepo source. Total files: {len(files)}\n\n')
    
    total_lines = 0
    for f in files:
        rel = f.relative_to(root)
        text = f.read_text(encoding='utf-8')
        lines = text.splitlines()
        total_lines += len(lines)
        content.append(f'## File: `{rel}`\n')
        content.append(f'```python\n{text}\n```\n\n')
        
    bundle_text = ''.join(content)
    
    # Save to root and desktop
    (root / 'OMNISCRIPT_COMPILER_BUNDLE.md').write_text(bundle_text, encoding='utf-8')
    if desktop.exists():
        (desktop / 'OMNISCRIPT_COMPILER_BUNDLE.md').write_text(bundle_text, encoding='utf-8')
        
    print(f'Compiler bundle generated: {len(files)} files, {total_lines} lines.')

def generate_benchmark_bundle():
    root = Path(__file__).resolve().parent.parent
    benchmark_dir = root / 'OMNISCRIPT_AI_BENCHMARK'
    desktop = Path(r'C:\Users\tiamat\Desktop')
    
    if not benchmark_dir.exists():
        print('Benchmark dir not found')
        return
        
    content = []
    content.append('# v7 Benchmark Suite — Complete Results and Reasoning Ledger\n\n')
    
    runs = sorted(benchmark_dir.rglob('RESULTS.md')) + sorted(benchmark_dir.rglob('BENCHMARK_REASONING.md'))
    # Group by run/project
    
    # Let's do a structured walk of all phases
    for phase_dir in sorted(benchmark_dir.glob('PHASE_*')):
        if not phase_dir.is_dir():
            continue
        content.append(f'# {phase_dir.name}\n\n')
        for proj_dir in sorted(phase_dir.glob('PROJECT_*')):
            if not proj_dir.is_dir():
                continue
            content.append(f'## Project: {proj_dir.name}\n\n')
            for run_dir in sorted(proj_dir.glob('RUN_*')):
                if not run_dir.is_dir():
                    continue
                content.append(f'### Run: {run_dir.name}\n\n')
                
                res_file = run_dir / 'RESULTS.md'
                if res_file.exists():
                    content.append('#### RESULTS.md\n\n')
                    content.append(read_md(res_file) + '\n\n')
                    
                reas_file = run_dir / 'BENCHMARK_REASONING.md'
                if reas_file.exists():
                    content.append('#### BENCHMARK_REASONING.md\n\n')
                    content.append(read_md(reas_file) + '\n\n')
                    
    bundle_text = ''.join(content)
    
    (root / 'V7_ALL_BENCHMARK_AND_REASONING.md').write_text(bundle_text, encoding='utf-8')
    (root / 'all_benchmarks_and_reasoning.md').write_text(bundle_text, encoding='utf-8')
    
    if desktop.exists():
        (desktop / 'V7_ALL_BENCHMARK_AND_REASONING.md').write_text(bundle_text, encoding='utf-8')
        (desktop / 'all_benchmarks_and_reasoning.md').write_text(bundle_text, encoding='utf-8')
        
    print('Benchmark bundle generated successfully.')

if __name__ == '__main__':
    generate_compiler_bundle()
    generate_benchmark_bundle()
