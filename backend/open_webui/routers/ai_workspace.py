import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from open_webui.utils.auth import get_verified_user
from open_webui.utils.models import get_all_models, get_filtered_models


router = APIRouter()

URL_PATTERN = re.compile(r'https?://\S+', re.IGNORECASE)

IMAGE_ANALYSIS_KEYWORDS = (
    'image',
    'photo',
    'picture',
    'screenshot',
    'diagram',
    'chart',
    'scan',
    'analyze image',
    'describe image',
    'look at this image',
    'изображ',
    'картин',
    'фото',
    'скриншот',
    'диаграм',
    'схем',
    'распознай',
)
IMAGE_GENERATION_KEYWORDS = (
    'generate image',
    'create image',
    'draw',
    'illustration',
    'render',
    'poster',
    'logo',
    'banner',
    'mockup',
    'сгенерир',
    'создай изображ',
    'нарисуй',
    'иллюстрац',
    'баннер',
    'логотип',
    'постер',
)
IMAGE_EDITING_KEYWORDS = (
    'edit image',
    'edit photo',
    'modify image',
    'remove background',
    'retouch',
    'upscale',
    'отредактир',
    'измени изображ',
    'убери фон',
    'улучши фото',
)
AUDIO_KEYWORDS = (
    'audio',
    'voice',
    'recording',
    'transcribe',
    'transcript',
    'podcast',
    'meeting recording',
    'speech to text',
    'аудио',
    'голос',
    'запись',
    'транскриб',
    'расшифр',
    'подкаст',
)
FILE_KEYWORDS = (
    'pdf',
    'docx',
    'xlsx',
    'spreadsheet',
    'presentation',
    'file',
    'document',
    'table',
    'report',
    'файл',
    'документ',
    'таблиц',
    'презентац',
    'отчет',
)
WEB_SEARCH_KEYWORDS = (
    'search the web',
    'search web',
    'internet search',
    'latest',
    'today',
    'current',
    'news',
    'research',
    'find online',
    'в интернете',
    'в сети',
    'найди',
    'поищи',
    'актуаль',
    'свеж',
    'новост',
    'последн',
)
LINK_PARSING_KEYWORDS = (
    'summarize this link',
    'summarize url',
    'parse link',
    'extract from url',
    'scrape',
    'read this page',
    'прочитай ссыл',
    'суммируй ссыл',
    'спарси',
    'извлеки',
    'проанализируй ссыл',
)
MEMORY_KEYWORDS = ('remember', 'save this', 'запомни', 'сохрани это')


