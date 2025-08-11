
from ctxinject.overrides import (
    GlobalProvider,
    Provider,
    global_provider,
    resolve_overrides,
)


def test_override_and_get_override() -> None:
    provider = Provider()

    def orig() -> str:
        return "original"

    def repl() -> str:
        return "replacement"

    provider.override(orig, repl)
    assert provider.get_override(orig) is repl
    assert provider.has_override(orig)
    assert orig in provider
    assert len(provider) == 1
    assert bool(provider)


def test_remove_override() -> None:
    provider = Provider()

    def orig() -> None:
        pass

    def repl() -> None:
        pass

    provider.override(orig, repl)
    assert provider.remove_override(orig)
    assert not provider.has_override(orig)
    assert not provider.remove_override(orig)


def test_override_many_and_clear() -> None:
    provider = Provider()

    def o1() -> None:
        pass

    def r1() -> None:
        pass

    def o2() -> None:
        pass

    def r2() -> None:
        pass

    provider.override_many({o1: r1, o2: r2})
    assert provider.get_override(o1) is r1
    assert provider.get_override(o2) is r2
    provider.clear()
    assert len(provider) == 0


def test_scope_temporary_override() -> None:
    provider = Provider()

    def orig() -> str:
        return "original"

    def repl() -> str:
        return "replacement"

    with provider.scope(orig, repl):
        assert provider.get_override(orig) is repl
    assert provider.get_override(orig) is None


def test_scope_many_temporary_override() -> None:
    provider = Provider()

    def o1() -> str:
        return "o1"

    def r1() -> str:
        return "r1"

    def o2() -> str:
        return "o2"

    def r2() -> str:
        return "r2"

    provider.override(o1, r1)
    original_state = provider.get_override(o1)
    with provider.scope_many({o1: r1, o2: r2}):
        assert provider.get_override(o1) is r1
        assert provider.get_override(o2) is r2
    assert provider.get_override(o1) is original_state
    assert provider.get_override(o2) is None


def test_copy_creates_independent_provider() -> None:
    provider = Provider()

    def orig() -> None:
        pass

    def repl() -> None:
        pass

    provider.override(orig, repl)
    copy_provider = provider.copy()
    assert copy_provider.get_override(orig) is repl
    provider.remove_override(orig)
    assert copy_provider.has_override(orig)


def test_merge_providers() -> None:
    p1 = Provider()
    p2 = Provider()

    def o1() -> None:
        pass

    def r1() -> None:
        pass

    def o2() -> None:
        pass

    def r2() -> None:
        pass

    p1.override(o1, r1)
    p2.override(o2, r2)
    merged = p1.merge(p2)
    assert merged.get_override(o1) is r1
    assert merged.get_override(o2) is r2


def test_global_provider_delegation_and_reset() -> None:
    gp = GlobalProvider()

    def orig() -> None:
        pass

    def repl() -> None:
        pass

    gp.override(orig, repl)
    assert gp.get_override(orig) is repl
    gp.reset()
    assert gp.get_override(orig) is None


def test_resolve_overrides_behavior() -> None:
    global_provider.clear()

    def o1() -> None:
        pass

    def r1() -> None:
        pass

    def o2() -> None:
        pass

    def r2() -> None:
        pass

    local = Provider()
    local.override(o1, r1)
    global_provider.override(o2, r2)
    assert resolve_overrides(local, use_global=True) == {o1: r1, o2: r2}
    assert resolve_overrides(local, use_global=False) == {o1: r1}
    assert resolve_overrides(None, use_global=True) == {o2: r2}
    assert resolve_overrides(None, use_global=False) == {}
