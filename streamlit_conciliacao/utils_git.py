"""Funções de integração com o GitHub."""

from __future__ import annotations

import json
from typing import Any

from github import Github


def commit_json(token: str, repo: str, rel_path: str, data: dict, msg: str) -> None:
    """Cria ou atualiza arquivo JSON em um repositório GitHub.

    A função só executa quando ``token`` e ``repo`` são informados.
    """
    if not token or not repo:
        return

    gh = Github(token)
    repository = gh.get_repo(repo)

    content = json.dumps(data, indent=2, ensure_ascii=False)
    try:
        existing = repository.get_contents(rel_path)
        repository.update_file(existing.path, msg, content, existing.sha)
    except Exception:
        repository.create_file(rel_path, msg, content)

