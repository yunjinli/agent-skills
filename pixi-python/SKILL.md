---
name: pixi-python
description: Use for designing, reviewing, or repairing Pixi-based Python environments, especially pixi.toml workspaces with PyPI dependencies, conda-forge dependencies, feature/env composition, CUDA/PyTorch wheels, source-built CUDA extensions, ML/CV/robotics stacks, Isaac/physics side environments, and commands that should run through pixi run.
---

# Pixi Python

Prefer Pixi as the project-local Python environment and task runner when a repository has `pixi.toml` or `[tool.pixi.workspace]`.

## Default operating rules

- Inspect the existing `pixi.toml`, `pixi.lock`, features, environments, tasks, README, and CI before changing anything.
- Run Python commands through Pixi: `pixi run python ...`, `pixi run pytest`, or `pixi run -e <env> <task>`.
- Prefer existing project tasks over ad-hoc commands.
- Avoid `pixi shell` for agent work because hidden shell state makes results hard to reproduce.
- Do not initialize or migrate a project to Pixi unless the user asked for environment design/migration.
- Preserve existing constraints unless there is concrete evidence they are wrong.

## Dependency policy

- Use `conda-forge` as the only Conda channel unless the existing project already requires another channel.
- Prefer PyPI dependencies for Python packages.
- Use Conda dependencies mainly for Python itself, compilers, native libraries, and command-line tools.
- Do not declare the same Python package in both `[dependencies]` and `[pypi-dependencies]`.
- Prefer manifest-managed dependencies over install tasks.
- Use tasks only for packages that need nonstandard install flows: submodules, `--no-build-isolation`, custom flags, patches, or generated files.

## CUDA / PyTorch policy

- Treat the system CUDA toolkit as a build tool, not a Conda dependency.
- For this machine and similar local Linux workstations, the expected toolkit is usually `/usr/local/cuda-12.8/`; verify before relying on it.
- Do not add `cudatoolkit`, `cuda-toolkit`, Conda CUDA component packages, or Conda `pytorch-gpu` unless the project explicitly uses that model.
- Install PyTorch from PyPI unless the repository already chose Conda.
- Put CUDA wheel indexes in host-specific features, not in the architecture-neutral base feature.
- Add `LIBRARY_PATH=/usr/local/cuda-12.8/lib64/stubs` only when extension builds need link-time `-lcuda`; never put CUDA stubs in `LD_LIBRARY_PATH`.
- Set `TORCH_CUDA_ARCH_LIST` only for source builds that need it, especially GPU-less cluster login nodes.

## Recommended Pixi structure

For nontrivial ML/CUDA projects, use explicit environment composition:

- `base`: architecture/CUDA-neutral Python deps, shared tools, shared tasks.
- `local`, `vega`, `leonardo`, `jupiter`, etc.: host/cluster/platform-specific CUDA wheel indexes, compilers, system requirements, and architecture-specific deps.
- `sim`, `isaacsim`, or other heavy side stacks: separate standalone environments when Python version or dependency constraints diverge.
- `no-default-feature = true`: use when each environment should be fully explicit.

Do not introduce multi-feature structure for a simple single-platform project.

## When to read references

- Read [references/templates.md](references/templates.md) before creating or substantially refactoring a Pixi manifest.
- Read [references/checklist.md](references/checklist.md) when reviewing a manifest, diagnosing a solve/build issue, or changing CUDA/PyTorch/source-build behavior.

## Validation

After meaningful manifest changes, run checks proportional to the risk:

```bash
pixi list
pixi run python -c "import sys; print(sys.executable)"
pixi run -e <env> python -c "import torch; print(torch.__version__, torch.version.cuda)"
pixi run -e <env> bash -lc '"$CUDA_HOME/bin/nvcc" --version'
```

For source-build tasks, validate imports for the packages installed by the task. If `pixi.lock` changed, report it explicitly.
