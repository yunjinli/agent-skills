# Pixi Python review checklist

## Before editing

- Locate the Pixi workspace root.
- Read `pixi.toml` and check whether the project also uses `[tool.pixi.workspace]` in `pyproject.toml`.
- Check `pixi.lock` state and avoid unnecessary lock churn.
- Identify all environments and their feature composition.
- Identify whether tasks are part of the install/build workflow.

## Manifest structure

- `channels = ["conda-forge"]` unless the project has a documented exception.
- Platform list matches real targets; do not add `linux-aarch64` unless it is actually targeted.
- Shared Python deps live in `base`; host-specific CUDA/platform details live in host features.
- Side stacks with incompatible Python or heavy GUI/sim constraints are isolated in their own env.
- `no-default-feature = true` is used when env composition should be explicit.

## Dependency placement

- Python packages usually belong in `[pypi-dependencies]`.
- Python itself, compilers, CMake, Ninja, system libraries, and native CLIs usually belong in `[dependencies]`.
- No package is duplicated between Conda and PyPI dependency sections.
- Source installs are represented as Pixi PyPI git/path dependencies when possible.
- Install tasks are reserved for custom sequences, submodules, build flags, or `--no-build-isolation`.

## CUDA and PyTorch

- Confirm `CUDA_HOME` if extension builds require CUDA.
- Do not add Conda CUDA toolkit packages unless the project intentionally uses Conda CUDA.
- Keep CUDA wheel indexes in host features.
- Check `torch`, `torchvision`, `torchaudio`, Python version, platform, and CUDA wheel availability together.
- Set `TORCH_CUDA_ARCH_LIST` for GPU-less source builds or cluster builds where auto-detection is impossible.
- Use CUDA stubs only via `LIBRARY_PATH` for link-time `-lcuda`; never via `LD_LIBRARY_PATH`.

## Commands

Prefer:

```bash
pixi run python -m pytest
pixi run -e local python -c "import torch; print(torch.__version__, torch.version.cuda)"
pixi run -e local bash -lc '"$CUDA_HOME/bin/nvcc" --version'
pixi run -e local install-submodules
```

Avoid:

```bash
python script.py
pip install package
pixi shell
```

## Failure diagnosis

- Solve failures: check platforms, Python version pins, PyPI indexes, architecture-specific wheels, and `system-requirements`.
- Import failures after install tasks: check whether the task ran in the intended env and whether the install is absent from `pixi.lock` by design.
- CUDA extension failures: check `CUDA_HOME`, `nvcc`, compiler version, PyTorch CUDA runtime, `TORCH_CUDA_ARCH_LIST`, and missing stubs.
- aarch64 failures: suspect unavailable wheels first; use source-build paths or platform-specific pins.
