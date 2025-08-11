#!/usr/bin/env python3
"""
Example demonstrating the new Provider-based override system.
"""
import asyncio

from ctxinject import DependsInject, Provider, global_provider, inject_args


# Production dependencies
def prod_database() -> str:
    return "postgresql://prod-server/app"


def prod_cache() -> str:
    return "redis://prod-server:6379"


def prod_logger() -> str:
    return "production-logger"


# Test dependencies
def test_database() -> str:
    return "sqlite:///:memory:"


def test_cache() -> str:
    return "memory-cache"


def test_logger() -> str:
    return "test-logger"


# Business logic that uses dependencies
def process_request(
    db: str = DependsInject(prod_database),
    cache: str = DependsInject(prod_cache),
    logger: str = DependsInject(prod_logger),
) -> str:
    return f"Processing with DB: {db}, Cache: {cache}, Logger: {logger}"


async def main():
    """Demonstrate different override patterns."""

    print("=== Override System Demonstration ===\n")

    # 1. Without overrides (production dependencies)
    print("1. Production mode (no overrides):")
    injected = await inject_args(process_request, {})
    result = injected()
    print(f"   {result}\n")

    # 2. Local provider with specific overrides
    print("2. Local provider overrides:")
    local_provider = Provider()
    local_provider.override(prod_database, test_database)
    local_provider.override(prod_cache, test_cache)

    injected = await inject_args(process_request, {}, overrides=local_provider)
    result = injected()
    print(f"   {result}\n")

    # 3. Context manager for temporary overrides
    print("3. Temporary override with context manager:")
    with local_provider.scope(prod_logger, test_logger):
        injected = await inject_args(process_request, {}, overrides=local_provider)
        result = injected()
        print(f"   Inside scope: {result}")

    # Outside scope, logger override is removed
    injected = await inject_args(process_request, {}, overrides=local_provider)
    result = injected()
    print(f"   Outside scope: {result}\n")

    # 4. Global provider
    print("4. Global provider overrides:")
    global_provider.override(prod_database, test_database)
    global_provider.override(prod_cache, test_cache)
    global_provider.override(prod_logger, test_logger)

    # No local provider specified - uses global
    injected = await inject_args(process_request, {})
    result = injected()
    print(f"   {result}\n")

    # 5. Local provider overrides global
    print("5. Local provider takes precedence over global:")

    def special_database() -> str:
        return "special://localhost/test"

    special_provider = Provider()
    special_provider.override(prod_database, special_database)

    injected = await inject_args(process_request, {}, overrides=special_provider)
    result = injected()
    print(f"   {result}\n")

    # 6. Multiple overrides at once
    print("6. Multiple overrides at once:")
    batch_provider = Provider()
    batch_provider.override_many(
        {
            prod_database: lambda: "batch-db",
            prod_cache: lambda: "batch-cache",
            prod_logger: lambda: "batch-logger",
        }
    )

    injected = await inject_args(process_request, {}, overrides=batch_provider)
    result = injected()
    print(f"   {result}\n")

    # 7. Provider merge
    print("7. Provider merge:")
    provider_a = Provider()
    provider_a.override(prod_database, lambda: "provider-a-db")
    provider_a.override(prod_cache, lambda: "provider-a-cache")

    provider_b = Provider()
    provider_b.override(prod_cache, lambda: "provider-b-cache")  # This will override A
    provider_b.override(prod_logger, lambda: "provider-b-logger")

    merged_provider = provider_a.merge(provider_b)
    injected = await inject_args(process_request, {}, overrides=merged_provider)
    result = injected()
    print(f"   {result}\n")

    # 8. Legacy dict format still works
    print("8. Legacy dict format (backward compatibility):")
    legacy_overrides = {
        prod_database: lambda: "legacy-db",
        prod_cache: lambda: "legacy-cache",
    }

    injected = await inject_args(process_request, {}, overrides=legacy_overrides)
    result = injected()
    print(f"   {result}\n")

    # Clean up global provider
    global_provider.clear()
    print("Global provider cleared.")


if __name__ == "__main__":
    asyncio.run(main())
