# Publishing

Every push to `main` runs the complete test matrix and, after it succeeds,
publishes a new development release to PyPI. Publication uses OpenID Connect
Trusted Publishing; no PyPI token is stored in GitHub.

## One-Time PyPI Setup

Before the first publishing workflow runs, create a pending trusted publisher
at <https://pypi.org/manage/account/publishing/> with these exact values:

| Field | Value |
| --- | --- |
| PyPI project name | `pydagitty` |
| GitHub owner | `marcandre259` |
| GitHub repository | `pydagitty` |
| Workflow filename | `ci.yml` |
| Environment name | `pypi` |

The pending publisher creates the PyPI project during the first successful
publication. Later runs use the publisher attached to that project.

## Versioning

`setuptools-scm` derives versions from Git history. Untagged `main` commits
produce monotonically increasing PEP 440 development versions such as
`0.1.dev2`. The workflow checks out complete history so each pushed commit has
a unique version accepted by PyPI.

For a stable release, tag the intended commit with a PEP 440 version and push
the tag. For example:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Tags beginning with `v` run the same test and publishing pipeline. Do not push
both a new `main` commit and its stable tag simultaneously: publish the tagged
release first, then continue development on `main`.

## Security

The `publish` job receives `id-token: write` only after every supported Python
version passes tests, lint, and strict type checking. The GitHub `pypi`
environment can optionally require reviewers before publication.
