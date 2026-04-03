from app.core.env_store import EnvStore


def test_env_store_updates_existing_keys_and_appends_missing_ones(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        '# Example env\n'
        'DIALOG_API_KEY=old-dialog\n'
        '\n'
        'DIALOG_MODEL=deepseek-chat\n',
        encoding='utf-8',
    )

    EnvStore(env_path).update(
        {
            'DIALOG_API_KEY': 'new-dialog',
            'KNOWLEDGE_BUILD_API_KEY': 'new-build',
        }
    )

    assert env_path.read_text(encoding='utf-8') == (
        '# Example env\n'
        'DIALOG_API_KEY=new-dialog\n'
        '\n'
        'DIALOG_MODEL=deepseek-chat\n'
        '\n'
        'KNOWLEDGE_BUILD_API_KEY=new-build\n'
    )


def test_env_store_reads_key_value_pairs(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text(
        '# Comment\n'
        'DIALOG_API_KEY=dialog-key\n'
        'KNOWLEDGE_BUILD_API_KEY=build-key\n',
        encoding='utf-8',
    )

    values = EnvStore(env_path).read()

    assert values == {
        'DIALOG_API_KEY': 'dialog-key',
        'KNOWLEDGE_BUILD_API_KEY': 'build-key',
    }