class WorkspaceFile(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    content_type: Optional[str] = None
    name: Optional[str] = None


class WorkspaceRouteRequest(BaseModel):
    prompt: str = ''
    files: list[WorkspaceFile] = Field(default_factory=list)
    selected_model_ids: list[str] = Field(default_factory=list)
    current_features: dict[str, bool] = Field(default_factory=dict)


class WorkspaceRouteCandidate(BaseModel):
    id: str
    name: str
    score: int
    matched_capabilities: list[str] = Field(default_factory=list)


class WorkspaceRouteResponse(BaseModel):
    mode: Literal['auto'] = 'auto'
    task: str
    task_label: str
    selected_model_id: Optional[str] = None
    selected_model_name: Optional[str] = None
    required_capabilities: list[str] = Field(default_factory=list)
    features: dict[str, bool] = Field(default_factory=dict)
    memory_recommended: bool = False
    reasons: list[str] = Field(default_factory=list)
    summary: str
    candidate_models: list[WorkspaceRouteCandidate] = Field(default_factory=list)


def _contains_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _capability(model: dict, name: str, default: bool = True) -> bool:
    return (model.get('info', {}).get('meta', {}).get('capabilities') or {}).get(name, default)


def _feature_available(request: Request, user, feature_name: str) -> bool:
    feature_to_config = {
        'web_search': 'ENABLE_WEB_SEARCH',
        'image_generation': 'ENABLE_IMAGE_GENERATION',
        'memory': 'ENABLE_MEMORIES',
    }

    config_flag = feature_to_config.get(feature_name)
    if not config_flag:
        return False

    if not getattr(request.app.state.config, config_flag, False):
        return False

    permissions = getattr(user, 'permissions', {}) or {}
    features = permissions.get('features', {}) if isinstance(permissions, dict) else {}
    return user.role == 'admin' or features.get(feature_name, True)


def _classify_task(prompt: str, files: list[WorkspaceFile]) -> dict:
    normalized_prompt = prompt.lower().strip()
    has_url = bool(URL_PATTERN.search(prompt))

    image_files = [
        file
        for file in files
        if file.type == 'image' or (file.content_type or '').startswith('image/')
    ]
    audio_files = [
        file
        for file in files
        if file.type == 'audio' or (file.content_type or '').startswith('audio/')
    ]
    doc_files = [
        file
        for file in files
        if file.type not in {'image', 'audio'}
        and not (file.content_type or '').startswith('image/')
        and not (file.content_type or '').startswith('audio/')
    ]

    wants_image_generation = _contains_keyword(normalized_prompt, IMAGE_GENERATION_KEYWORDS)
    wants_image_editing = _contains_keyword(normalized_prompt, IMAGE_EDITING_KEYWORDS)
    wants_image_analysis = _contains_keyword(normalized_prompt, IMAGE_ANALYSIS_KEYWORDS)
    wants_audio = _contains_keyword(normalized_prompt, AUDIO_KEYWORDS)
    wants_file_analysis = _contains_keyword(normalized_prompt, FILE_KEYWORDS)
    wants_web_search = _contains_keyword(normalized_prompt, WEB_SEARCH_KEYWORDS)
    wants_link_parsing = has_url and _contains_keyword(normalized_prompt, LINK_PARSING_KEYWORDS)
    wants_memory = _contains_keyword(normalized_prompt, MEMORY_KEYWORDS)

    if audio_files or wants_audio:
        return {
            'task': 'audio_workflow',
            'task_label': 'Audio workflow',
            'required_capabilities': [],
            'features': {},
            'reasons': ['Detected audio input or a transcription-style request.'],
            'memory_recommended': wants_memory,
        }

    if image_files and wants_image_editing:
        return {
            'task': 'image_editing',
            'task_label': 'Image editing',
            'required_capabilities': ['vision'],
            'features': {'image_generation': True},
            'reasons': ['Detected an image-editing request with an attached image.'],
            'memory_recommended': wants_memory,
        }

    if image_files or wants_image_analysis:
        return {
            'task': 'image_analysis',
            'task_label': 'Image analysis',
            'required_capabilities': ['vision'],
            'features': {},
            'reasons': ['Detected visual input that should be routed to a vision-capable model.'],
            'memory_recommended': wants_memory,
        }

    if wants_image_generation:
        return {
            'task': 'image_generation',
            'task_label': 'Image generation',
            'required_capabilities': [],
            'features': {'image_generation': True},
            'reasons': ['Detected an illustration or image-generation request.'],
            'memory_recommended': wants_memory,
        }

    if doc_files or wants_file_analysis:
        return {
            'task': 'file_analysis',
            'task_label': 'File analysis',
            'required_capabilities': ['file_context'],
            'features': {},
            'reasons': ['Detected attached documents or a document-analysis request.'],
            'memory_recommended': wants_memory,
        }

    if wants_link_parsing:
        return {
            'task': 'link_parsing',
            'task_label': 'Link parsing',
            'required_capabilities': [],
            'features': {},
            'reasons': ['Detected a direct URL parsing or page-reading request.'],
            'memory_recommended': wants_memory,
        }

    if wants_web_search:
        return {
            'task': 'web_research',
            'task_label': 'Web research',
            'required_capabilities': ['web_search'],
            'features': {'web_search': True},
            'reasons': ['Detected a request that benefits from current web information.'],
            'memory_recommended': wants_memory,
        }

    return {
        'task': 'general_chat',
        'task_label': 'General chat',
        'required_capabilities': [],
        'features': {},
        'reasons': ['Using the general-purpose text workflow.'],
        'memory_recommended': wants_memory,
    }


def _score_model(model: dict, task: dict, preferred_ids: list[str]) -> tuple[int, list[str]]:
    model_id = model.get('id', '')
    model_name = (model.get('name') or model_id).lower()
    matched_capabilities = []
    score = 0

    for capability in task['required_capabilities']:
        if _capability(model, capability, True):
            matched_capabilities.append(capability)
            score += 80
        else:
            score -= 200

    if task['task'] == 'image_analysis' and any(
        hint in model_name for hint in ('vision', 'vl', 'llava', 'pixtral', '4o', 'gemini', 'claude')
    ):
        score += 35

    if task['task'] in {'general_chat', 'web_research', 'file_analysis'} and any(
        hint in model_name
        for hint in ('gpt-5', 'o3', 'claude', 'gemini', 'qwen', 'llama', 'deepseek', 'sonnet', 'pro')
    ):
        score += 20

    if task['task'] == 'web_research' and _capability(model, 'web_search', True):
        matched_capabilities.append('web_search')
        score += 40

    if task['task'] == 'file_analysis' and _capability(model, 'file_context', True):
        matched_capabilities.append('file_context')
        score += 30

    if model_id in preferred_ids:
        score += 25

    if any(token in model_name for token in ('mini', 'flash')):
        score -= 5

    return score, sorted(set(matched_capabilities))


@router.post('/route', response_model=WorkspaceRouteResponse)
async def route_request(
    request: Request,
    form_data: WorkspaceRouteRequest,
    user=Depends(get_verified_user),
):
    task = _classify_task(form_data.prompt, form_data.files)

    available_models = get_filtered_models(await get_all_models(request, user=user), user)
    scored_models = []
    for model in available_models:
        score, matched_capabilities = _score_model(model, task, form_data.selected_model_ids)
        scored_models.append(
            {
                'id': model.get('id'),
                'name': model.get('name') or model.get('id'),
                'score': score,
                'matched_capabilities': matched_capabilities,
            }
        )

    scored_models.sort(key=lambda item: item['score'], reverse=True)
    best_model = scored_models[0] if scored_models else None

    if best_model and best_model['score'] >= 0:
        selected_model_id = best_model['id']
        selected_model_name = best_model['name']
    else:
        selected_model_id = form_data.selected_model_ids[0] if form_data.selected_model_ids else None
        selected_model_name = selected_model_id

    features = {}
    for feature_name, enabled in task['features'].items():
        features[feature_name] = bool(enabled and _feature_available(request, user, feature_name))

    if form_data.current_features.get('memory', False) and _feature_available(request, user, 'memory'):
        features['memory'] = True

    reasons = list(task['reasons'])
    if task['memory_recommended'] and not form_data.current_features.get('memory', False):
        reasons.append('The prompt suggests persistent context would be useful; memories can stay enabled for continuity.')

    if best_model and best_model['score'] >= 0 and task['required_capabilities']:
        reasons.append(
            f"Selected {best_model['name']} because it best matched: {', '.join(best_model['matched_capabilities'])}."
        )
    elif selected_model_name:
        reasons.append(f'Selected {selected_model_name} as the best available default for this request.')

    if features.get('web_search'):
        reasons.append('Web search was enabled for this turn.')

    if features.get('image_generation'):
        reasons.append('Image generation was enabled for this turn.')

    summary_parts = [task['task_label']]
    if selected_model_name:
        summary_parts.append(selected_model_name)

    return WorkspaceRouteResponse(
        task=task['task'],
        task_label=task['task_label'],
        selected_model_id=selected_model_id,
        selected_model_name=selected_model_name,
        required_capabilities=task['required_capabilities'],
        features=features,
        memory_recommended=task['memory_recommended'],
        reasons=reasons,
        summary=' -> '.join(summary_parts),
        candidate_models=[WorkspaceRouteCandidate(**candidate) for candidate in scored_models[:3]],
    )
