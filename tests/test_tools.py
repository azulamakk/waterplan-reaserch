from waterplan.models.schemas import Source, ValidationStatus
from waterplan.agent.tools import make_tools


def test_record_finding_accumulates():
    findings = {"water_stress": [], "incidents": [], "regulations": []}
    tools = make_tools(findings, use_cache=False)
    record_finding = next(t for t in tools if t.name == "record_finding")

    result = record_finding.invoke({
        "dimension": "water_stress",
        "url": "https://example.com",
        "title": "Test Source",
        "excerpt": "Test excerpt text",
        "summary": "Test finding",
        "validation_status": "MATCH_FOUND",
    })

    assert len(findings["water_stress"]) == 1
    assert findings["water_stress"][0].validation_status == ValidationStatus.MATCH
    assert "1" in result


def test_finish_research_requires_two_sources():
    findings = {"water_stress": [], "incidents": [], "regulations": []}
    tools = make_tools(findings, use_cache=False)
    finish = next(t for t in tools if t.name == "finish_research")

    result = finish.invoke({
        "water_stress_summary": "test",
        "incidents_summary": "test",
        "regulations_summary": "test",
        "overall_confidence": 0.8,
    })

    assert "NOT READY" in result


def test_finish_research_succeeds_with_enough_sources():
    findings = {"water_stress": [], "incidents": [], "regulations": []}
    tools = make_tools(findings, use_cache=False)
    record = next(t for t in tools if t.name == "record_finding")
    finish = next(t for t in tools if t.name == "finish_research")

    for dim in ["water_stress", "incidents", "regulations"]:
        for i in range(2):
            record.invoke({
                "dimension": dim,
                "url": f"https://example.com/{dim}/{i}",
                "title": f"Source {i}",
                "excerpt": f"Excerpt for {dim} source {i}",
                "summary": f"Summary {i}",
                "validation_status": "MATCH_FOUND",
            })

    result = finish.invoke({
        "water_stress_summary": "Water stress summary",
        "incidents_summary": "Incidents summary",
        "regulations_summary": "Regulations summary",
        "overall_confidence": 0.85,
    })

    assert "NOT READY" not in result
    assert "__summaries__" in findings


def test_invalid_dimension_rejected():
    findings = {}
    tools = make_tools(findings, use_cache=False)
    record = next(t for t in tools if t.name == "record_finding")

    result = record.invoke({
        "dimension": "invalid_dim",
        "url": "https://example.com",
        "title": "Test",
        "excerpt": "Test",
        "summary": "Test",
        "validation_status": "MATCH_FOUND",
    })

    assert "ERROR" in result
