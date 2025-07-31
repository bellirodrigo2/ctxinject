# ruff: noqa
# mypy: ignore-errors
"""
Real-World Microservices Architecture with ctxinject

This example demonstrates a production-ready e-commerce microservices architecture
using ctxinject for dependency injection, service orchestration, and clean separation
of concerns. Perfect for understanding how to build scalable, maintainable systems.

Architecture Overview:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│  Order Service   │───▶│ Payment Service │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  User Service   │    │ Inventory Service│    │ Notification    │
└─────────────────┘    └──────────────────┘    │   Service       │
         │                       │              └─────────────────┘
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   Database      │    │   Event Bus      │
└─────────────────┘    └──────────────────┘

Features Demonstrated:
- Service-to-service communication
- Event-driven architecture
- Circuit breaker patterns
- Distributed tracing
- Configuration management
- Testing with service mocks
- Health checks and monitoring
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from ctxinject.inject import inject_args
from ctxinject.model import ArgsInjectable, DependsInject, ModelFieldInject

# =============================================================================
# Domain Models and Events
# =============================================================================


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""

    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderItem(BaseModel):
    """Individual item in an order."""

    product_id: str
    product_name: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)

    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price


class Order(BaseModel):
    """Complete order information."""

    order_id: str
    user_id: str
    items: List[OrderItem]
    status: OrderStatus = OrderStatus.PENDING
    total_amount: float
    currency: str = "USD"
    created_at: datetime
    updated_at: datetime
    shipping_address: Dict[str, Any]
    payment_method: str


class OrderEvent(BaseModel):
    """Domain event for order state changes."""

    event_id: str
    event_type: str
    order_id: str
    user_id: str
    data: Dict[str, Any]
    timestamp: datetime
    correlation_id: str


class PaymentRequest(BaseModel):
    """Payment processing request."""

    payment_id: str
    order_id: str
    amount: float
    currency: str
    payment_method: str
    user_id: str


# =============================================================================
# Configuration and Infrastructure
# =============================================================================


class ServiceConfig:
    """Microservice configuration management."""

    # Database configuration
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # Redis configuration
    redis_host: str
    redis_port: int
    redis_db: int

    # External API configuration
    payment_gateway_url: str
    payment_gateway_key: str
    notification_service_url: str

    # Circuit breaker configuration
    circuit_breaker_threshold: int
    circuit_breaker_timeout: int

    # Tracing configuration
    jaeger_agent_host: str
    jaeger_agent_port: int

    def __init__(self):
        # Database settings
        self.db_host = "localhost"
        self.db_port = 5432
        self.db_name = "ecommerce"
        self.db_user = "app_user"
        self.db_password = "secure_password"

        # Redis settings
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_db = 0

        # External services
        self.payment_gateway_url = "https://api.stripe.com/v1"
        self.payment_gateway_key = "sk_test_payment_key"
        self.notification_service_url = "https://api.sendgrid.com/v3"

        # Circuit breaker
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 60

        # Distributed tracing
        self.jaeger_agent_host = "localhost"
        self.jaeger_agent_port = 6831

    @property
    def database_url(self) -> str:
        """Get database connection URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_service_timeouts(self) -> Dict[str, float]:
        """Get service timeout configuration."""
        return {
            "database": 5.0,
            "redis": 1.0,
            "payment_gateway": 10.0,
            "notification_service": 5.0,
            "inventory_service": 3.0,
        }


# =============================================================================
# Service Layer - Infrastructure Services
# =============================================================================


async def get_database_connection() -> "DatabaseService":
    """Create database connection with connection pooling."""
    await asyncio.sleep(0.01)  # Simulate connection setup
    return DatabaseService()


async def get_redis_connection() -> "CacheService":
    """Create Redis connection for caching and sessions."""
    await asyncio.sleep(0.005)
    return CacheService()


async def get_event_bus() -> "EventBusService":
    """Create event bus for inter-service communication."""
    await asyncio.sleep(0.002)
    return EventBusService()


async def get_circuit_breaker() -> "CircuitBreakerService":
    """Create circuit breaker for resilience patterns."""
    return CircuitBreakerService()


async def get_tracer() -> "TracingService":
    """Create distributed tracing service."""
    return TracingService()


