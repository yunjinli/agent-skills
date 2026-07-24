# Pixi manifest templates

Use these as compact starting points, not as mandatory structure. The pattern is based on the TRELLIS and TRELLIS.2 manifests: explicit environments, a shared `base`, and host-specific CUDA/platform features.

## Multi-host CUDA / ML workspace

```toml
[workspace]
name = "my-project"
version = "0.1.0"
description = "Python/CUDA project"
channels = ["conda-forge"]
platforms = ["linux-64", "linux-aarch64"]

[environments]
default  = { features = ["base", "local"],    no-default-feature = true }
vega     = { features = ["base", "vega"],     no-default-feature = true }
leonardo = { features = ["base", "leonardo"], no-default-feature = true }
jupiter  = { features = ["base", "jupiter"],  no-default-feature = true }

[feature.base.dependencies]
python = "3.10.*"
pip = "*"
ninja = "*"
libjpeg-turbo = "*"

[feature.base.pypi-dependencies]
torch = "==2.7.1"
torchvision = "==0.22.1"
numpy = "*"
opencv-python-headless = "<5"
trimesh = "*"
transformers = ">=4.56,<5"

[feature.base.tasks]
install-flash-attn = { cmd = "python -m pip install flash-attn --no-build-isolation --no-cache-dir" }
install-nvdiffrast = { cmd = "python -m pip install git+https://github.com/NVlabs/nvdiffrast.git@v0.4.0 --no-build-isolation" }
install-submodules = { depends-on = ["install-flash-attn", "install-nvdiffrast"] }

[feature.local]
platforms = ["linux-64"]

[feature.local.activation.env]
CUDA_HOME = "/usr/local/cuda-12.8/"
CUDA_PATH = "/usr/local/cuda-12.8/"
# Link-time only. Add only when an extension links with -lcuda.
LIBRARY_PATH = "/usr/local/cuda-12.8/lib64/stubs"

[feature.local.dependencies]
gcc_linux-64 = "11.*"
gxx_linux-64 = "11.*"

[feature.local.pypi-options]
extra-index-urls = ["https://download.pytorch.org/whl/cu128"]

[feature.vega]
platforms = ["linux-64"]

[feature.vega.activation.env]
TORCH_CUDA_ARCH_LIST = "8.0"

[feature.vega.pypi-options]
extra-index-urls = ["https://download.pytorch.org/whl/cu128"]

[feature.leonardo]
platforms = ["linux-64"]

[feature.leonardo.activation.env]
TORCH_CUDA_ARCH_LIST = "8.0"

[feature.leonardo.pypi-options]
extra-index-urls = ["https://download.pytorch.org/whl/cu126"]

[feature.jupiter]
platforms = ["linux-aarch64"]

[feature.jupiter.system-requirements]
libc = "2.34"

[feature.jupiter.activation.env]
TORCH_CUDA_ARCH_LIST = "9.0"

[feature.jupiter.pypi-options]
extra-index-urls = ["https://download.pytorch.org/whl/cu128"]
```

Notes:

- Keep `torch`/`torchvision` version pins in `base` only if every environment can use compatible wheels.
- Keep the CUDA wheel index in the host feature so `base` remains platform-neutral.
- Put x86-only wheels such as some `spconv`, `xformers`, or `open3d` versions in `local`/x86 features, not in `base`.
- For `linux-aarch64`, expect more source builds and more `system-requirements` constraints.

## Standalone side environment

Use this when one stack needs a different Python version or dependency universe. This is cleaner than forcing incompatible simulation or GUI packages into the ML base.

```toml
[environments]
sim = { features = ["sim"], no-default-feature = true }

[feature.sim]
platforms = ["linux-64"]

[feature.sim.dependencies]
python = "3.12.*"

[feature.sim.pypi-dependencies]
mujoco = ">=3.9.0,<4"
trimesh = "*"
coacd = ">=1.0.11,<2"
viser = ">=0.2.11,<0.3"
```

## Package-specific PyTorch wheel indexes

Prefer this when only PyTorch packages should resolve from the CUDA wheel index:

```toml
[feature.local.pypi-dependencies]
torch = { version = "==2.7.1", index = "https://download.pytorch.org/whl/cu128" }
torchvision = { version = "==0.22.1", index = "https://download.pytorch.org/whl/cu128" }
```

Use `extra-index-urls` when an existing manifest intentionally selects CUDA wheels by composing features:

```toml
[feature.local.pypi-options]
extra-index-urls = ["https://download.pytorch.org/whl/cu128"]
```

## Source-build tasks

Use tasks for install flows that Pixi cannot represent cleanly:

```toml
[feature.base.tasks]
install-utils3d = { cmd = "python -m pip install git+https://github.com/EasternJournalist/utils3d.git@<commit> --no-build-isolation" }
install-nvdiffrast = { cmd = "python -m pip install git+https://github.com/NVlabs/nvdiffrast.git@v0.4.0 --no-build-isolation" }
install-extension = { cmd = "python -m pip install ./extension --no-build-isolation" }
install-submodules = { depends-on = ["install-utils3d", "install-nvdiffrast", "install-extension"] }
```

Pin Git dependencies to a commit or fixed tag when reproducibility matters.

## Minimal single-environment project

Do not over-design small projects:

```toml
[workspace]
name = "small-project"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64"]

[dependencies]
python = "3.12.*"

[pypi-dependencies]
numpy = "*"
pytest = "*"

[tasks]
test = "pytest"
```
