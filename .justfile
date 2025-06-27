# Display recipes when `just` is run without a target
default:
    @just --list

# FastAPI server
run args...:
    @echo "▶️  Starting API with: {{args}}"
    uv run uvicorn mcp_mitm_mem0.api:app {{args}}

# Pytest with coverage flags already in pytest.ini; forward any extra args
test args...:
    @echo "🧪 Running tests"
    uv run pytest {{args}}

# Ruff format + lint + (basic) type-checking rules
lint:
    @echo "🎨 Ruff format"
    uv run ruff format .
    @echo "🔎 Ruff lint --fix"
    uv run ruff check --fix .
    @echo "✅ Ruff final pass"
    uv run ruff check .

# (Optional but handy) install all dependency groups
install:
    uv sync --all-groups