class DatabaseService:
    """Database service with connection pooling and transactions."""

    def __init__(self):
        self.connected = True
        self.orders_db = {}
        self.users_db = {}
        self.products_db = {
            "prod-001": {"name": "Laptop", "price": 999.99, "stock": 50},
            "prod-002": {"name": "Mouse", "price": 29.99, "stock": 100},
            "prod-003": {"name": "Keyboard", "price": 79.99, "stock": 75},
        }

    async def save_order(self, order: Order) -> Order:
        """Save order to database."""
        await asyncio.sleep(0.02)  # Simulate database write
        self.orders_db[order.order_id] = order.dict()
        return order

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        await asyncio.sleep(0.01)
        order_data = self.orders_db.get(order_id)
        return Order(**order_data) if order_data else None

    async def update_order_status(self, order_id: str, status: OrderStatus) -> bool:
        """Update order status."""
        await asyncio.sleep(0.015)
        if order_id in self.orders_db:
            self.orders_db[order_id]["status"] = status
            self.orders_db[order_id]["updated_at"] = datetime.utcnow().isoformat()
            return True
        return False

    async def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product information."""
        await asyncio.sleep(0.01)
        return self.products_db.get(product_id)

    async def update_product_stock(self, product_id: str, quantity_delta: int) -> bool:
        """Update product stock levels."""
        await asyncio.sleep(0.015)
        if product_id in self.products_db:
            current_stock = self.products_db[product_id]["stock"]
            new_stock = current_stock + quantity_delta
            if new_stock >= 0:
                self.products_db[product_id]["stock"] = new_stock
                return True
        return False


class CacheService:
    """Redis-based caching service for performance optimization."""

    def __init__(self):
        self.cache = {}
        self.session_store = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        await asyncio.sleep(0.001)
        return self.cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        await asyncio.sleep(0.001)
        self.cache[key] = value
        return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        await asyncio.sleep(0.001)
        return self.cache.pop(key, None) is not None

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session data."""
        await asyncio.sleep(0.002)
        return self.session_store.get(session_id)

    async def set_session(
        self, session_id: str, data: Dict[str, Any], ttl: int = 3600
    ) -> bool:
        """Store user session data."""
        await asyncio.sleep(0.002)
        self.session_store[session_id] = data
        return True


class EventBusService:
    """Event bus for asynchronous inter-service communication."""

    def __init__(self):
        self.events = []
        self.subscribers = {}

    async def publish(self, event: OrderEvent) -> bool:
        """Publish domain event to event bus."""
        await asyncio.sleep(0.002)
        self.events.append(event.dict())

        # Notify subscribers
        event_type = event.event_type
        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    print(f"Event handler error: {e}")

        return True

    def subscribe(self, event_type: str, handler):
        """Subscribe to domain events."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    async def get_events(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get events by correlation ID."""
        await asyncio.sleep(0.001)
        return [
            event
            for event in self.events
            if event.get("correlation_id") == correlation_id
        ]


