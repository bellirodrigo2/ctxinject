Examples
========

This section contains usage examples for ctxinject.

Basic Dependency Injection
---------------------------

.. code-block:: python

   from ctxinject.inject import inject_args
   from ctxinject.model import ArgsInjectable

   def greet(name: str, count: int = ArgsInjectable(5)):
       return f"Hello {name}! (x{count})"

   # Inject by name and default
   context = {"name": "Alice"}
   injected = await inject_args(greet, context)
   result = injected()  # "Hello Alice! (x5)"

FastAPI-style Dependencies
---------------------------

.. code-block:: python

   from ctxinject.model import DependsInject

   async def get_database() -> str:
       return "postgresql://localhost/db"

   def process_data(db: str = DependsInject(get_database)):
       return f"Processing with {db}"

   # Dependencies resolved automatically
   injected = await inject_args(process_data, {})
   result = injected()

Context Manager Dependencies
----------------------------

.. code-block:: python

   from contextlib import asynccontextmanager
   from ctxinject.model import DependsInject

   @asynccontextmanager
   async def get_connection():
       conn = await create_connection()
       try:
           yield conn
       finally:
           await conn.close()

   def handle_request(conn = DependsInject(get_connection)):
       return conn.query("SELECT 1")

   # Resources automatically managed
   async with AsyncExitStack() as stack:
       injected = await inject_args(handle_request, {}, stack=stack)
       result = injected()

Priority-based Async Execution
-------------------------------

.. code-block:: python

   async def get_auth(order=0) -> str:
       return "auth-token"

   async def get_user(order=1) -> str:  
       return "user-data"

   def process_request(
       auth: str = DependsInject(get_auth, order=0),
       user: str = DependsInject(get_user, order=1)
   ):
       return f"Processing {user} with {auth}"

   # Auth resolved before user (order matters)
   injected = await inject_args(process_request, {})
   result = injected()

Performance Optimization
-------------------------

.. code-block:: python

   # Use ordered=True for maximum performance
   # Pre-computes sync/async separation and ordering
   injected = await inject_args(my_function, context, ordered=True)
   result = injected()

Model Field Injection
----------------------

.. code-block:: python

   from ctxinject.model import ModelFieldInject

   class Config:
       database_url: str = "sqlite:///app.db"
       debug: bool = True

   def setup_app(
       db_url: str = ModelFieldInject(Config, "database_url"),
       debug: bool = ModelFieldInject(Config, "debug")
   ):
       return f"App: {db_url}, debug={debug}"

   config = Config()
   context = {Config: config}
   injected = await inject_args(setup_app, context)
   result = injected()

Testing with Overrides
-----------------------

.. code-block:: python

   # Production dependency
   async def get_real_service() -> str:
       return "production-service"

   def business_logic(service: str = DependsInject(get_real_service)):
       return f"Using {service}"

   # Test override
   async def get_mock_service() -> str:
       return "mock-service"

   # Override for testing
   injected = await inject_args(
       business_logic, 
       context={},
       overrides={get_real_service: get_mock_service}
   )
   result = injected()  # "Using mock-service"