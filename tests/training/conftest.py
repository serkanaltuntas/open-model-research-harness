from pathlib import Path

import pytest

from harness.training.data import read_jsonl

FIXTURES = Path(__file__).parent / "fixtures/valid.jsonl"


@pytest.fixture
def example():
    return read_jsonl(FIXTURES)[0]


@pytest.fixture
def eval_rows():
    return [
        {
            "id": "held-out",
            "prompt": "This reserved diagnostic question must never appear in any training message.",
        }
    ]


class FakeTokenizer:
    """Character tokenizer with atomic EOS, deliberately independent of BPE."""

    eos_token = "<|im_end|>"
    eos_token_id = 151645
    pad_token_id = 151643
    all_special_tokens = ("<|im_start|>", "<|im_end|>", "<|endoftext|>")

    def apply_chat_template(
        self, messages, *, tokenize, add_generation_prompt, enable_thinking
    ):
        assert tokenize is False and enable_thinking is True
        prefix = f"<|im_start|>user\n{messages[0]['content']}<|im_end|>\n<|im_start|>assistant\n"
        if add_generation_prompt:
            return prefix
        return (
            prefix
            + "<think>\n\n</think>\n\n"
            + messages[1]["content"].lstrip("\n")
            + "<|im_end|>\n"
        )

    def encode(self, text, *, add_special_tokens):
        assert add_special_tokens is False
        parts = text.split(self.eos_token)
        result = []
        for index, part in enumerate(parts):
            if index:
                result.append(self.eos_token_id)
            result.extend(ord(char) + 256 for char in part)
        return result

    def decode(
        self, ids, *, skip_special_tokens=False, clean_up_tokenization_spaces=False
    ):
        return "".join(
            self.eos_token if token == self.eos_token_id else chr(token - 256)
            for token in ids
        )


@pytest.fixture
def tokenizer():
    return FakeTokenizer()