class CircuitBreakerService:
    """Circuit breaker pattern for external service resilience."""

    def __init__(self):
        self.failures = {}
        self.last_failure_time = {}
        self.circuit_open = {}

    async def call_with_circuit_breaker(self, service_name: str, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        threshold = 3
        timeout = 30

        # Check if circuit is open
        if self.circuit_open.get(service_name, False):
            last_failure = self.last_failure_time.get(service_name, 0)
            if time.time() - last_failure < timeout:
                raise Exception(f"Circuit breaker open for {service_name}")
            else:
                # Try to close circuit
                self.circuit_open[service_name] = False
                self.failures[service_name] = 0

        try:
            result = await func(*args, **kwargs)
            # Reset failure count on success
            self.failures[service_name] = 0
            return result
        except Exception as e:
            # Increment failure count
            self.failures[service_name] = self.failures.get(service_name, 0) + 1
            self.last_failure_time[service_name] = time.time()

            # Open circuit if threshold exceeded
            if self.failures[service_name] >= threshold:
                self.circuit_open[service_name] = True

            raise e


class TracingService:
    """Distributed tracing for request monitoring."""

    def __init__(self):
        self.traces = {}

    def start_span(self, span_name: str, correlation_id: str) -> str:
        """Start a new tracing span."""
        span_id = str(uuid4())
        if correlation_id not in self.traces:
            self.traces[correlation_id] = []

        self.traces[correlation_id].append(
            {
                "span_id": span_id,
                "span_name": span_name,
                "start_time": time.time(),
                "end_time": None,
                "duration_ms": None,
                "tags": {},
            }
        )

        return span_id

    def finish_span(
        self, span_id: str, correlation_id: str, tags: Optional[Dict[str, Any]] = None
    ):
        """Finish a tracing span."""
        if correlation_id in self.traces:
            for span in self.traces[correlation_id]:
                if span["span_id"] == span_id:
                    span["end_time"] = time.time()
                    span["duration_ms"] = (span["end_time"] - span["start_time"]) * 1000
                    if tags:
                        span["tags"].update(tags)
                    break

    def get_trace(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get complete trace by correlation ID."""
        return self.traces.get(correlation_id, [])


# =============================================================================
# Business Services - Domain Logic
# =============================================================================


class InventoryService:
    """Inventory management service."""

    def __init__(self, db: DatabaseService, cache: CacheService):
        self.db = db
        self.cache = cache

    async def check_availability(self, product_id: str, quantity: int) -> bool:
        """Check if product is available in requested quantity."""
        # Try cache first
        cache_key = f"stock:{product_id}"
        cached_stock = await self.cache.get(cache_key)

        if cached_stock is not None:
            return cached_stock >= quantity

        # Get from database
        product = await self.db.get_product(product_id)
        if product:
            await self.cache.set(cache_key, product["stock"], ttl=60)
            return product["stock"] >= quantity

        return False

    async def reserve_items(self, items: List[OrderItem], order_id: str) -> bool:
        """Reserve inventory items for an order."""
        reservations = []

        try:
            for item in items:
                if not await self.check_availability(item.product_id, item.quantity):
                    # Rollback previous reservations
                    for prev_item in reservations:
                        await self.db.update_product_stock(
                            prev_item.product_id, prev_item.quantity
                        )
                    return False

                # Reserve stock
                success = await self.db.update_product_stock(
                    item.product_id, -item.quantity
                )
                if success:
                    reservations.append(item)
                    # Invalidate cache
                    await self.cache.delete(f"stock:{item.product_id}")
                else:
                    # Rollback
                    for prev_item in reservations:
                        await self.db.update_product_stock(
                            prev_item.product_id, prev_item.quantity
                        )
                    return False

            return True

        except Exception:
            # Rollback on any error
            for item in reservations:
                await self.db.update_product_stock(item.product_id, item.quantity)
            return False


class PaymentService:
    """Payment processing service with external gateway integration."""

    def __init__(self, circuit_breaker: CircuitBreakerService, config: ServiceConfig):
        self.circuit_breaker = circuit_breaker
        self.config = config
        self.payment_records = {}

    async def process_payment(self, payment_request: PaymentRequest) -> Dict[str, Any]:
        """Process payment through external gateway."""

        async def _call_payment_gateway():
            # Simulate external API call
            await asyncio.sleep(0.1)

            # Simulate occasional failures for circuit breaker demo
            if random.random() < 0.1:  # 10% failure rate
                raise Exception("Payment gateway timeout")

            # Mock successful payment
            return {
                "transaction_id": f"txn_{uuid4()}",
                "status": PaymentStatus.AUTHORIZED,
                "amount": payment_request.amount,
                "currency": payment_request.currency,
                "gateway_response": {"code": "00", "message": "Approved"},
            }

        try:
            result = await self.circuit_breaker.call_with_circuit_breaker(
                "payment_gateway", _call_payment_gateway
            )

            # Store payment record
            self.payment_records[payment_request.payment_id] = {
                **payment_request.dict(),
                **result,
                "processed_at": datetime.utcnow().isoformat(),
            }

            return result

        except Exception as e:
            # Payment failed
            failure_result = {
                "transaction_id": None,
                "status": PaymentStatus.FAILED,
                "error": str(e),
                "gateway_response": {"code": "99", "message": "Payment failed"},
            }

            self.payment_records[payment_request.payment_id] = {
                **payment_request.dict(),
                **failure_result,
                "processed_at": datetime.utcnow().isoformat(),
            }

            return failure_result

    async def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment status by ID."""
        return self.payment_records.get(payment_id)


class NotificationService:
    """Notification service for customer communications."""

    def __init__(self, circuit_breaker: CircuitBreakerService):
        self.circuit_breaker = circuit_breaker
        self.sent_notifications = []

    async def send_order_confirmation(self, order: Order, user_email: str) -> bool:
        """Send order confirmation email."""

        async def _send_email():
            await asyncio.sleep(0.05)  # Simulate email API call

            if random.random() < 0.05:  # 5% failure rate
                raise Exception("Email service unavailable")

            return True

        try:
            await self.circuit_breaker.call_with_circuit_breaker(
                "notification_service", _send_email
            )

            self.sent_notifications.append(
                {
                    "type": "order_confirmation",
                    "order_id": order.order_id,
                    "user_email": user_email,
                    "sent_at": datetime.utcnow().isoformat(),
                }
            )

            return True

        except Exception:
            return False

    async def send_payment_notification(
        self, order_id: str, user_email: str, status: PaymentStatus
    ) -> bool:
        """Send payment status notification."""

        async def _send_email():
            await asyncio.sleep(0.05)
            return True

        try:
            await self.circuit_breaker.call_with_circuit_breaker(
                "notification_service", _send_email
            )

            self.sent_notifications.append(
                {
                    "type": "payment_notification",
                    "order_id": order_id,
                    "user_email": user_email,
                    "payment_status": status,
                    "sent_at": datetime.utcnow().isoformat(),
                }
            )

            return True

        except Exception:
            return False


# =============================================================================
# Dependency Factory Functions
# =============================================================================


async def create_inventory_service(
    db: Annotated[DatabaseService, DependsInject(get_database_connection)],
    cache: Annotated[CacheService, DependsInject(get_redis_connection)],
) -> InventoryService:
    """Create inventory service with dependencies."""
    return InventoryService(db, cache)


async def create_payment_service(
    circuit_breaker: Annotated[
        CircuitBreakerService, DependsInject(get_circuit_breaker)
    ],
    config: Annotated[ServiceConfig, ArgsInjectable(ServiceConfig())],
) -> PaymentService:
    """Create payment service with dependencies."""
    return PaymentService(circuit_breaker, config)


async def create_notification_service(
    circuit_breaker: Annotated[
        CircuitBreakerService, DependsInject(get_circuit_breaker)
    ],
) -> NotificationService:
    """Create notification service with dependencies."""
    return NotificationService(circuit_breaker)


def generate_correlation_id() -> str:
    """Generate unique correlation ID for request tracing."""
    return f"corr_{uuid4()}"


# =============================================================================
# Order Processing Orchestration
# =============================================================================


async def create_order(
    # Request data
    user_id: Annotated[str, ArgsInjectable(...)],
    items: Annotated[List[OrderItem], ArgsInjectable(...)],
    shipping_address: Annotated[Dict[str, Any], ArgsInjectable(...)],
    payment_method: Annotated[str, ArgsInjectable(...)],
    # Service dependencies
    db: Annotated[DatabaseService, DependsInject(get_database_connection)],
    inventory: Annotated[InventoryService, DependsInject(create_inventory_service)],
    payment: Annotated[PaymentService, DependsInject(create_payment_service)],
    notifications: Annotated[
        NotificationService, DependsInject(create_notification_service)
    ],
    event_bus: Annotated[EventBusService, DependsInject(get_event_bus)],
    tracer: Annotated[TracingService, DependsInject(get_tracer)],
    # Configuration
    timeouts: Annotated[
        Dict[str, float], ModelFieldInject(ServiceConfig, field="get_service_timeouts")
    ],
    # Request metadata
    correlation_id: Annotated[str, DependsInject(generate_correlation_id)],
) -> Dict[str, Any]:
    """
    Orchestrate order creation across multiple microservices.

    This demonstrates the power of dependency injection for complex business workflows
    involving multiple services, external APIs, and distributed transactions.
    """

    start_time = time.time()

    # Start distributed tracing
    main_span = tracer.start_span("create_order", correlation_id)

    try:
        # Step 1: Validate inventory availability
        inventory_span = tracer.start_span("check_inventory", correlation_id)

        for item in items:
            available = await inventory.check_availability(
                item.product_id, item.quantity
            )
            if not available:
                tracer.finish_span(
                    inventory_span, correlation_id, {"error": "insufficient_stock"}
                )
                raise ValueError(f"Insufficient stock for product {item.product_id}")

        tracer.finish_span(inventory_span, correlation_id, {"status": "available"})

        # Step 2: Create order record
        order_span = tracer.start_span("create_order_record", correlation_id)

        order_id = f"order_{uuid4()}"
        total_amount = sum(item.total_price for item in items)

        order = Order(
            order_id=order_id,
            user_id=user_id,
            items=items,
            total_amount=total_amount,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            shipping_address=shipping_address,
            payment_method=payment_method,
        )

        saved_order = await db.save_order(order)
        tracer.finish_span(order_span, correlation_id, {"order_id": order_id})

        # Step 3: Reserve inventory
        reservation_span = tracer.start_span("reserve_inventory", correlation_id)

        reservation_success = await inventory.reserve_items(items, order_id)
        if not reservation_success:
            tracer.finish_span(
                reservation_span, correlation_id, {"error": "reservation_failed"}
            )
            raise ValueError("Failed to reserve inventory items")

        tracer.finish_span(reservation_span, correlation_id, {"status": "reserved"})

        # Step 4: Process payment
        payment_span = tracer.start_span("process_payment", correlation_id)

        payment_request = PaymentRequest(
            payment_id=f"pay_{uuid4()}",
            order_id=order_id,
            amount=total_amount,
            currency="USD",
            payment_method=payment_method,
            user_id=user_id,
        )

        payment_result = await payment.process_payment(payment_request)

        if payment_result["status"] == PaymentStatus.FAILED:
            tracer.finish_span(
                payment_span, correlation_id, {"error": "payment_failed"}
            )
            # TODO: Implement compensation - release inventory
            raise ValueError(
                f"Payment failed: {payment_result.get('error', 'Unknown error')}"
            )

        tracer.finish_span(payment_span, correlation_id, {"status": "authorized"})

        # Step 5: Update order status
        await db.update_order_status(order_id, OrderStatus.CONFIRMED)

        # Step 6: Publish domain events
        event_span = tracer.start_span("publish_events", correlation_id)

        order_created_event = OrderEvent(
            event_id=str(uuid4()),
            event_type="order.created",
            order_id=order_id,
            user_id=user_id,
            data={
                "total_amount": total_amount,
                "items_count": len(items),
                "payment_method": payment_method,
            },
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
        )

        await event_bus.publish(order_created_event)

        payment_authorized_event = OrderEvent(
            event_id=str(uuid4()),
            event_type="payment.authorized",
            order_id=order_id,
            user_id=user_id,
            data={
                "payment_id": payment_request.payment_id,
                "transaction_id": payment_result["transaction_id"],
                "amount": total_amount,
            },
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id,
        )

        await event_bus.publish(payment_authorized_event)
        tracer.finish_span(event_span, correlation_id, {"events_published": 2})

        # Step 7: Send notifications (async, non-blocking)
        notification_span = tracer.start_span("send_notifications", correlation_id)

        # In real system, this would be async/background task
        user_email = f"user_{user_id}@example.com"  # Mock user email
        await notifications.send_order_confirmation(saved_order, user_email)

        tracer.finish_span(notification_span, correlation_id, {"status": "sent"})

        # Complete main span
        processing_time = (time.time() - start_time) * 1000
        tracer.finish_span(
            main_span,
            correlation_id,
            {
                "status": "success",
                "processing_time_ms": processing_time,
                "total_amount": total_amount,
            },
        )

        return {
            "success": True,
            "order_id": order_id,
            "status": OrderStatus.CONFIRMED,
            "total_amount": total_amount,
            "payment_status": payment_result["status"],
            "transaction_id": payment_result["transaction_id"],
            "correlation_id": correlation_id,
            "processing_time_ms": processing_time,
        }

    except Exception as e:
        # Handle failures and publish compensation events
        error_span = tracer.start_span("handle_error", correlation_id)

        # TODO: Implement saga pattern for distributed transaction rollback
        # This would include:
        # - Release reserved inventory
        # - Refund payment if captured
        # - Update order status to cancelled
        # - Publish compensation events

        processing_time = (time.time() - start_time) * 1000
        tracer.finish_span(error_span, correlation_id, {"error": str(e)})
        tracer.finish_span(
            main_span,
            correlation_id,
            {
                "status": "failed",
                "error": str(e),
                "processing_time_ms": processing_time,
            },
        )

        return {
            "success": False,
            "error": str(e),
            "correlation_id": correlation_id,
            "processing_time_ms": processing_time,
        }


# =============================================================================
# Order Status and Tracking
# =============================================================================


async def get_order_status(
    # Request parameters
    order_id: Annotated[str, ArgsInjectable(...)],
    user_id: Annotated[str, ArgsInjectable(...)],
    # Service dependencies
    db: Annotated[DatabaseService, DependsInject(get_database_connection)],
    cache: Annotated[CacheService, DependsInject(get_redis_connection)],
    payment: Annotated[PaymentService, DependsInject(create_payment_service)],
    event_bus: Annotated[EventBusService, DependsInject(get_event_bus)],
    tracer: Annotated[TracingService, DependsInject(get_tracer)],
    # Request metadata
    correlation_id: Annotated[str, DependsInject(generate_correlation_id)],
) -> Dict[str, Any]:
    """Get comprehensive order status with payment and event history."""

    span = tracer.start_span("get_order_status", correlation_id)
    start_time = time.time()

    try:
        # Get order from database
        order = await db.get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Verify user access
        if order.user_id != user_id:
            raise ValueError("Access denied: order belongs to different user")

        # Get payment information
        # In real system, we'd need to track payment_id with order
        payment_info = None
        for payment_id, payment_data in payment.payment_records.items():
            if payment_data.get("order_id") == order_id:
                payment_info = payment_data
                break

        # Get event history
        events = await event_bus.get_events(correlation_id)
        order_events = [e for e in events if e.get("order_id") == order_id]

        # Get distributed trace
        trace_data = tracer.get_trace(correlation_id)

        processing_time = (time.time() - start_time) * 1000
        tracer.finish_span(span, correlation_id, {"status": "success"})

        return {
            "success": True,
            "order": order.dict(),
            "payment_info": payment_info,
            "events": order_events,
            "trace": trace_data,
            "correlation_id": correlation_id,
            "processing_time_ms": processing_time,
        }

    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        tracer.finish_span(span, correlation_id, {"error": str(e)})

        return {
            "success": False,
            "error": str(e),
            "correlation_id": correlation_id,
            "processing_time_ms": processing_time,
        }


# =============================================================================
# Demo and Testing
# =============================================================================


async def demo_successful_order():
    """Demonstrate successful order processing flow."""
    print("🛒 Demo: Successful E-commerce Order Processing")
    print("=" * 70)

    # Create sample order data
    order_items = [
        OrderItem(
            product_id="prod-001", product_name="Laptop", quantity=1, unit_price=999.99
        ),
        OrderItem(
            product_id="prod-002", product_name="Mouse", quantity=2, unit_price=29.99
        ),
    ]

    shipping_address = {
        "street": "123 Main St",
        "city": "San Francisco",
        "state": "CA",
        "zip": "94105",
        "country": "USA",
    }

    # Create context for dependency injection
    context = {
        "user_id": "user_12345",
        "items": order_items,
        "shipping_address": shipping_address,
        "payment_method": "credit_card",
    }

    # Inject dependencies and execute order creation
    injected_create_order = await inject_args(create_order, context)
    result = await injected_create_order()

    print(f"✅ Order Creation Result:")
    print(f"   Success: {result['success']}")
    if result["success"]:
        print(f"   Order ID: {result['order_id']}")
        print(f"   Total Amount: ${result['total_amount']:.2f}")
        print(f"   Payment Status: {result['payment_status']}")
        print(f"   Transaction ID: {result['transaction_id']}")
        print(f"   Processing Time: {result['processing_time_ms']:.2f}ms")
        print(f"   Correlation ID: {result['correlation_id']}")

        # Now check order status
        print(f"\n📊 Checking Order Status...")
        status_context = {"order_id": result["order_id"], "user_id": "user_12345"}

        injected_get_status = await inject_args(get_order_status, status_context)
        status_result = await injected_get_status()

        if status_result["success"]:
            print(f"   Order Status: {status_result['order']['status']}")
            print(f"   Events Count: {len(status_result['events'])}")
            print(f"   Trace Spans: {len(status_result['trace'])}")
    else:
        print(f"   Error: {result['error']}")


async def demo_with_service_mocks():
    """Demonstrate testing with service mocks."""
    print("\n🧪 Demo: Testing with Service Mocks")
    print("=" * 70)

    # Mock services for testing
    class MockPaymentService:
        def __init__(self, should_fail=False):
            self.should_fail = should_fail
            self.payment_records = {}

        async def process_payment(self, payment_request):
            if self.should_fail:
                return {
                    "transaction_id": None,
                    "status": PaymentStatus.FAILED,
                    "error": "Mocked payment failure",
                    "gateway_response": {"code": "99", "message": "Test failure"},
                }
            else:
                return {
                    "transaction_id": f"mock_txn_{uuid4()}",
                    "status": PaymentStatus.AUTHORIZED,
                    "amount": payment_request.amount,
                    "currency": payment_request.currency,
                    "gateway_response": {"code": "00", "message": "Mock approved"},
                }

    # Create mock that fails payment
    def create_failing_payment_service():
        return MockPaymentService(should_fail=True)

    # Define overrides for testing
    overrides = {create_payment_service: create_failing_payment_service}

    # Test with failing payment
    order_items = [
        OrderItem(
            product_id="prod-003", product_name="Keyboard", quantity=1, unit_price=79.99
        )
    ]

    context = {
        "user_id": "test_user",
        "items": order_items,
        "shipping_address": {"street": "Test St", "city": "Test City"},
        "payment_method": "test_card",
    }

    # Inject with overrides
    injected_create_order = await inject_args(
        create_order, context, overrides=overrides
    )
    result = await injected_create_order()

    print(f"🧪 Test Result (Payment Failure):")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'N/A')}")
    print(f"   Processing Time: {result['processing_time_ms']:.2f}ms")
    print("✅ Successfully demonstrated error handling with mocks")


