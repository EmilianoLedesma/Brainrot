# Publish this source on GitHub

The repository's original code and documentation use **MIT OR Apache-2.0**,
at the recipient's choice. Free personal and commercial use, modification and
redistribution are allowed under the selected license's terms. See [LICENSE](../../LICENSE),
[LICENSE-MIT](../../LICENSE-MIT), [LICENSE-APACHE](../../LICENSE-APACHE), and [NOTICE](../../NOTICE).
Third-party terms remain separate; see [third-party notices](third-party-notices.md).

Suggested human-readable credit: **Brainrot by Emiliano Ledesma and contributors**.
A link back to the project's GitHub repository is appreciated. Retain the notices
required by your selected license. Apache 2.0 also includes an express patent
license and requirements concerning changed files and applicable NOTICE content.
Neither option requires a visible credit in every generated video.

## Create the upload archive

From the project root:

```powershell
python scripts/package_source.py
```

This writes `out/releases/brainrot-github-source.zip` from the current checkout,
including uncommitted source changes. It excludes private configuration, local
agent settings, Git metadata, installed dependencies and generated/private media.
The tool checks for configured secret values before writing the archive.

Create a GitHub repository, extract the ZIP, and upload its contents at the
repository root. Do not add another license through GitHub's creation form;
the archive already contains the project license and third-party notices.
Keep dotfiles such as `.gitignore` when uploading. Never upload `.env`, media
archives, OAuth state, tokens, local logs or a copy of a virtual environment.

For this existing Git checkout, normal reviewed commits and pushes are preferable
to reuploading a ZIP. No commit, push or repository creation is performed by the
packaging command. Follow the README/bootstrap guide on another computer and
transfer credentials and private media separately.
