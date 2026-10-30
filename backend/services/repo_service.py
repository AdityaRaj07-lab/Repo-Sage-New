import os
import re
import uuid
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any

GITHUB_URL_REGEX = re.compile(r"^https?://github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+?)(?:\.git)?/?$")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REPOS_DATA_DIR = PROJECT_ROOT / "repos_data"

def validate_github_url(url: str) -> Tuple[bool, str, str]:
    """
    Validates if a URL is a valid GitHub repository URL.
    Returns (is_valid, owner, repo_name)
    """
    cleaned = url.strip()
    match = GITHUB_URL_REGEX.match(cleaned)
    if match:
        owner, repo = match.group(1), match.group(2)
        # Strip any trailing .git
        if repo.endswith(".git"):
            repo = repo[:-4]
        return True, owner, repo
    return False, "", ""

def clone_repository(url: str, branch: str = None) -> Tuple[str, str, str, str]:
    """
    Clones a GitHub repository or prepares a local repository.
    Returns: (repo_id, repo_name, owner, local_path)
    """
    REPOS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if local path was provided for offline/demo usage
    local_path_candidate = Path(url.strip())
    if local_path_candidate.exists() and local_path_candidate.is_dir():
        repo_name = local_path_candidate.name or "local_repo"
        owner = "local"
        repo_id = f"repo_{uuid.uuid4().hex[:8]}"
        target_dir = REPOS_DATA_DIR / repo_id
        
        # Copy supported files to isolated repos_data directory
        shutil.copytree(
            local_path_candidate,
            target_dir,
            ignore=shutil.ignore_patterns(".git", "venv", "__pycache__", "repos_data", "chroma_data", "*.db", "node_modules")
        )
        return repo_id, repo_name, owner, str(target_dir)

    # Otherwise validate as GitHub URL
    is_valid, owner, repo_name = validate_github_url(url)
    if not is_valid:
        raise ValueError(
            f"Invalid GitHub repository URL: '{url}'. "
            f"Expected format: https://github.com/owner/repository"
        )

    repo_id = f"repo_{uuid.uuid4().hex[:8]}"
    target_dir = REPOS_DATA_DIR / repo_id

    clone_cmd = ["git", "clone", "--depth", "1"]
    if branch:
        clone_cmd.extend(["--branch", branch])
    clone_cmd.extend([url.strip(), str(target_dir)])

    try:
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False
        )
        if result.returncode != 0:
            err = result.stderr or result.stdout or "Unknown git error"
            raise RuntimeError(f"Git clone failed: {err.strip()}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Git clone timed out after 120 seconds. Check network connectivity.")
    except Exception as e:
        raise RuntimeError(f"Failed to clone repository: {str(e)}")

    return repo_id, repo_name, owner, str(target_dir)