async def demo_circuit_breaker():
    """Demonstrate circuit breaker pattern."""
    print("\n⚡ Demo: Circuit Breaker Pattern")
    print("=" * 70)

    # This demo shows how the circuit breaker protects against cascading failures
    # when external services are unavailable

    print("Simulating multiple payment failures to trigger circuit breaker...")

    for i in range(5):
        try:
            order_items = [
                OrderItem(
                    product_id="prod-001",
                    product_name="Test Product",
                    quantity=1,
                    unit_price=10.00,
                )
            ]

            context = {
                "user_id": f"test_user_{i}",
                "items": order_items,
                "shipping_address": {"test": "address"},
                "payment_method": "test_card",
            }

            injected_create_order = await inject_args(create_order, context)
            result = await injected_create_order()

            if result["success"]:
                print(f"   Attempt {i+1}: ✅ Success")
            else:
                print(
                    f"   Attempt {i+1}: ❌ Failed - {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            print(f"   Attempt {i+1}: ❌ Circuit breaker exception - {str(e)}")

    print("✅ Circuit breaker pattern demonstrated")


async def main():
    """Run all microservices demos."""
    print("🏗️  Real-World Microservices Architecture with ctxinject")
    print("=" * 80)
    print("Demonstrating production-ready patterns for scalable e-commerce systems:")
    print("• Service orchestration with dependency injection")
    print("• Event-driven architecture with domain events")
    print("• Circuit breaker pattern for resilience")
    print("• Distributed tracing and monitoring")
    print("• Testing with service mocks and overrides")
    print()

    await demo_successful_order()
    await demo_with_service_mocks()
    await demo_circuit_breaker()

    print("\n" + "=" * 80)
    print("✨ All microservices demos completed successfully!")
    print()
    print("Key Benefits Demonstrated:")
    print("🎯 Clean separation of concerns with dependency injection")
    print("🚀 High-performance async service orchestration")
    print("🛡️  Resilience patterns (circuit breaker, timeouts, retries)")
    print("📊 Observability with distributed tracing")
    print("🧪 Testability with easy service mocking")
    print("📈 Scalability through event-driven architecture")


if __name__ == "__main__":
    asyncio.run(main())
