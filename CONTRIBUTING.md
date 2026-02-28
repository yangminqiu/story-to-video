# Contributing to story-to-video

Thanks for contributing! This guide keeps PRs fast to review and easy to merge.

## Development setup

```bash
git clone https://github.com/lymcho/story-to-video.git
cd story-to-video
pip install -r requirements.txt
cp .env.example .env
```

## Branch naming

Use one of these prefixes:
- `feat/` new feature
- `fix/` bug fix
- `docs/` docs only
- `chore/` maintenance

Example:
```bash
git checkout -b feat/shorts-export
```

## Pull request checklist

Before opening a PR:
- [ ] Keep scope focused (one purpose per PR)
- [ ] Run basic local checks (at least Python syntax)
- [ ] Update README/docs if behavior changes
- [ ] Include clear test/usage notes in PR description

## Commit message style

Prefer concise imperative messages, e.g.:
- `Add YouTube Shorts generator`
- `Fix subtitle timestamp formatting`
- `Update README quick start`

## Reporting issues

Please use issue templates and provide:
- Environment (OS + Python version)
- Reproduction steps
- Expected vs actual behavior
- Logs/errors if available
