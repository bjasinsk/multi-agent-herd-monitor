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

Run:

```shell
uv run aasd
```

Run with debugger:

```shell
uv run debugpy -m aasd
```

Run with autoreload:

```shell
uv run debugpy -m aasd
```
