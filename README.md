# gitsweep

> Find stale branches, large files, and bloated git history.

[![PyPI](https://img.shields.io/pypi/v/kryptorious-gitsweep)](https://pypi.org/project/kryptorious-gitsweep/) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Part of the [Kryptorious developer toolkit](https://kryptorious.gumroad.com/l/jbvet) — 31 open-source tools, one $9 lifetime license.

## Install

```bash
pip install kryptorious-gitsweep
```

## Quickstart

```bash
gitsweep clean --aggressive
# -> deletes merged+stale branches after reporting
```

## Commands

| Command | Description |
|---------|-------------|
| `gitsweep clean` | Safe mode: report stale branches and large files without deleting. |
| `gitsweep clean --aggressive` | Actually delete merged-and-stale branches; lower the large-file threshold. |
| `gitsweep clean --repo path/to/repo` | Target a specific repository. |



## License

MIT — free for personal and commercial use. The $9 lifetime license adds DevFlow Premium (multi-environment CI/CD, approval gates, infrastructure-as-code). Get it at [kryptorious.gumroad.com/l/jbvet](https://kryptorious.gumroad.com/l/jbvet).
