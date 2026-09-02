# Plan: Make `pep.config` mutable and persistable from Python

## The question

Can we do this from Python and have it stick?

```python
pep = Project("project_config.yaml")
pep.config["something"] = "nothing"   # mutate
pep.write_raw("out/")                 # saved config contains the change
```

**Answer: yes, but it requires a change on the Rust side.** It cannot be done in
pure Python today — the current `config` accessor hands back a throwaway copy, so
any mutation is silently lost.

---

## Why it doesn't work today

`Project.config` is a read-only getter in `peprs-py/src/project.rs` (`get_config`,
lines ~670–681):

```rust
#[getter]
pub fn get_config(&self) -> PyResult<Py<PyAny>> {
    Python::attach(|py| match &self.inner.config {
        Some(config) => {
            let value = config.get_raw_config(None, None);   // clone of raw
            let obj = pythonize(py, &value)?;                // brand-new dict
            Ok(obj.into())
        }
        None => Ok(py.None()),
    })
}
```

Every access to `pep.config`:

1. clones the Rust config (`ProjectConfig.get_raw_config`, `peprs-core/src/config.rs:225`),
2. builds a **fresh** Python dict via `pythonize`.

So `pep.config["something"] = "nothing"` mutates a temporary dict that is
immediately discarded. There is:

- no `#[setter]` for `config` (whole-dict replacement), and
- no live proxy object that writes back into the Rust struct on item assignment.

The next read of `pep.config` re-derives the dict from the untouched Rust
`ProjectConfig`, so the edit is gone.

Compare with `name`/`description`, which *do* round-trip because they have both a
getter and a `#[setter]` that mutate `inner.config` (`project.rs:646–661`,
delegating to `Project::set_name`/`set_description` in `peprs-core/src/project.rs:388–405`).

---

## Where the config actually lives

`ProjectConfig` (`peprs-core/src/config.rs:29`) has:

- **typed fields**: `pep_version`, `name`, `description`, `sample_table`,
  `subsample_table`, `sample_table_index`, `subsample_table_index`,
  `sample_modifiers`, `project_modifiers`;
- **`raw: Option<serde_json::Value>`** — the full original config as parsed from YAML.

`get_raw_config()` (`config.rs:225`) is the single source of truth for what
Python sees and what gets serialized. It:

1. clones `raw`,
2. **overlays** `name`, `description`, `pep_version` from the typed fields on top,
3. optionally overlays `sample_table` / `subsample_table`.

The save path (`write_raw` → `raw_pep_files` in `peprs-core/src/utils.rs:219`)
serializes exactly this `get_raw_config()` output to `project_config.yaml`.

**Two consequences that shape the design:**

1. **Writing into `raw` persists** to the saved config file — *except* for
   `name`/`description`/`pep_version`, which are always re-overlaid from the typed
   fields. Edits to those three keys must be routed to the typed fields (or the
   overlay behavior must change).
2. **Structural fields are consumed at build time.** `sample_modifiers`,
   `project_modifiers`, `sample_table`, indices, etc. are parsed into typed fields
   and drive sample processing during `.build()`
   (`finalize_project_creation`, `peprs-core/src/project.rs:944`). Editing them in
   `config` *after* construction changes only what gets **saved**, not the
   already-processed `samples` DataFrame. (See "Reprocessing caveat".)

---

## Recommended approach: a live `Config` proxy (`pep.config["x"] = "y"`)

This is the only approach that supports the exact ergonomics the user asked for.

### Idea

Introduce a `#[pyclass(name = "Config")]` mapping object that holds a handle back
to its parent `PyProject` (a `Py<PyProject>`, exactly like `PySamplesIter` already
does in `peprs-py/src/samples.rs:107–111`). It implements the Python mapping
protocol and, on every write, mutates the parent's `inner.config` in place.

Ownership is clean: the proxy stores only a `Py<PyProject>` handle (a Python
reference-counted pointer), not a Rust borrow. On each operation it does
`self.project.bind(py).borrow()` / `.borrow_mut()` to reach the config — no
aliasing conflict, no need to wrap the core in `Rc<RefCell>`/`Arc<Mutex>`.

### New file: `peprs-py/src/config.rs`

