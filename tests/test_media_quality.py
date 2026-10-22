import pytest

from brainrot import render
from brainrot.domain.jobs import PermanentError


@pytest.mark.parametrize("words", [
    [{"start": 0, "end": 121}],
    [{"start": -1, "end": 1}],
    [{"start": 1, "end": 1}],
    [{"start": 2, "end": 3}, {"start": 1, "end": 2}],
    [{"start": 0, "end": 1}, {"start": 0, "end": 2}],
    [{"start": 0, "end": float("nan")}],
])
def test_invalid_caption_timing_cannot_reach_render(words):
    with pytest.raises(PermanentError, match="captions"):
        render.check_captions(words, 120)


def test_caption_overlap_clears_the_previous_word_at_the_next_start():
    words = [{"text": "First", "start": 0, "end": 1.1}, {"text": "Second", "start": 1, "end": 2}]
    render.check_captions(words, 120)
    captions = render.build_captions(words)
    assert "0:00:00.00,0:00:01.00" in captions
    assert "0:00:00.00,0:00:01.10" not in captions
