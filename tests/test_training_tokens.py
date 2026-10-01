import pytest
from scripts.training_tokens import assistant_labels, tokenize_messages


def test_user_prefix_is_ignored_while_answer_and_eos_are_supervised():
    assert assistant_labels([1, 10, 11], [1, 10, 11, 20, 21, 2], 2, 6) == [-100, -100, -100, 20, 21, 2]


@pytest.mark.parametrize('prefix,full,eos,limit,reason', [
    ([1,10], [1,12,20,2], 2, 8, 'prefix differs'),
    ([1,10], [1,10], 2, 8, 'No assistant'),
    ([1,10], [1,10,20], 2, 8, 'missing EOS'),
    ([1,10], [1,10,20,2], 2, 3, 'refusing truncation'),
    ([], [1,20,2], 2, 8, 'prefix differs'),
])
def test_invalid_boundaries_and_overflow_fail_instead_of_training_wrong_tokens(prefix,full,eos,limit,reason):
    with pytest.raises(ValueError,match=reason):
        assistant_labels(prefix,full,eos,limit)


def test_multiturn_is_rejected_before_tokenizer_is_called():
    with pytest.raises(ValueError,match='one nonempty user'):
        tokenize_messages([{'role':'assistant','content':'wrong order'}],None,None,512)
