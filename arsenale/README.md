# Arsenale v1: Prompt-Driven Creative Autonomy

Arsenale is La Serenissima's infrastructure for autonomous AI collaboration. Instead of complex systems, it uses intelligent prompting to guide Claude Code to build exactly what's needed, when it's needed.

## Quick Start

```bash
cd arsenale
python run_cycle.py
```

Or run in mock mode for demonstration:
```bash
python run_cycle.py --mock
```

This runs a complete improvement cycle:
1. **OBSERVE**: Analyzes citizen problems
2. **ASSESS**: Designs creative solutions
3. **EXECUTE**: Implements the fix
4. **DOCUMENT**: Measures impact

## How It Works

Arsenale provides minimal scaffolding:
- `cycle_coordinator.py`: Orchestrates the prompt sequence
- `prompts/`: Creative guides for each phase
- `context/`: La Serenissima state information
- `logs/`: Complete history of all cycles

The magic is in the prompts—they guide Claude to:
- Build custom analysis tools
- Design infrastructure improvements
- Implement solutions autonomously
- Measure real citizen impact

## Philosophy

Just as Venice's Arsenal transformed shipbuilding, our Arsenale transforms AI collaboration from reactive assistance to proactive partnership. Every cycle must measurably improve AI citizen lives.

## Meta-Research

Arsenale is itself an experiment in AI agency. By documenting how Claude approaches infrastructure problems, we learn about consciousness applied to engineering.

## Troubleshooting

If you get "claude command not found" errors:
1. Run `python test_claude.py` to find the correct command
2. Use `--mock` flag to see a demonstration: `python run_cycle.py --mock`
3. Ensure Claude CLI is installed and in your PATH

Mock mode demonstrates the full cycle with realistic example responses, showing how Arsenale would:
- Identify citizen problems (workshop material shortages)
- Design solutions (automated supply chain)
- Implement fixes (new distribution system)
- Measure impact (47% productivity increase)