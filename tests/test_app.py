import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit_conciliacao import app  # noqa: E402


def test_listar_empresas(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cnpj_dir = data_dir / "12345678901234"
    cnpj_dir.mkdir()
    cfg = cnpj_dir / "contas_config.json"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(app, "DATA_DIR", data_dir)
    empresas = app._listar_empresas()
    assert empresas == {"12345678901234": cfg}
