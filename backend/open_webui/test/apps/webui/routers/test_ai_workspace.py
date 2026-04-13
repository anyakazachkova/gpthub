from open_webui.routers.ai_workspace import WorkspaceFile, _classify_task, _score_model


def test_classify_audio_file_as_audio_workflow():
    task = _classify_task(
        'Please transcribe this meeting and highlight action items',
        [WorkspaceFile(type='audio', content_type='audio/mpeg', name='meeting.mp3')],
    )

    assert task['task'] == 'audio_workflow'
    assert task['confidence'] == 'high'
    assert task['input_sources'] == ['audio', 'text']
    assert task['workflow'][0] == 'Transcribe audio'


def test_classify_url_research_as_deep_research():
    task = _classify_task(
        'Сделай deep research по рынку ИИ-ассистентов и сравни это с https://example.com/report',
        [],
    )

    assert task['task'] == 'deep_research'
    assert task['features']['web_search'] is True
    assert 'web_search' in task['required_capabilities']
    assert 'link' in task['input_sources']


def test_classify_attached_document_as_file_analysis():
    task = _classify_task(
        'Сделай выводы по этому файлу',
        [WorkspaceFile(type='file', content_type='application/pdf', name='report.pdf')],
    )

    assert task['task'] == 'file_analysis'
    assert task['confidence'] == 'high'
    assert 'file' in task['input_sources']


def test_score_model_prefers_vision_capable_model_for_image_analysis():
    task = _classify_task('Describe this screenshot', [WorkspaceFile(type='image', content_type='image/png')])

    vision_score, vision_caps = _score_model(
        {
            'id': 'vision-model',
            'name': 'GPT-4o Vision',
            'info': {'meta': {'capabilities': {'vision': True}}},
        },
        task,
        [],
    )
    text_score, text_caps = _score_model(
        {
            'id': 'text-model',
            'name': 'Plain Text Model',
            'info': {'meta': {'capabilities': {'vision': False}}},
        },
        task,
        [],
    )

    assert vision_score > text_score
    assert 'vision' in vision_caps
    assert 'vision' not in text_caps


def test_score_model_prefers_web_search_for_deep_research():
    task = _classify_task('Need a deep research brief on current AI browser agents', [])

    web_score, web_caps = _score_model(
        {
            'id': 'research-model',
            'name': 'GPT-5 Pro Research',
            'info': {'meta': {'capabilities': {'web_search': True, 'file_context': True}}},
        },
        task,
        [],
    )
    baseline_score, baseline_caps = _score_model(
        {
            'id': 'baseline-model',
            'name': 'Local Chat Model',
            'info': {'meta': {'capabilities': {'web_search': False, 'file_context': False}}},
        },
        task,
        [],
    )

    assert web_score > baseline_score
    assert 'web_search' in web_caps
    assert baseline_caps == []
