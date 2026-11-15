# HVAC Schedule Integration for Home Assistant

# Generic rules

1. Development language is Engish. All files except localization files must be writted in development language

# Codestyle guidelines

1. Each file must contain not more than 1 class. If file contains a class, the filename must be the same as the class name
2. Limit lines to 120 characters, including indentation. Keep function signatures, calls, and expressions on one line
   when they fit within this limit; do not introduce unnecessary line breaks.

# Validation

1. All Python code changes must pass Pylance type checking in strict mode. For command-line validation, use Pyright with the project's `pyproject.toml` configuration: `uvx pyright` (or `.venv/bin/uvx pyright` when using the project's virtual environment).
2. Validate both the integration code and tests. The result must contain zero errors and zero warnings. Do not weaken strict mode or exclude changed files to make validation pass.
3. Do not add diagnostic suppressions without the user's approval.

# Project Evolution

1. Every project change must support upgrading the component in place by installing the new version over the existing version, without removing and re-adding the integration.
2. Preserve existing configuration, user settings, entity identities, and behavior unless a change is explicitly intended. Provide automatic migrations or backward-compatible defaults for stored data when its structure changes; do not require manual edits to Home Assistant storage.
3. Verify upgrade compatibility with configuration from the previous version. New optional features must remain disabled for existing installations unless the user explicitly enables them.