```rust
use pyo3::prelude::*;
use pyo3::exceptions::{PyKeyError, PyRuntimeError};
use pyo3::types::PyDict;
use pythonize::{depythonize, pythonize};
use serde_json::Value;

use crate::project::PyProject;

#[pyclass(name = "Config", mapping)]
pub struct PyConfig {
    pub project: Py<PyProject>,
}

#[pymethods]
impl PyConfig {
    fn __getitem__(&self, py: Python, key: &str) -> PyResult<Py<PyAny>> {
        let proj = self.project.borrow(py);
        let cfg = proj.inner.config.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Project has no config"))?;
        // read through get_raw_config so name/description/pep_version are correct
        let value = cfg.get_raw_config(None, None).unwrap_or(Value::Null);
        match value.get(key) {
            Some(v) => Ok(pythonize(py, v)
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?.into()),
            None => Err(PyKeyError::new_err(key.to_string())),
        }
    }

    fn __setitem__(&self, py: Python, key: &str, value: Py<PyAny>) -> PyResult<()> {
        let mut proj = self.project.borrow_mut(py);
        let cfg = proj.inner.config.as_mut()
            .ok_or_else(|| PyRuntimeError::new_err("Project has no config"))?;

        // ensure raw exists
        if cfg.raw.is_none() {
            cfg.raw = Some(Value::Object(Default::default()));
        }
        let json_val: Value = depythonize(value.bind(py))
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        // route the three overlaid keys to typed fields so they aren't masked
        match key {
            "name"        => cfg.name = json_val.as_str().map(str::to_string),
            "description" => cfg.description = json_val.as_str().map(str::to_string),
            "pep_version" => {
                if let Some(s) = json_val.as_str() { cfg.pep_version = s.to_string(); }
            }
            _ => {}
        }
        // always mirror into raw (source of truth for serialization)
        if let Some(Value::Object(map)) = cfg.raw.as_mut() {
            map.insert(key.to_string(), json_val);
        }
        Ok(())
    }

    fn __delitem__(&self, py: Python, key: &str) -> PyResult<()> {
        let mut proj = self.project.borrow_mut(py);
        let cfg = proj.inner.config.as_mut()
            .ok_or_else(|| PyRuntimeError::new_err("Project has no config"))?;
        if let Some(Value::Object(map)) = cfg.raw.as_mut() { map.remove(key); }
        match key {
            "name"        => cfg.name = None,
            "description" => cfg.description = None,
            _ => {}
        }
        Ok(())
    }

    fn __contains__(&self, py: Python, key: &str) -> bool {
        let proj = self.project.borrow(py);
        proj.inner.config.as_ref()
            .and_then(|c| c.get_raw_config(None, None))
            .map(|v| v.get(key).is_some())
            .unwrap_or(false)
    }

    fn __len__(&self, py: Python) -> usize { self.to_value(py).map(map_len).unwrap_or(0) }

    fn keys(&self, py: Python) -> Vec<String> { /* from to_value(py) */ }
    fn values(&self, py: Python) -> PyResult<Py<PyAny>> { /* ... */ }
    fn items(&self, py: Python) -> PyResult<Py<PyAny>> { /* ... */ }

    #[pyo3(signature = (key, default=None))]
    fn get(&self, py: Python, key: &str, default: Option<Py<PyAny>>) -> Py<PyAny> {
        self.__getitem__(py, key).unwrap_or_else(|_| default.unwrap_or_else(|| py.None()))
    }

    fn update(&self, py: Python, other: &Bound<'_, PyDict>) -> PyResult<()> {
        for (k, v) in other.iter() {
            self.__setitem__(py, &k.extract::<String>()?, v.unbind())?;
        }
        Ok(())
    }

    fn to_dict(&self, py: Python) -> PyResult<Py<PyAny>> {
        let v = self.to_value(py)?;              // serde_json::Value
        Ok(pythonize(py, &v).map_err(|e| PyRuntimeError::new_err(e.to_string()))?.into())
    }

    fn __repr__(&self, py: Python) -> String { /* format!("Config({...})") */ }
}
```

(`to_value`/`map_len` are small private helpers; sketch elided.)

### Change the getter to return the proxy

In `peprs-py/src/project.rs`, replace the `get_config` getter body so it hands
back a `PyConfig` bound to the same project. The getter needs the `Py<Self>`
handle, so switch to the `Py<Self>` receiver form (as `py_samples_iter` does at
`project.rs:690`):

```rust
#[getter(config)]
fn get_config(slf: Py<Self>, py: Python<'_>) -> PyResult<Py<PyConfig>> {
    Py::new(py, PyConfig { project: slf })
}
```

### Optional: a whole-dict setter

Add a `#[setter] set_config` on `PyProject` so `pep.config = {...}` also works:
depythonize the dict into `serde_json::Value`, set `cfg.raw = Some(value)`, then
re-derive the typed fields (`serde_json::from_value` into `ProjectConfig`, or at
least sync `name`/`description`/`pep_version`).

### Register the class

Add `pub mod config;` and `m.add_class::<PyConfig>()?;` in `peprs-py/src/lib.rs`.

---

