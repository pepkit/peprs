from typing import Any, Dict, List, Mapping, Optional, Union, Iterator

from polars import DataFrame as PolarsDataFrame
from pandas import DataFrame as PandasDataFrame


class Sample:
    """A single sample with both attribute and dict-style access.

    Supports attribute access (``sample.col``), dict-style access
    (``sample["col"]``), ``in`` checks, ``len()``, and dict-like
    ``keys()``, ``values()``, ``items()``, ``get()`` methods.
    """

    def __getitem__(self, key: str) -> Any:
        """Get a sample attribute by key.

        :param key: column name
        :return: attribute value
        :raises KeyError: if the key is not found
        """
        ...

    def __getattr__(self, name: str) -> Any:
        """Get a sample attribute by name.

        :param name: column name
        :return: attribute value
        :raises AttributeError: if the attribute is not found
        """
        ...

    def __contains__(self, key: str) -> bool: ...
    def __len__(self) -> int: ...
    def __repr__(self) -> str: ...

    def keys(self) -> List[str]:
        """Return list of column names."""
        ...

    def values(self) -> List[Any]:
        """Return list of attribute values."""
        ...

    def items(self) -> List[tuple[str, Any]]:
        """Return list of (column_name, value) pairs."""
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """Get a sample attribute, returning *default* if not found.

        :param key: column name
        :param default: value to return if key is absent (default ``None``)
        """
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict of column names to values."""
        ...


class Project:
    """A PEP (Portable Encapsulated Projects) project.

    Wraps a Rust-backed PEP project providing access to sample metadata,
    project configuration, and serialization methods.
    """

    name: Optional[str]
    """Project name, or None if not set."""

    description: Optional[str]
    """Project description, or None if not set."""

    pep_version: str
    """PEP specification version string."""

    sample_name_colname: str
    """Column name used as the sample table index (default: "sample_name")."""

    config: "Config"
    """Live, mutable view of the project configuration.

    Returns a :class:`Config` mapping backed by this project. Item assignment
    (``project.config["key"] = value``) mutates the project's config in place and
    persists across accesses. Assigning a whole dict (``project.config = {...}``)
    replaces the config. Editing structural keys (e.g. ``sample_modifiers``)
    updates the saved config immediately; call :meth:`reprocess` to apply them to
    the processed sample table.
    """

    samples: SamplesIter
    """Iterator over processed samples. Each element is a ``Sample`` object."""

    sample_table: PandasDataFrame
    """Deprecated ``peppy``-compatible alias for :meth:`to_pandas`.

    Processed sample table as a Pandas DataFrame indexed by the sample-name
    column (default ``sample_name``), kept as a column too, so both
    ``pep.sample_table["<col>"]`` and ``pep.sample_table.loc["<sample_name>"]``
    behave as under peppy.

    .. deprecated::
        Accessing this property emits a ``DeprecationWarning`` and it will be
        removed in a future release. Use :meth:`to_pandas` instead.
    """

    subsample_table: Optional[PolarsDataFrame]
    """Flat subsample table as a Polars DataFrame, formed by concatenating the
    project's subsample tables vertically, or ``None`` if the project defines no
    subsamples."""

    def __init__(
        self,
        path: str,
        amendments: Optional[List[str]] = None,
        sample_table_index: Optional[str] = None,
        subsample_table_index: Optional[List[str]] = None,
    ) -> None:
        """Create a new Project from a YAML config or CSV file path.

        :param path: path to a .yaml/.yml config or .csv sample table
        :param amendments: list of amendment names to activate
        :param sample_table_index: column name to use as the sample index
        :param subsample_table_index: column names for subsample table indices
        """
        ...

    @classmethod
    def from_polars(
        cls,
        df: PolarsDataFrame,
        sample_table_index: Optional[str] = None,
    ) -> "Project":
        """Create a Project from a Polars DataFrame.

        :param df: a Polars DataFrame with sample data
        :param sample_table_index: column name for the sample index (default: "sample_name")
        """
        ...

    @classmethod
    def from_pandas(
        cls,
        df: PandasDataFrame,
        sample_table_index: Optional[str] = None,
    ) -> "Project":
        """Create a Project from a Pandas DataFrame.

        :param df: a Pandas DataFrame with sample data
        :param sample_table_index: column name for the sample index (default: "sample_name")
        """
        ...

    @classmethod
    def from_dict(cls, pep_dictionary: Dict[str, Any]) -> "Project":
        """Create a Project from a Python dict.

        :param pep_dictionary: dict with keys "config", "samples", and optionally "subsamples".
            "config" should be a dict of project config.
            "samples" should be a list of sample dicts.
            "subsamples" should be a list of lists of subsample dicts.
        """
        ...

    @classmethod
    def from_sample_yaml(
        cls,
        yaml_file: str,
        sample_table_index: Optional[str] = None,
    ) -> "Project":
        """Create a Project from a YAML file containing raw sample records.

        :param yaml_file: path to a YAML file with sample data (list-of-dicts
            or dict-of-lists)
        :param sample_table_index: column name to use as the sample index
            (default: "sample_name")
        """
        ...

    @classmethod
    def from_pephub(cls, registry: str) -> "Project":
        """Create a Project from a PEPHub registry path.

        :param registry: PEPHub registry path (e.g. "namespace/name:tag")
        """
        ...

    def to_dict(
        self, raw: bool = False, by_sample: bool = True
    ) -> Dict[str, Any]:
        """Convert the project to a Python dict.

        :param raw: if True, include raw config/samples/subsamples; otherwise processed samples only
        :param by_sample: if True, samples are a list of row-dicts; if False, a column-dict
        :return: dict with "config", "samples", and optionally "subsamples" keys
        """
        ...

    def to_polars(self, raw: bool = False) -> PolarsDataFrame:
        """Return the samples as a Polars DataFrame.

        :param raw: if True, return raw (unprocessed) samples; otherwise processed
        :return: Polars DataFrame of samples
        """
        ...

    def to_pandas(self, raw: bool = False) -> PandasDataFrame:
        """Return the samples as a Pandas DataFrame indexed by the sample-name column.

        The frame is indexed by the sample table index column (default
        ``sample_name``) without dropping it, mirroring peppy's sample table so
        that both ``df["<col>"]`` and ``df.loc["<sample_name>"]`` work. If the
        index column is absent, the frame keeps its default range index.

        :param raw: if True, return raw (unprocessed) samples; otherwise processed
        :return: Pandas DataFrame of samples
        """
        ...

    def write_yaml(self, path: str) -> None:
        """Write processed samples to a YAML file.

        :param path: destination file path
        """
        ...

    def write_json(self, path: str) -> None:
        """Write processed samples to a JSON file.

        :param path: destination file path
        """
        ...

    def write_csv(self, path: str) -> None:
        """Write processed samples to a CSV file.

        :param path: destination file path
        """
        ...

    def write_raw(self, path: str, zipped: bool = False) -> None:
        """Write the raw project (config, samples, subsamples) to disk.

        :param path: destination path (folder or zip file)
        :param zipped: if True, write as a zip archive; otherwise as a folder
        """
        ...

    def to_yaml_string(self) -> str:
        """Return processed samples as a YAML string."""
        ...

    def to_json_string(self) -> str:
        """Return processed samples as a JSON string."""
        ...

    def to_csv_string(self) -> str:
        """Return processed samples as a CSV string."""
        ...

    def get_sample(self, name: str) -> Sample:
        """Look up a single sample by name.

        :param name: sample name to look up
        :return: Sample object for the matching sample
        :raises ValueError: if the sample name is not found
        """
        ...

    def get_samples(self, names: Union[str, List[str]]) -> List[Sample]:
        """Look up multiple samples by name.

        :param names: a single sample name, or a list of sample names
        :return: list of Sample objects for the matching samples. Names not
            found in the sample table are silently skipped.
        """
        ...

    def list_amendments(self) -> List[str]:
        """Return the names of amendments defined in the PEP config.

        :raises ValueError: if the PEP defines no amendments
        """
        ...

    def activate_amendments(self, amendments: List[str]) -> None:
        """Activate one or more amendments, reloading the project from its config.

        :param amendments: amendment names to activate
        :raises ValueError: if the PEP defines no amendments, was not loaded
            from a config file, or names an amendment that does not exist
        """
        ...

    def reprocess(self) -> None:
        """Re-run sample processing from the current in-memory config and tables.

        Recomputes the processed sample table by re-applying the config's sample
        modifiers and subsample merge to the in-memory raw samples/subsamples.
        Does **not** read anything from disk. Call this after mutating
        :attr:`config` so the processed samples reflect the changes.

        :raises ValueError: if the project has no config
        """
        ...

    def add_sample(self, sample: Mapping[str, Any]) -> None:
        """Add a new sample to the project's raw sample table.

        Appends one row to the raw sample table. The processed sample table is
        left unchanged; call :meth:`reprocess` afterward to fold the new sample
        into the processed output. Columns new to the project are added (existing
        rows become null); columns omitted from ``sample`` are null for the new
        row.

        :param sample: a mapping of attribute name to value describing the sample
        :raises ValueError: if ``sample`` is not a mapping
        :raises RuntimeError: if the sample's index value (e.g. ``sample_name``)
            already exists in the raw sample table
        """
        ...

    def len(self) -> int:
        """Return the number of samples in the project."""
        ...

    def __len__(self) -> int: ...
    def __repr__(self) -> str: ...


class Config:
    """A live, mutable mapping view over a :class:`Project`'s configuration.

    Reads go through the owning project and writes mutate its config in place, so
    changes persist across accesses and are written out by
    :meth:`Project.write_raw` and ``Project.to_dict(raw=True)``. Editing
    structural keys (e.g. ``sample_modifiers``) updates the saved config
    immediately; call :meth:`Project.reprocess` to apply them to the processed
    sample table.
    """

    def __getitem__(self, key: str) -> Any:
        """Get a config value by key.

        :raises KeyError: if the key is not present
        """
        ...

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a config value, mutating the owning project's config in place."""
        ...

    def __delitem__(self, key: str) -> None:
        """Remove a config key.

        :raises KeyError: if the key is not present
        """
        ...

    def __contains__(self, key: str) -> bool: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[str]: ...
    def __repr__(self) -> str: ...

    def keys(self) -> List[str]:
        """Return the config's top-level keys."""
        ...

    def values(self) -> List[Any]:
        """Return the config's top-level values."""
        ...

    def items(self) -> List[tuple[str, Any]]:
        """Return the config's top-level (key, value) pairs."""
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value, returning *default* if the key is absent."""
        ...

    def update(self, other: Dict[str, Any]) -> None:
        """Merge the key/value pairs from *other* into the config."""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain (non-live) ``dict`` copy of the config."""
        ...


class SamplesIter:
    """Iterator over project samples.

    Each iteration yields a ``Sample`` object.
    Supports indexing (including negative indices) and len().
    """

    def __iter__(self) -> "SamplesIter": ...

    def __next__(self) -> Sample:
        """Yield the next sample."""
        ...

    def __getitem__(self, index: int) -> Sample:
        """Get a sample by index. Supports negative indexing.

        :param index: zero-based index; negative values count from the end
        :return: Sample object
        """
        ...

    def __len__(self) -> int: ...
    def __repr__(self) -> str: ...
