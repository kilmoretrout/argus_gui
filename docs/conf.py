# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
project = 'Argus GUI'
copyright = '2025, Dylan Ray, Dennis Evangelista'
author = 'Dylan Ray, Dennis Evangelista'
release = '3.0.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'furo'
html_static_path = ['_static']
html_title = "Argus GUI Documentation"

# -- MyST options ------------------------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "tasklist",
]

# -- Autodoc options ---------------------------------------------------------
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}