## Simpler alternative (no proxy)

If the exact `pep.config["x"] = "y"` syntax is not essential, a much smaller change
is a pair of explicit methods on `PyProject` in `peprs-py/src/project.rs`:

```python
pep.set_config_value("something", "nothing")   # single key
pep.update_config({"a": 1, "b": 2})            # merge a dict
pep.config = {...}                             # whole-dict setter (@setter)
```

Each mutates `inner.config.raw` (and syncs the typed name/description/pep_version).
Pros: ~30 lines, no new class, `pep.config` stays a plain `dict` (keeps the current
`isinstance(config, dict)` test passing). Cons: does not give the requested
subscript-assignment ergonomics.

**Recommendation:** implement the proxy (primary ask), and keep `update_config`
as a convenience for bulk edits.

---

## Persistence — how edits reach disk

No changes needed to the save path. Once the edit lands in `inner.config` (raw +
synced typed fields):

- `pep.write_raw("out/")` / `write_raw("out.zip", zipped=True)` →
  `raw_pep_files` → `get_raw_config()` serializes the modified config to
  `project_config.yaml`.
- `pep.to_dict(raw=True)["config"]` reflects the edit.
- `peprs-core`'s `ProjectConfig::save_yaml` / `write_config_yaml` /
  `write_config_json` likewise.

---

## Caveats to document in the docstring / `.pyi`

1. **Reprocessing.** Editing structural keys (`sample_modifiers`,
   `project_modifiers`, `sample_table`, `*_table_index`) changes only the
   **saved/serialized** config, not the already-processed `samples`. The sample
   table is computed once during `.build()`
   (`finalize_project_creation`, `peprs-core/src/project.rs:944`).
   - *Optional follow-up:* add `Project.reprocess()` / `rebuild()` in peprs-core
     that re-runs `finalize_project_creation` from the current `config` + raw
     samples, so config edits can take effect on samples in-process. Treat as a
     separate task.
2. **`name`/`description`/`pep_version`** are stored in typed fields and overlaid
   on read/save; the proxy routes writes to those keys accordingly so
   `pep.config["name"] = "x"` and `pep.name` stay consistent.
3. **`isinstance(pep.config, dict)` becomes False** with the proxy — it's now a
   `Config` mapping. Update `test_config_property`
   (`peprs-py/tests/test_project.py:84`) to assert mapping behavior
   (`pep.config["..."]`, `to_dict()`), and register `Config` as a
   `collections.abc.MutableMapping` in the `.pyi` if strict typing is desired.

---

## Files to change

| File | Change |
|------|--------|
| `peprs-py/src/config.rs` | **new** — `PyConfig` mapping proxy |
| `peprs-py/src/project.rs` | change `get_config` to return `PyConfig`; optional `set_config` setter; optional `update_config` |
| `peprs-py/src/lib.rs` | `pub mod config;` + `m.add_class::<PyConfig>()?;` |
| `peprs-py/py_src/peprs/__init__.pyi` | retype `config` as `Config` mapping; document caveats; add `Config` stub |
| `peprs-py/tests/test_project.py` | update `test_config_property`; add round-trip + persistence tests |
| `peprs-core/src/project.rs` | *(optional)* `reprocess()` for config edits to affect samples |

---

## Test plan (`peprs-py/tests/test_project.py`)

```python
def test_config_item_assignment_persists(example_pep_cfg_path):
    p = Project(example_pep_cfg_path)
    p.config["something"] = "nothing"
    assert p.config["something"] == "nothing"          # survives re-read

def test_config_edit_saved(tmp_path, example_pep_cfg_path):
    p = Project(example_pep_cfg_path)
    p.config["something"] = "nothing"
    p.write_raw(str(tmp_path / "out"))
    import yaml
    saved = yaml.safe_load((tmp_path / "out" / "project_config.yaml").read_text())
    assert saved["something"] == "nothing"

def test_config_name_key_syncs_typed_field(example_pep_cfg_path):
    p = Project(example_pep_cfg_path)
    p.config["name"] = "renamed"
    assert p.name == "renamed"                          # typed field stays in sync

def test_config_update_and_delete(example_pep_cfg_path):
    p = Project(example_pep_cfg_path)
    p.config.update({"a": 1, "b": 2})
    assert p.config["a"] == 1 and p.config["b"] == 2
    del p.config["a"]
    assert "a" not in p.config
```

Also add a Rust unit test in `peprs-core` if a `reprocess()` method is added.

---

## Effort estimate

- Proxy + getter change + registration: ~120 lines Rust, half a day.
- `.pyi` + tests: ~1–2 hours.
- Optional `reprocess()` in core: separate, larger task (re-run modifier pipeline).
