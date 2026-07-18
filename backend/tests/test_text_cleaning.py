from app.services.text_cleaning import (
    clean_text,
    normalize_unicode,
    remove_extra_spaces,
    remove_page_numbers,
)


def test_normalize_unicode_compatibility():
    result = normalize_unicode("\uff36\uff45\uff4c\uff4c\uff4f")  # 全角 V e l l o
    assert "Vello" in result


def test_remove_extra_spaces():
    result = remove_extra_spaces("hello    world")
    assert result == "hello world"


def test_remove_page_numbers_numeric_only():
    text = "some text\n42\nmore text"
    result = remove_page_numbers(text)
    assert "42" not in result
    assert "some text" in result
    assert "more text" in result


def test_remove_page_numbers_page_keyword():
    text = "content\nPage 3\nmore"
    result = remove_page_numbers(text)
    assert "Page 3" not in result
    assert "content" in result


def test_remove_page_numbers_dashed():
    text = "content\n- 5 -\nmore"
    result = remove_page_numbers(text)
    assert "- 5 -" not in result
    assert "content" in result


def test_remove_page_numbers_fraction():
    text = "content\n3 / 5\nmore"
    result = remove_page_numbers(text)
    assert "3 / 5" not in result


def test_clean_text_preserves_content():
    text = "The quick brown fox jumps over the lazy dog."
    result = clean_text(text)
    assert result == text
