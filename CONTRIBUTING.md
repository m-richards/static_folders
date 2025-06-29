# Contribution Guidelines
Contributions to static_folders are most welcome. However, it's worth noting at this point,
it's still very early in development, and is maintained in spare time, between my other commitments. 

I'd like to have more fleshed out guidance here, but it's not a priority for the moment.

## Running CI locally

Using pixi as a task runner, which is perhaps a bit overkill. See pixi.toml for commands. Summary is:
- `pixi run format` to run ruff format
- `pixi run lint` to run ruff check
- `pixi run type_check` to run mypy
- `pixi run ci_all` to run these steps alltogether
