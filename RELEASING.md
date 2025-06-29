# Release procedure

1. Check the changelog looks good
2. Add release date to changelog, and increment version in `pyproject.toml`
3. Commit changes - `git commit -m RLS: vx.y.z` (or `git commit --allow-empty -m 'RLS: v0.2.1'` if already done)
4. Tag the release commit: `git tag -a vx.y.z -m "Version x.y.z"`
4. Push the release commit and tag to main `git push --follow tags` (`git push upstream main --follow tags` is the more general specification)