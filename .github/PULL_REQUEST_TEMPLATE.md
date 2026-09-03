## Summary

<!-- Brief description of what this PR does and why. -->

## Related issue

<!-- Link to the issue this PR addresses, e.g. "Closes #123". -->

## Checklist

Before requesting a review, please ensure all of the following pass:

```bash
uv run ruff check .           # lint
uv run ruff format --check .  # format
uv run pyrefly check          # type check
uv run pytest tests/ -v       # tests
```

- [ ] Lint passes (`ruff check`)
- [ ] Format passes (`ruff format --check`)
- [ ] Type check passes (`pyrefly check`)
- [ ] Tests pass (`pytest`)
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
