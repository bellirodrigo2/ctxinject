import os
import sys
from typing import Any, List

sys.path.insert(0, os.path.abspath("../../"))

project = "ctxinject"
copyright = "2025, rodbell"
author = "rodbell"
release = "0.1.1"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns: List[Any] = []

html_theme = "sphinx_rtd_theme"
html_static_path: List[Any] = []  # Vazio para evitar warning

# Configurações do autodoc
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Configurações do Napoleon
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# Reduzir warnings
autodoc_member_order = "bysource"
autodoc_typehints = "description"
suppress_warnings = ["image.nonlocal_uri"]
