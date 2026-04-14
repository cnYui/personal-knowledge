from app.services.graph_history_entity_resolver import GraphHistoryEntityResolver


def test_entity_resolver_returns_exact_match():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI', 'Open AI']})

    resolved = resolver.resolve('OpenAI')

    assert resolved.status == 'ok'
    assert resolved.canonical_name == 'OpenAI'
    assert resolved.matched_alias == 'OpenAI'


def test_entity_resolver_returns_alias_match():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI', 'Open AI']})

    resolved = resolver.resolve('Open AI')

    assert resolved.status == 'ok'
    assert resolved.canonical_name == 'OpenAI'
    assert resolved.matched_alias == 'Open AI'


def test_entity_resolver_returns_ambiguous_target():
    resolver = GraphHistoryEntityResolver(alias_map={'Apple Inc.': ['Apple'], 'Apple Fruit': ['Apple']})

    resolved = resolver.resolve('Apple')

    assert resolved.status == 'ambiguous_target'
    assert len(resolved.disambiguation_candidates) == 2


def test_entity_resolver_returns_not_found():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['Open AI']})

    resolved = resolver.resolve('Anthropic')

    assert resolved.status == 'not_found'
    assert resolved.canonical_name is None
