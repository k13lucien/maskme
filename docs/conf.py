# Configuration file for the Sphinx documentation builder.
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

# -- Project information -----------------------------------------------------
project = 'MaskMe'
copyright = '2026, MaskMe Contributors'
author = 'MaskMe Contributors'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_copybutton',
    'sphinxawesome_theme',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinxawesome_theme'
html_title = "MaskMe"
html_static_path = ['_static']

# Désactiver les marqueurs de liens permanents (¶)
html_permalinks = False

# Configuration de la coloration syntaxique
pygments_style = 'sphinx'
highlight_language = 'python3'

# -- MyST Parser configuration -----------------------------------------------
myst_enable_extensions = [
    "colon_fence",
]
