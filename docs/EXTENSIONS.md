# Extensions

The audit found that data analyst behavior is not a direct source feature.

Not implemented as direct port:

- CSV/Excel/Parquet dataset ingestion
- dataframe profiling
- dataset Q&A
- pandas/polars analysis workflow
- generated Python analysis sandbox
- chart artifact generation over datasets
- browser artifact editor/preview/download

If added later, these should live as optional extension skills/services and be traced separately from the Claude Code-like assistant runtime.

Potential extension skills:

- `load_dataset`
- `profile_dataset`
- `answer_dataset_question`
- `generate_python_analysis_code`
- `execute_python_analysis_code`
- `create_visualization`
- `create_analysis_artifact`
- `export_analysis_artifact`

