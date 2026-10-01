from copy import deepcopy
from scripts.validate_training_data import validate,reserved_evaluation_sources


def sample():
    return {'schema':'paper-voice-understanding-v1','source_id':'new-one','family':'new-family','split':'train',
            'license':'MIT','rights_confirmed':True,'human_reviewed':True,'document':'費用：免費。',
            'fields':{'deadline':'','required_documents':'','amount':'免費。','conditions':''},
            'questions':[{'question':'有費用嗎？','answer':'免費。','found':True,'evidence':['費用：免費。']}]}


def test_reviewed_source_with_real_evidence_is_eligible():
    assert validate([sample()]) == []


def test_rejects_cross_split_family_and_duplicate_text():
    a=sample(); b=deepcopy(a); b.update(source_id='another',split='test')
    errors=validate([a,b])
    assert any('family appears' in error for error in errors)
    assert any('text appears' in error for error in errors)


def test_existing_evaluation_document_cannot_be_renamed_into_training():
    a=sample()
    assert any('evaluation document' in e for e in validate([a],reserved_texts=[a['document']]))


def test_draft_labels_and_invented_evidence_are_rejected():
    a=sample(); a['human_reviewed']=False; a['questions'][0]['evidence']=['須繳交100元。']
    errors=validate([a])
    assert any('human review' in e for e in errors)
    assert any('not present verbatim' in e for e in errors)


def test_public_development_source_is_not_allowed_into_training():
    ids,texts=reserved_evaluation_sources()
    assert 'wda-pretraining-115' in ids
    row=sample();row['source_id']='different-page';row['family']='wda-pretraining-115'
    assert any('evaluation document' in e for e in validate([row],ids,texts))


def test_semantic_checker_evaluation_cannot_be_renamed_into_training():
    ids,texts=reserved_evaluation_sources()
    assert 'answer-verification:utilities' in ids
    row=sample();row['document']='本次僅停止供電。供水照常。'
    assert any('evaluation document' in e for e in validate([row],ids,texts))


def test_existing_evaluation_family_cannot_enter_under_a_new_source_id():
    ids,texts=reserved_evaluation_sources()
    row=sample();row['family']='workshop-registration'
    assert any('evaluation document' in e for e in validate([row],ids,texts))


def test_whitespace_is_not_an_evidence_span_but_empty_missing_field_is_valid():
    row=sample();row['fields']['deadline']=' \n\t　'
    assert any('deadline must be empty' in e for e in validate([row]))
    row['fields']['deadline']=''
    assert validate([row]) == []
