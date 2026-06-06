from waterplan.search.query_builder import all_queries, build_queries, QUERY_TEMPLATES


def test_build_queries_returns_two():
    queries = build_queries("Mexicali, Mexico", "water_stress")
    assert len(queries) == 2
    for q in queries:
        assert "Mexicali" in q or "mexicali" in q.lower()


def test_all_queries_covers_all_dimensions():
    queries = all_queries("Chandler, Arizona, USA")
    assert set(queries.keys()) == {"water_stress", "incidents", "regulations"}
    for dim, qs in queries.items():
        assert len(qs) >= 2, f"{dim} should have at least 2 queries"


def test_queries_are_distinct():
    queries = build_queries("Monterrey, Mexico", "water_stress")
    assert queries[0] != queries[1], "Two queries should differ to hit different sources"


def test_location_interpolated():
    for dim in QUERY_TEMPLATES:
        queries = build_queries("Test City, XY", dim)
        for q in queries:
            assert "Test City" in q or "test city" in q.lower()
