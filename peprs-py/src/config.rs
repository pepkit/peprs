use pyo3::exceptions::{PyKeyError, PyRuntimeError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pythonize::{depythonize, pythonize};
use serde_json::Value;

use crate::project::PyProject;

///
/// A live, mutable mapping view over a [`PyProject`]'s configuration.
///
/// Item access reads through the project's config, and item assignment mutates
/// the project's config in place, so changes persist across accesses and are
/// written out by `Project.write_raw` / `to_dict(raw=True)`. Editing structural
/// keys (e.g. `sample_modifiers`) affects the saved config immediately; call
/// `Project.reprocess()` to apply them to the processed sample table.
///
#[pyclass(name = "Config", mapping)]
pub struct PyConfig {
    /// Handle back to the owning project; all reads/writes go through it.
    pub project: Py<PyProject>,
}

impl PyConfig {
    ///
    /// Snapshot the project's merged raw config as a JSON value.
    ///
    /// Returns `Value::Null` if the project has no config.
    ///
    pub(crate) fn snapshot(&self, py: Python<'_>) -> PyResult<Value> {
        let proj = self.project.borrow(py);
        match &proj.inner.config {
            Some(config) => Ok(config.get_raw_config(None, None).unwrap_or(Value::Null)),
            None => Ok(Value::Null),
        }
    }
}

#[pymethods]
impl PyConfig {
    fn __getitem__(&self, py: Python<'_>, key: &str) -> PyResult<Py<PyAny>> {
        match self.snapshot(py)?.get(key) {
            Some(v) => Ok(pythonize(py, v)
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
                .into()),
            None => Err(PyKeyError::new_err(key.to_string())),
        }
    }

    fn __setitem__(&self, py: Python<'_>, key: &str, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let json_val: Value =
            depythonize(value).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let mut proj = self.project.borrow_mut(py);
        let cfg = proj
            .inner
            .config
            .as_mut()
            .ok_or_else(|| PyRuntimeError::new_err("Project has no config"))?;
        cfg.set_raw_field(key, json_val)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(())
    }

    fn __delitem__(&self, py: Python<'_>, key: &str) -> PyResult<()> {
        let mut proj = self.project.borrow_mut(py);
        let cfg = proj
            .inner
            .config
            .as_mut()
            .ok_or_else(|| PyRuntimeError::new_err("Project has no config"))?;
        let present = cfg
            .get_raw_config(None, None)
            .map(|v| v.get(key).is_some())
            .unwrap_or(false);
        if !present {
            return Err(PyKeyError::new_err(key.to_string()));
        }
        cfg.remove_raw_field(key);
        Ok(())
    }

    fn __contains__(&self, py: Python<'_>, key: &str) -> PyResult<bool> {
        Ok(self.snapshot(py)?.get(key).is_some())
    }

    fn __len__(&self, py: Python<'_>) -> PyResult<usize> {
        Ok(self.snapshot(py)?.as_object().map(|m| m.len()).unwrap_or(0))
    }

    fn __iter__(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let list = PyList::empty(py);
        for k in self.keys(py)? {
            list.append(k)?;
        }
        Ok(list.as_any().try_iter()?.unbind().into_any())
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        Ok(format!("Config({})", self.snapshot(py)?))
    }

    fn keys(&self, py: Python<'_>) -> PyResult<Vec<String>> {
        Ok(self
            .snapshot(py)?
            .as_object()
            .map(|m| m.keys().cloned().collect())
            .unwrap_or_default())
    }

    fn values(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        let snap = self.snapshot(py)?;
        let mut out = Vec::new();
        if let Some(map) = snap.as_object() {
            for v in map.values() {
                out.push(
                    pythonize(py, v)
                        .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
                        .into(),
                );
            }
        }
        Ok(out)
    }

    fn items(&self, py: Python<'_>) -> PyResult<Vec<(String, Py<PyAny>)>> {
        let snap = self.snapshot(py)?;
        let mut out = Vec::new();
        if let Some(map) = snap.as_object() {
            for (k, v) in map {
                out.push((
                    k.clone(),
                    pythonize(py, v)
                        .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
                        .into(),
                ));
            }
        }
        Ok(out)
    }

    #[pyo3(signature = (key, default=None))]
    fn get(&self, py: Python<'_>, key: &str, default: Option<Py<PyAny>>) -> PyResult<Py<PyAny>> {
        match self.snapshot(py)?.get(key) {
            Some(v) => Ok(pythonize(py, v)
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
                .into()),
            None => Ok(default.unwrap_or_else(|| py.None())),
        }
    }

    ///
    /// Merge the key/value pairs from a dict into the config.
    ///
    fn update(&self, py: Python<'_>, other: &Bound<'_, PyDict>) -> PyResult<()> {
        for (k, v) in other.iter() {
            let key: String = k.extract()?;
            self.__setitem__(py, &key, &v)?;
        }
        Ok(())
    }

    ///
    /// Return a plain (non-live) `dict` copy of the config.
    ///
    fn to_dict(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        Ok(pythonize(py, &self.snapshot(py)?)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
            .into())
    }
}
