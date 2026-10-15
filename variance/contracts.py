"""Version-one structured specialist contracts and completion validation."""
from typing import TypedDict

from .domain import Invalid


class ResearchResult(TypedDict):
    score: int
    rationale: str
    confidence: str
    source: str
    completed_at: str
    contract: int


class CreativeBrief(TypedDict):
    concept: str
    audience: str
    direction: str
    constraints: str
    adapter: str
    version: int
    prompt: str


class PlatformPackage(TypedDict):
    caption: str
    alt: str
    limit: int


class MetricSnapshot(TypedDict):
    platform: str
    impressions: int
    likes: int
    comments: int
    shares: int
    saves: int
    period: str
    provenance: str
    recorded_at: str
    comment_notes: str


def validate_result(kind: str, document: dict) -> None:
    """Validate before committing. Future model adapters must pass the same boundary."""
    if kind == 'research':
        result = document.get('research', {})
        if type(result.get('score')) is not int or not 0 <= result['score'] <= 100 or result.get('contract') != 1:
            raise Invalid('Research result does not satisfy contract v1.')
        required = ('rationale', 'confidence', 'source', 'completed_at')
    elif kind == 'creative':
        result = document.get('brief', {})
        if type(result.get('version')) is not int or result['version'] < 1:
            raise Invalid('Brief version is invalid.')
        required = ('concept', 'audience', 'direction', 'constraints', 'adapter', 'prompt')
    elif kind == 'package':
        packages = document.get('packages', {})
        if set(packages) != {'instagram', 'facebook', 'x'}:
            raise Invalid('All three platform packages are required.')
        for p, maximum in (('instagram', 2200), ('facebook', 5000), ('x', 280)):
            item = packages[p]
            if not isinstance(item, dict) or not isinstance(item.get('caption'), str) or not 0 < len(item['caption']) <= maximum or not isinstance(item.get('alt'), str) or not 0 < len(item['alt']) <= 1000:
                raise Invalid('Platform package does not satisfy contract v1.')
        return
    elif kind == 'analyze':
        result = document.get('analysis', {})
        if not isinstance(result.get('rows'), list) or not result['rows'] or not isinstance(result.get('recommendations'), list) or not all(isinstance(r, str) for r in result['recommendations']):
            raise Invalid('Analysis result does not satisfy contract v1.')
        required = ('limitations', 'completed_at')
    else:
        raise Invalid('Unknown specialist contract.')
    if any(not isinstance(result.get(k), str) or not result[k].strip() or len(result[k]) > 20000 for k in required):
        raise Invalid('Specialist output has invalid text fields.')
