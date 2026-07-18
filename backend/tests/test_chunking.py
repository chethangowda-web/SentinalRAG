from app.services.chunking_service import TextChunk, chunk_text, split_into_paragraphs


def test_split_paragraphs():
    text = "Para one.\n\nPara two.\n\nPara three."
    result = split_into_paragraphs(text)
    assert len(result) == 3
    assert result[0] == "Para one."


def test_chunk_small_text():
    text = "Hello world. This is a small document."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0].word_count == len(text.split())
    assert chunks[0].chunk_index == 0


def test_chunk_large_text(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.CHUNK_SIZE", 10)
    monkeypatch.setattr("app.core.config.settings.CHUNK_OVERLAP", 3)

    words = ["word"] * 50
    text = " ".join(words)
    chunks = chunk_text(text)

    assert len(chunks) > 1
    for c in chunks:
        assert c.word_count <= 10


def test_chunk_tracks_char_range():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n\nFourth paragraph."
    chunks = chunk_text(text)
    assert len(chunks) >= 1
    for c in chunks:
        assert c.char_end > c.char_start
        assert c.text == text[c.char_start:c.char_end]


def test_chunk_has_overlap(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.CHUNK_SIZE", 8)
    monkeypatch.setattr("app.core.config.settings.CHUNK_OVERLAP", 3)

    paragraphs = [
        "one two three four five",
        "six seven eight nine ten",
        "eleven twelve thirteen fourteen fifteen",
        "sixteen seventeen eighteen nineteen twenty",
    ]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text)

    if len(chunks) > 1:
        overlap_words_chunk1 = set(chunks[0].text.split())
        overlap_words_chunk2 = set(chunks[1].text.split())
        common = overlap_words_chunk1 & overlap_words_chunk2
        assert len(common) > 0


def test_chunk_structure():
    text = "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z"
    chunks = chunk_text(text)
    assert len(chunks) == 1
    c = chunks[0]
    assert isinstance(c, TextChunk)
    assert c.chunk_index == 0
    assert c.char_start == 0
    assert c.char_end == len(text)
    assert c.word_count == 26
    assert c.page_number is None
