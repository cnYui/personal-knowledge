from app.services.graph_history_entity_resolver import GraphHistoryEntityResolver


def test_entity_resolver_returns_exact_match():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI', 'Open AI']})

    resolved = resolver.resolve('OpenAI')

    assert resolved.status == 'ok'
    assert resolved.canonical_name == 'OpenAI'
    assert resolved.matched_alias == 'OpenAI'


def test_entity_resolver_matches_canonical_name_without_alias_duplication():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['Open AI']})

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


def test_entity_resolver_normalizes_input_and_aliases_for_match():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['  Open AI  ' ]})

    resolved = resolver.resolve('  open ai  ')

    assert resolved.status == 'ok'
    assert resolved.canonical_name == 'OpenAI'
    assert resolved.matched_alias == '  Open AI  '


def test_entity_resolver_does_not_treat_duplicate_aliases_for_same_canonical_as_ambiguous():
    resolver = GraphHistoryEntityResolver(alias_map={'OpenAI': ['OpenAI', ' openai ' ]})

    resolved = resolver.resolve('OpenAI')

    assert resolved.status == 'ok'
    assert resolved.canonical_name == 'OpenAI'
    assert resolved.matched_alias == 'OpenAI'
    assert resolved.disambiguation_candidates == []


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
    assert resolved.matched_alias is None
    assert resolved.disambiguation_candidates == []
