"""
12_repo.py -- turn the built site into a ready-to-push git repository, and emit a
bundle so it can be pushed from any machine without this sandbox.

Outputs
    ~/uniranks/out/repo/                     the working tree, git initialised, one commit
    ~/uniranks/out/uni-rankings-repo.bundle  a git bundle (full history, one file)
    ~/uniranks/out/uni-rankings-repo.zip     zip of the working tree incl. .git
"""
import os, shutil, subprocess, glob

SITE = os.path.expanduser("~/uniranks/site")
OUT = os.path.expanduser("~/uniranks/out")
REPO = f"{OUT}/repo"

if os.path.isdir(REPO):
    shutil.rmtree(REPO)
shutil.copytree(SITE, REPO)

os.makedirs(f"{REPO}/.github/workflows", exist_ok=True)
open(f"{REPO}/.github/workflows/pages.yml", "w").write("""name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: .
      - id: deployment
        uses: actions/deploy-pages@v4
""")

open(f"{REPO}/.gitignore", "w").write(
    "__pycache__/\n*.pyc\n.DS_Store\n*.npz\nposterior*.npz\n")

open(f"{REPO}/LICENSE", "w").write("""Code (everything under code/): MIT License.

Copyright (c) 2026 Charles Crabtree

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

--------------------------------------------------------------------------------

Derived estimates (everything under data/ produced by this pipeline): CC BY 4.0.

The underlying published rankings remain the property of their publishers. This
repository redistributes harmonised extracts for research replication; see
data/SOURCES.txt for the provenance of every input file and check the terms of the
original publisher before redistributing any of it further.
""")

env = dict(os.environ, GIT_AUTHOR_NAME="Charles Crabtree",
           GIT_AUTHOR_EMAIL="crabtreedcharles@gmail.com",
           GIT_COMMITTER_NAME="Charles Crabtree",
           GIT_COMMITTER_EMAIL="crabtreedcharles@gmail.com",
           GIT_AUTHOR_DATE="2026-08-12T12:00:00+0000",
           GIT_COMMITTER_DATE="2026-08-12T12:00:00+0000")


def git(*a, **kw):
    return subprocess.run(["git", "-C", REPO, *a], env=env, check=kw.get("check", True),
                          capture_output=True, text=True)


git("init", "-q", "-b", "main")
git("add", "-A")
git("commit", "-q", "-m", """A latent measure of international university standing, 2003-2026

Twelve international ranking systems harmonised and pooled with a dynamic Bayesian
latent-trait model: each ranking enters as one noisy, censored instrument reading a
single underlying quantity.

- 115 system-editions, 72k published listings, ~3.2k institutions, 24 reference years
- blocked Gibbs sampler with FFBS over the latent paths; interval censoring for banded
  ranks, left censoring for non-listing
- per-row retrieval provenance so weaker channels can be dropped and the model refit""")

msg = git("log", "--oneline", "-1").stdout.strip()
subprocess.run(["git", "-C", REPO, "bundle", "create",
                f"{OUT}/uni-rankings-repo.bundle", "--all"],
               env=env, check=True, capture_output=True)
shutil.make_archive(f"{OUT}/uni-rankings-repo", "zip", OUT, "repo")

sz = sum(os.path.getsize(os.path.join(r, f))
         for r, _, fs in os.walk(REPO) for f in fs if ".git/" not in r)
print(f"repo ready at {REPO}")
print(f"  commit: {msg}")
print(f"  tracked size: {sz/1e6:.1f} MB")
print(f"  bundle: {OUT}/uni-rankings-repo.bundle "
      f"({os.path.getsize(f'{OUT}/uni-rankings-repo.bundle')/1e6:.1f} MB)")
print(f"  zip:    {OUT}/uni-rankings-repo.zip "
      f"({os.path.getsize(f'{OUT}/uni-rankings-repo.zip')/1e6:.1f} MB)")
print("\nlargest tracked files:")
fs = sorted(((os.path.getsize(p), os.path.relpath(p, REPO))
             for p in glob.glob(f"{REPO}/**/*", recursive=True)
             if os.path.isfile(p) and "/.git/" not in p), reverse=True)[:8]
for s, p in fs:
    print(f"  {s/1e6:7.2f} MB  {p}")
