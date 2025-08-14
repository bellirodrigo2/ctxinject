ctxinject Documentation
=======================

A flexible dependency injection library for Python that adapts to your function signatures.
Write functions however you want - ctxinject figures out the dependencies.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api
   examples

Quick Start
-----------

Install the package:

.. code-block:: bash

   pip install ctxinject

Key Features
------------

- **FastAPI-style dependency injection** - Familiar ``Depends()`` pattern
- **Model field injection** - Direct access to model fields and methods
- **Context managers** - Automatic resource management for dependencies  
- **Priority-based async execution** - Control execution order with async batching
- **Multiple injection strategies** - By type, name, model fields, or dependencies
- **Test-friendly** - Easy dependency overriding for testing

Basic usage:

.. code-block:: python

   from ctxinject.inject import inject_args
   from ctxinject.model import ArgsInjectable, DependsInject
   
   def greet(name: str, count: int = ArgsInjectable(5)):
       return f"Hello {name}! (x{count})"
   
   # Inject dependencies
   context = {"name": "Alice"}
   injected = await inject_args(greet, context)
   result = injected()  # "Hello Alice! (x5)"

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex` 
* :ref:`search`