# AASD

### Install

Install the project

```shell
uv sync
```

Install pre-commit hooks:

```shell
pre-commit install
```

If you're using VS Code:

```shell
cp -r .vscode-sample .vscode
```

### Run

Start the spade Server in the background (kindly ignore the errors):

```shell
uv run spade run
```

Run the Streamlit live dashboard:

```shell
uv run streamlit run src/aasd/dashboard.py
```

Run:

```shell
uv run aasd [--scenario <PATH_TO_SCENARIO>]
```

Available scenarios:

- `all_infected.json` - All cows infected and spaced closely, should move away from each other
- `base_infected.json` - One infected cow and four healthy, the healthy ones should move away
- `infeasible.json` - Global boundaries too small to ensure proper spacing. Cows should move to boundary corners maximizing the distance between them
- `oneline.json` - All cows aligned in one line, communication only between neighbors
- `out_of_bounds.json` - Cows placed outside global boundaries, should move towards them
- `spaced_apart.json` - Cows spaced to far for communication, should indicate how some cows posses outdated information

### Development

Run with debugger:

```shell
uv run debugpy -m aasd
```

Run with autoreload:

```shell
uv run watchmedo auto-restart --pattern "*.py" --recursive  aasd
```

Run tests:

```shell
uv run pytest
```

Lint and format:

```shell
uv run ruff check --fix
uv run ruff format
uv run mypy .
```
