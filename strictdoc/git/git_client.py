import os.path
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from strictdoc.helpers.timing import measure_performance

PATH_TO_TMP_DIR = tempfile.gettempdir()
PATH_TO_SANDBOX_DIR = os.path.join(
    PATH_TO_TMP_DIR, "strictdoc_cache", "git_sandbox"
)


class GitClient:
    def __init__(self, path_to_git_root: str):
        assert os.path.isdir(path_to_git_root)
        self.path_to_git_root: str = path_to_git_root

    @staticmethod
    def create_repo_from_local_copy(revision: str):
        with measure_performance(f"Copy Git repo: {revision}"):
            path_to_cwd = os.getcwd()
            path_to_sandbox_git_repo = os.path.join(
                PATH_TO_SANDBOX_DIR, revision
            )
            path_to_sandbox_git_repo_git = os.path.join(
                path_to_sandbox_git_repo, ".git"
            )
            if revision != "HEAD+" and os.path.exists(
                path_to_sandbox_git_repo_git
            ):
                git_client = GitClient(path_to_sandbox_git_repo)

                if git_client.is_clean_branch():
                    return git_client

            Path(PATH_TO_SANDBOX_DIR).mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                [
                    "rsync",
                    "-ra",
                    "--delete",
                    "--exclude=.idea/",
                    "--exclude=.ruff_cache/",
                    "--exclude=__pycache__/",
                    "--exclude=build/",
                    "--exclude=output/",
                    "--exclude=strictdoc-project.github.io/",
                    ".",
                    path_to_sandbox_git_repo,
                ],
                cwd=path_to_cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, result

            git_client = GitClient(path_to_sandbox_git_repo)

            if revision != "HEAD+":
                git_client.hard_reset(revision=revision)
                git_client.clean()

            return git_client

    def is_git_repo(self):
        """
        https://stackoverflow.com/a/16925062/598057
        """
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout == "true"

    def is_clean_branch(self):
        """
        https://unix.stackexchange.com/a/155077/77389
        """
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.returncode != 0:
            return False
        return result.stdout == ""

    def add_file(self, path_to_file):
        result = subprocess.run(
            ["git", "add", path_to_file],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.returncode == 0, result

    def add_all(self):
        result = subprocess.run(
            ["git", "add", "."],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.returncode == 0, result

    def commit(self, message: str):
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.returncode == 0, result

    def check_revision(self, revision: str):
        assert isinstance(revision, str)
        assert len(revision) > 0
        result = subprocess.run(
            ["git", "rev-parse", revision],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        raise LookupError(f"Non-existing revision: {revision}.")

    def commit_all(self, message: str):
        result = subprocess.run(
            ["git", "commit", "-a", "-m", message],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.returncode == 0, result

    def rebase_from_main(self):
        result = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.returncode == 0, result
        result = subprocess.run(
            ["git", "rebase", "origin/main"],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.returncode == 0, result

    def push(self):
        result = subprocess.run(
            ["git", "push", "origin"],
            cwd=self.path_to_git_root,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.returncode == 0, result

    def hard_reset(self, revision: Optional[str] = None):
        reset_args = ["git", "reset", "--hard"]
        if revision is not None:
            reset_args.append(revision)
        result = subprocess.run(
            reset_args,
            cwd=self.path_to_git_root,
            capture_output=False,
            text=True,
            check=True,
        )
        assert result.returncode == 0, result

    def clean(self):
        result = subprocess.run(
            ["git", "clean", "-fd"],
            cwd=self.path_to_git_root,
            capture_output=False,
            text=True,
            check=True,
        )
        assert result.returncode == 0, result
