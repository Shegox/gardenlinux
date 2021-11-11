import os
import urllib.parse

import ccc.github
import glci.github


def update_status(
    giturl: str,
    committish: str,
    repo_dir: str,
):
    repo_dir = os.path.abspath(repo_dir)
    repo_url = urllib.parse.urlparse(giturl)
    github_cfg = ccc.github.github_cfg_for_hostname(
        repo_url.hostname,
    )

    glci.github.post_github_status(
        github_cfg=github_cfg,
        committish=committish,
        state=glci.github.GitHubStatus.PENDING,
        description='Pipeline run started',
    )
