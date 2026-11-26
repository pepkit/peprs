<h1 align="center">
<img src="docs/img/peprs_logo.svg" alt="peprs logo" height="100px">
</h1>

`peprs` - A spicy 🌶️ library for managing biological sample metadata to enable reproducible and scalable bioinformatics

Don't let sample metadata parsing bottleneck your pipelines!

## About this project

`peprs` is a rust implementation of the [PEP specification](https://pep.databio.org/) and expanded ecosystem. In short, PEP is a framework for managing biological sample metadata. PEP is a **community driven** effort to create a **fast**, **reliable**, **reusable**, and **scalable** library for handling biological sample metadata.

PEP and its ecosystem is developed and maintained by the [Databio](https://databio.org) team. As a challenge and learning experience, we have been rewriting the core components of the PEP ecosystem in Rust for performance and reliability.

We are starting with the core PEP specification for metadata management and will expand to include the full ecosystem (looper, pephub-client, pipestat). The core PEP specification is implemented in the `peprs-core` crate. The Python bindings are implemented in the `peprs-py` crate.

### 📦 Modules

- **[peprs-core](peprs-core/)** — Core library implementing the PEP specification. With core module user can create pep objects and do all kind of manipulations.
- **[peprs-eido](peprs-eido/)** — Schema-based validation of PEP projects against JSON schemas with eido-specific extensions (imports, tangible file checks).
- **[peprs-cli](peprs-cli/)** — Command-line interface with `inspect`, `validate`, and `convert` subcommands.
- **[peprs-py](peprs-py/)** — Python bindings via PyO3. Exposes the `Project` class with full Polars/Pandas DataFrame interoperability.
- **[pephub-client](pephub-client/)** — Work in progress

## ⚙️ Installation

### Python (recommended)

```bash
pip install peprs
```

or with `uv`
```bash
uv pip install peprs
```

### Python (from source)

To build and install the Python package from source (requires [maturin](https://www.maturin.rs/) and Rust toolchain):

```bash
git clone https://github.com/pepkit/peprs.git
cd peprs/peprs-py
maturin develop
```

### Rust

Add to your `Cargo.toml`:

```toml
[dependencies]
peprs-core = { git = "https://github.com/pepkit/peprs" }
```

### CLI

Prebuilt binaries are published to [GitHub Releases](https://github.com/khoroshevskyi/peprs/releases) for Linux, macOS, Windows, and FreeBSD (x86_64 and aarch64).

#### Using `ubi` (cross-platform, no Rust required)

[`ubi`](https://github.com/houseabsolute/ubi) auto-detects your platform, downloads the right archive, and installs `peprs`:

```bash
ubi --project khoroshevskyi/peprs --in ~/.local/bin
```

#### Using `cargo-binstall`

```bash
cargo binstall peprs-cli
```

#### Manual download

Grab the archive for your platform from the [releases page](https://github.com/khoroshevskyi/peprs/releases/latest), extract it, and place the `peprs` binary on your `PATH`. For example on Linux x86_64:

```bash
curl -L https://github.com/khoroshevskyi/peprs/releases/latest/download/peprs-Linux-x86_64-musl.tar.gz \
  | tar xz -C ~/.local/bin/
```

#### From source

```bash
cargo install --path peprs-cli
```

#### Using Python

```bash
pip install peprs
```

## 🔧 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PH_HOME` | `~/.pephubclient/` | Directory where the PEPHub auth cache (`jwt.toml`) is stored. |
| `PEPHUB_BASE_URL` | `https://pephub-api.databio.org` | Overrides the PEPHub API endpoint used for login and `Project.from_pephub(...)`. |

## 🐍 Quick Python example

> 💡 Ready-to-run example PEPs live in [`example-peps/`](example-peps/) and example eido schemas live in [`example_schemas/`](example_schemas/). The snippets below use placeholder paths -> swap in a file from those folders (paths or urls) to try them out.

### Load a project

```python
import peprs

# Load a PEP from a YAML config file
project = peprs.Project("path/to/project_config.yaml")
# or pull it straight from PEPHub
project = peprs.Project.from_pephub("databio/example:default")
```

### Inspect the project

```python
print(project.name)
print(project.description)
print(len(project))  # number of samples
```

### Work with samples

```python
# Look up a single sample by name
sample = project.get_sample("3-1_11102016")

# Iterate over samples
for sample in project.samples:
    print(sample)
```

### Convert to a DataFrame

```python
# Polars
df_pl = project.to_polars()
print(df_pl)

# Pandas
df_pd = project.to_pandas()
print(df_pd)
```

### Export the project to specific format

```python
project.write_csv("output.csv")
project.write_yaml("output.yaml")
project.write_json("output.json")
```

### ✅ Validate a project with a Pydantic model

Define the expected shape of your project as a [Pydantic](https://docs.pydantic.dev/) model and let `peprs` validate against it:

```python
import peprs
from peprs.eido import validate_with_pydantic
from pydantic import BaseModel

# Describe the attributes every sample must have
class Sample(BaseModel):
    sample_name: str
    protocol: str
    file: str

project = peprs.Project("path/to/project_config.yaml")

# Raises EidoValidationError if any sample doesn't match the model
try:
    validate_with_pydantic(project, sample_model=Sample)
    print("Project is valid! 🎉")
except Exception as e:
    print(f"{e}")
```

### ✅ Validate a project with a YAML schema

You can also validate against an [eido](https://pep.databio.org/eido/)-style schema stored as a YAML file. The schema describes the attributes each sample must have and which ones are required — see [`example_schemas/sample_schema.yaml`](example_schemas/sample_schema.yaml) for a ready-to-use example.

Point `validate_project` at the schema file:

```python
import peprs
from peprs.eido import validate_project

project = peprs.Project("path/to/project_config.yaml")

# Raises EidoValidationError if any sample doesn't match the schema
try:
    validate_project(project, schema="example_schemas/sample_schema.yaml")
    print("Project is valid! 🎉")
except Exception as e:
    print(f"{e}")
```

## 🖥️ CLI examples

Once the [`peprs` CLI](#cli) is installed, you can work with PEPs straight from the terminal.

### Inspect a PEP

Print a summary of a project and its samples:

```bash
peprs inspect path/to/project_config.yaml
```

Inspect a single sample by name:

```bash
peprs inspect path/to/project_config.yaml --sample-name 3-1_11102016
```

### Validate a PEP against a schema

Validate a project config against an eido schema file (YAML or JSON):

```bash
peprs validate path/to/project_config.yaml --schema example_schemas/sample_schema.yaml
```

### Log in to PEPHub

Authenticate so you can pull and push private projects. Running `login` with no arguments starts an interactive browser-based login:

```bash
peprs client login
```

Or register a token generated in your PEPHub account directly:

```bash
peprs client login --token <YOUR_PEPHUB_TOKEN>
```

## Benchmarks

Comparison of **peppy** (pure Python) vs **peprs** (Rust bindings). Averaged over 3 runs per sample size.

### Initialization Time (seconds)

| Library | 5 | 20 | 100 | 500 | 1,000 | 5,000 | 10,000 | 50,000 | 100,000 | 600,000 |
|---------|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| peppy | 0.019 | 0.026 | 0.096 | 0.428 | 0.851 | 4.226 | 8.700 | 44.017 | 87.613 | 297.433 |
| peprs | 0.003 | 0.002 | 0.002 | 0.003 | 0.004 | 0.014 | 0.036 | 0.043 | 0.068 | 0.339 |
| **speedup** | **7x** | **15x** | **50x** | **149x** | **196x** | **306x** | **244x** | **1,021x** | **1,288x** | **877x** |

### Validation Time (seconds)

| Library | 5 | 20 | 100 | 500 | 1,000 | 5,000 | 10,000 | 50,000 | 100,000 | 600,000 |
|---------|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| peppy | 0.004 | 0.006 | 0.017 | 0.070 | 0.166 | 0.685 | 1.380 | 6.928 | 14.208 | 84.452 |
| peprs | 0.012 | 0.001 | 0.002 | 0.008 | 0.008 | 0.038 | 0.079 | 0.423 | 0.794 | 4.339 |
| **speedup** | **0.4x** | **9x** | **10x** | **9x** | **20x** | **18x** | **17x** | **16x** | **18x** | **19x** |


## 🚀 Afterword

We are looking forward to integrating this project with WDL, Snakemake, and Nextflow. All contributions are welcome. Please open an issue or submit a pull request.