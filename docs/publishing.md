# Publishing

The `CI` workflow runs for pull requests, pushes to `main`, and tags matching
`v*`. Pull requests and `main` pushes validate releases but never publish them.
Stable publication is available only to a pushed `v*` tag and only after all
quality, artifact, and cross-platform smoke jobs pass.

## CI and Artifact Gates

Linux runs the complete test suite on Python 3.10, 3.11, 3.12, and 3.13. Ruff
and strict mypy run once in a separate job rather than once per Python version.
After those jobs pass, CI performs one build of the wheel and source
distribution and runs `twine check` on both.

The built distributions, not an editable checkout, are then installed with the
`viz` extra and smoke-tested in fresh jobs. The matrix covers Python 3.10 and
3.13 on Ubuntu, macOS, and Windows, with both wheel and source distribution
installs represented. Smoke coverage includes import location and version
metadata, graph construction, separation, adjustment, and Graphviz source
generation. One Ubuntu job also installs the system `dot` executable and
renders SVG.

## One-Time GitHub and PyPI Setup

Create a GitHub environment named `pypi`. Configure required reviewers, prevent
self-review, and restrict deployment tags to `v*`. These environment controls
provide the release review after all automated gates have succeeded and before
GitHub requests a publishing identity token.

Before the first release, create a pending trusted publisher at
<https://pypi.org/manage/account/publishing/> with these exact values:

| Field | Value |
| --- | --- |
| PyPI project name | `pydagitty` |
| GitHub owner | `marcandre259` |
| GitHub repository | `pydagitty` |
| Workflow filename | `ci.yml` |
| Environment name | `pypi` |

The pending publisher creates the PyPI project during the first successful
publication. Later releases use the trusted publisher attached to the project.
No long-lived PyPI token is stored in GitHub. Only the final `publish` job has
`id-token: write`; it receives no repository-content permission.
Third-party actions are pinned to reviewed commit SHAs, including both actions
that execute inside the OIDC-enabled publication job.

## Stable Release

`setuptools-scm` derives the package version from Git history. Create a PEP 440
version tag on a commit that has passed review, then push the tag. For example:

```bash
git tag v0.1.0
git push origin v0.1.0
```

CI checks out complete history for the build. It reads version metadata from
both generated artifacts and requires both versions to exactly equal the tag
with its leading `v` removed. Thus `v0.1.0` can publish only artifacts whose
version is exactly `0.1.0`; a mismatch fails before any environment approval or
OIDC request.

After all gates pass, a required reviewer approves the `pypi` environment and
the workflow publishes the already-tested artifacts. Do not move or reuse a
published tag. Use a new PEP 440 version for every release.

Development publication is not configured. Untagged commits still receive
development versions from `setuptools-scm`, but pushes to `main` only build and
test those artifacts.
