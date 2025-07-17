import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
from streamlit_conciliacao import utils  # noqa: E402
from streamlit_conciliacao import utils_git  # noqa: E402


def test_leitura_e_csv(tmp_path: Path) -> None:
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    excel_path = tmp_path / "dados.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    df_extrato = utils.read_extrato(excel_path)
    df_lanc = utils.read_lancamentos(excel_path)
    assert df_extrato.equals(df)
    assert df_lanc.equals(df)

    csv_path = tmp_path / "saida.csv"
    utils.to_csv_padronizado(df, csv_path)
    with csv_path.open("r", encoding="utf-8-sig") as fp:
        texto = fp.read()
    assert ";" in texto


def test_commit_json(monkeypatch):
    repo_mock = MagicMock()
    file_mock = MagicMock(path="p.json", sha="abc")

    github_instance = MagicMock()
    github_instance.get_repo.return_value = repo_mock

    with patch(
        "streamlit_conciliacao.utils_git.Github",
        return_value=github_instance,
    ) as gh_cls:
        repo_mock.get_contents.return_value = file_mock
        utils_git.commit_json("t", "org/repo", "p.json", {"x": 1}, "msg")
        repo_mock.update_file.assert_called_once()
        repo_mock.create_file.assert_not_called()

        repo_mock.update_file.reset_mock()
        repo_mock.create_file.reset_mock()
        repo_mock.get_contents.side_effect = Exception
        utils_git.commit_json("t", "org/repo", "p.json", {"x": 1}, "msg")
        repo_mock.create_file.assert_called_once()

    with patch("streamlit_conciliacao.utils_git.Github") as gh_cls:
        utils_git.commit_json("", "", "a.json", {}, "msg")
        gh_cls.assert_not_called()
