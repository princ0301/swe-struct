import shutil
import subprocess
from pathlib import Path

class GitError(RuntimeError):
    pass

def run_git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout

class RepoCache:
    def __init__(self, cache_dir: Path, url_template: str = "https://github.com/{repo}.git") -> None:
        self.cache_dir = cache_dir
        self.url_template = url_template

    def mirror_path(self, repo: str) -> Path:
        return self.cache_dir / "mirrors" / repo.replace("/", "__")

    def ensure_mirror(self, repo: str) -> Path:
        mirror = self.mirror_path(repo)
        if mirror.exists():
            return mirror
        url = self.url_template.format(repo=repo)
        mirror.parent.mkdir(parents=True, exist_ok=True)
        options = ["--filter=blob:none"] if url.startswith("http") else []
        run_git("clone", "--no-checkout", *options, url, str(mirror))
        return mirror

    def add_worktree(self, mirror: Path, target: Path, commit: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            run_git("worktree", "add", "--detach", str(target), commit, cwd=mirror)
        except GitError:
            run_git("fetch", "origin", commit, cwd=mirror)
            run_git("worktree", "add", "--detach", str(target), commit, cwd=mirror)

    def checkout(self, repo: str, commit: str, destination: Path) -> Path:
        mirror = self.ensure_mirror(repo)
        target = destination.resolve()
        self.add_worktree(mirror, target, commit)
        return target

    def checkout_shared(self, repo: str, commit: str) -> Path:
        mirror = self.ensure_mirror(repo)
        shared = (self.cache_dir / "shared" / repo.replace("/", "__")).resolve()
        if not shared.exists():
            self.add_worktree(mirror, shared, commit)
            return shared
        try:
            run_git("checkout", "--force", "--detach", commit, cwd=shared)
        except GitError:
            try:
                run_git("fetch", "origin", commit, cwd=mirror)
                run_git("checkout", "--force", "--detach", commit, cwd=shared)
            except GitError:
                shutil.rmtree(shared, ignore_errors=True)
                run_git("worktree", "prune", cwd=mirror)
                self.add_worktree(mirror, shared, commit)
        return shared

    def remove(self, repo: str, destination: Path) -> None:
        mirror = self.mirror_path(repo)
        target = destination.resolve()
        try:
            run_git("worktree", "remove", "--force", str(target), cwd=mirror)
        except GitError:
            pass
        shutil.rmtree(target, ignore_errors=True)
        try:
            run_git("worktree", "prune", cwd=mirror)
        except GitError:
            pass

def current_git_sha(cwd: Path | None = None) -> str:
    sha = run_git("rev-parse", "HEAD", cwd=cwd).strip()
    dirty = run_git("status", "--porcelain", cwd=cwd).strip()
    return f"{sha}-dirty" if dirty else sha