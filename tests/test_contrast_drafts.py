"""New contrast siblings stay train-only and cannot bypass human review."""
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import pytest
from scripts.prepare_training_messages import prepare
from scripts.validate_training_data import validate, reserved_evaluation_sources

ROOT=Path(__file__).resolve().parents[1]


def drafts():
    return json.loads((ROOT/'static/training-review-contrast.json').read_text(encoding='utf-8'))['rows']


def test_contrast_questions_require_document_specific_answers_and_grounded_fields():
    rows=drafts();pairs=defaultdict(list)
    assert len(rows)==6 and sum(len(r['questions']) for r in rows)==18
    for row in rows:
        pairs[row['family']].append(row)
        assert row['split']=='train' and not row['human_reviewed'] and not row['rights_confirmed']
    assert len(pairs)==3
    for pair in pairs.values():
        assert len(pair)==2
        a,b=pair
        assert a['questions'][0]['question']==b['questions'][0]['question']
        assert a['questions'][0]['found'] and not b['questions'][0]['found']
        assert b['questions'][0]['evidence']==[]
        assert a['document']!=b['document']
        assert all(a['fields'][k]==b['fields'][k] for k in ('deadline','required_documents','amount'))
    errors=validate(rows,*reserved_evaluation_sources())
    assert len(errors)==6 and all(e.endswith('rights and human review must be explicitly confirmed') for e in errors)
    with pytest.raises(ValueError,match='human review'):
        prepare(rows)


def test_pair_siblings_cannot_be_split_into_training_and_evaluation():
    rows=deepcopy(drafts());rows[1]['split']='dev'
    assert any('family appears in more than one split' in error for error in validate(rows))


def test_original_review_sources_are_not_reused():
    original=json.loads((ROOT/'static/training-review-drafts.json').read_text(encoding='utf-8'))['rows']
    for key in ('source_id','family','document'):
        assert not {r[key] for r in drafts()} & {r[key] for r in original}
