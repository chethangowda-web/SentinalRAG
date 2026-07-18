from pathlib import Path

from app.utils.file_utils import generate_document_id, get_processed_path


def test_generate_document_id():
    doc_id = generate_document_id()
    assert isinstance(doc_id, str)
    assert len(doc_id) == 36
    assert "-" in doc_id


def test_get_processed_path(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.config.settings.PROCESSED_DIR", tmp_path)
    path = get_processed_path("test-id-123")
    assert isinstance(path, Path)
    assert path.name == "test-id-123.txt"
    assert path.parent == tmp_path
    assert tmp_path.exists()
