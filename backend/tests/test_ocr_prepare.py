import pytest
from PIL import Image

from app.core.exceptions import InvalidUploadError
from app.services import ocr_service
from app.services.ocr_service import MAX_OCR_SIDE, prepare_for_ocr


def test_large_image_is_shrunk_to_the_longest_side_limit_and_grayscaled():
    result = prepare_for_ocr(Image.new("RGBA", (6000, 4000), (255, 255, 255, 255)))
    assert max(result.size) == MAX_OCR_SIDE
    assert result.size == (2500, 1666)  # aspect ratio kept (rounded down)
    assert result.mode == "L"


def test_tall_image_is_limited_by_its_height():
    result = prepare_for_ocr(Image.new("RGB", (1000, 5000)))
    assert result.size == (500, MAX_OCR_SIDE)


def test_small_image_keeps_its_size():
    result = prepare_for_ocr(Image.new("RGB", (800, 600)))
    assert result.size == (800, 600)
    assert result.mode == "L"


def test_absurdly_large_image_is_rejected_before_it_is_decoded(monkeypatch):
    monkeypatch.setattr(ocr_service, "MAX_IMAGE_PIXELS", 1_000_000)
    with pytest.raises(InvalidUploadError) as exc:
        prepare_for_ocr(Image.new("RGB", (2000, 1000)))
    assert "too large" in exc.value.detail


def test_extreme_aspect_ratio_never_collapses_to_zero_pixels():
    result = prepare_for_ocr(Image.new("L", (40000, 1)))
    assert min(result.size) >= 1
