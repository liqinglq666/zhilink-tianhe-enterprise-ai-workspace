from backend.knowledge_routes import _normalized_search_payload
from backend.knowledge_schemas import KnowledgeSearchRequest


def test_search_scope_normalization_does_not_treat_scale_as_entity_type():
    payload = KnowledgeSearchRequest.model_validate(
        {
            "query": "数字化诊断",
            "profile": {
                "industry": "商贸服务",
                "location": "广州市天河区",
                "scale": "20 人团队",
                "stage": "",
                "demands": "",
            },
            "category": "",
            "limit": 8,
        }
    )
    normalized = _normalized_search_payload(payload)
    assert normalized.profile.location == "广州市天河"
    assert normalized.profile.scale == ""
    assert normalized.profile.industry == "商贸服务"
