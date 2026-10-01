"""Assistant-only labels with exact chat-prefix checks and no truncation."""


def assistant_labels(prefix, full, eos_token_id, max_tokens):
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError('max_tokens must be positive')
    if not prefix or full[:len(prefix)] != prefix:
        raise ValueError('Inference prefix differs from the training chat template')
    if len(full) <= len(prefix):
        raise ValueError('No assistant target tokens')
    if full[-1] != eos_token_id:
        raise ValueError('Assistant target is missing EOS')
    if len(full) > max_tokens:
        raise ValueError(f'Sequence has {len(full)} tokens, exceeds {max_tokens}; refusing truncation')
    return [-100] * len(prefix) + full[len(prefix):]


def tokenize_messages(messages, inference_tokenizer, training_tokenizer, max_tokens):
    if (not isinstance(messages, list) or len(messages) != 2
            or any(not isinstance(m, dict) for m in messages)
            or [m.get('role') for m in messages] != ['user', 'assistant']
            or any(not isinstance(m.get('content'), str) or not m['content'].strip() for m in messages)):
        raise ValueError('Expected one nonempty user message and one assistant target')
    prefix = inference_tokenizer.apply_chat_template(messages[:1], tokenize=True, return_dict=False)
    full = training_tokenizer.apply_chat_template(messages, tokenize=True, return_dict=False)
    labels = assistant_labels(prefix, full, training_tokenizer.eos_token_id, max_tokens)
    return {'input_ids': full, 'attention_mask': [1] * len(full), 'labels': labels,
            'prefix_tokens': len(prefix), 'supervised_tokens': len(full) - len(prefix)}
