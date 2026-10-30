import re
import uuid
from pathlib import Path
from git import Repo

BASE_DIR = Path(__file__).resolve().parent.parent / "data"
BASE_DIR.mkdir(parents=True, exist_ok=True)


def clone_repository(repo_url: str):
    pattern = r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?(?:\.git)?"

    if not re.fullmatch(pattern, repo_url):
        raise ValueError("Please provide a valid public GitHub repository URL.")

    repo_id = str(uuid.uuid4())
    destination = BASE_DIR / repo_id

    Repo.clone_from(
        repo_url,
        str(destination),
        depth=1,
        single_branch=True
    )

    return repo_id, str(destination)