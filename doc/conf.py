# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 Simon Besnard
# SPDX-FileCopyrightText: 2026 Helmholtz Centre Potsdam - GFZ German Research Centre for Geosciences

import importlib
import inspect
import os
import sys
from datetime import datetime
from importlib.metadata import version as version_
from unittest.mock import MagicMock

# Pre-mock heavy optional imports so conf.py can be loaded without the full
# environment (e.g. on ReadTheDocs).  Must happen before `import eoforeststac`.
for _mod in ["tiledb", "pdal"]:
    sys.modules.setdefault(_mod, MagicMock())

from docutils import nodes
from docutils.parsers.rst import Directive

import eoforeststac

# Minimum version, enforced by sphinx
needs_sphinx = "4.3"

# -----------------------------------------------------------------------------
# General configuration
# -----------------------------------------------------------------------------

extensions = [
    "sphinxcontrib.mermaid",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "IPython.sphinxext.ipython_directive",
    "IPython.sphinxext.ipython_console_highlighting",
    "sphinx.ext.linkcode",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_inline_tabs",
    "sphinx_gallery.gen_gallery",
]

# Gallery configuration — files are shown as static examples (not executed)
sphinx_gallery_conf = {
    "filename_pattern": r"/plot_",  # only files named plot_*.py are executed
    "examples_dirs": "gallery",
    "gallery_dirs": "auto_examples",
}

skippable_extensions = [
    ("breathe", "skip generating C/C++ API from comment blocks."),
]
for ext, warn in skippable_extensions:
    ext_exist = importlib.util.find_spec(ext) is not None
    if ext_exist:
        extensions.append(ext)
    else:
        print(f"Unable to find Sphinx extension '{ext}', {warn}.")

templates_path = ["_templates"]
source_suffix = ".rst"

project = "eoforeststac"
year = datetime.now().year
copyright = f"2025-{year}, Simon Besnard, GFZ Potsdam"

version = version_("eoforeststac")

suppress_warnings = ["docutils.parsers.rst.states"]

today_fmt = "%B %d, %Y"
html_last_updated_fmt = today_fmt

exclude_dirs = []
exclude_patterns = ["gallery/README.rst"]

default_role = "autolink"

add_function_parentheses = False


class LegacyDirective(Directive):
    """
    Adapted from docutils/parsers/rst/directives/admonitions.py

    Uses a default text if the directive does not have contents. If it does,
    the default text is concatenated to the contents.
    """

    has_content = True
    node_class = nodes.admonition
    optional_arguments = 1

    def run(self):
        try:
            obj = self.arguments[0]
        except IndexError:
            obj = "submodule"
        text = (
            f"This {obj} is considered legacy and will no longer receive "
            "updates. This could also mean it will be removed in future "
            "eoforeststac versions."
        )

        try:
            self.content[0] = text + " " + self.content[0]
        except IndexError:
            source, lineno = self.state_machine.get_source_and_line(self.lineno)
            self.content.append(text, source=source, offset=lineno)
        text = "\n".join(self.content)
        admonition_node = self.node_class(rawsource=text)
        title_text = "Legacy"
        textnodes, _ = self.state.inline_text(title_text, self.lineno)
        title = nodes.title(title_text, "", *textnodes)
        admonition_node += title
        admonition_node["classes"] = ["admonition-legacy"]
        self.state.nested_parse(self.content, self.content_offset, admonition_node)
        return [admonition_node]


def setup(app):
    app.add_config_value("python_version_major", str(sys.version_info.major), "env")
    app.add_directive("legacy", LegacyDirective)


# -----------------------------------------------------------------------------
# HTML output
# -----------------------------------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "logo": {
        "image_light": "_static/logos/eoforestact_logo.png",
        "image_dark": "_static/logos/eoforestact_logo.png",
    },
    "github_url": "https://github.com/simonbesnard1/eoforeststac",
    "collapse_navigation": True,
    "header_links_before_dropdown": 6,
    "navbar_end": ["search-button", "theme-switcher", "navbar-icon-links"],
    "navbar_persistent": [],
    "show_version_warning_banner": True,
}

html_title = "%s v%s Manual" % (project, version)
html_static_path = ["_static"]
html_last_updated_fmt = "%b %d, %Y"
html_css_files = (
    ["eoforeststac.css"] if os.path.exists("_static/eoforeststac.css") else []
)
html_context = {"default_mode": "dark"}
html_use_modindex = True
html_copy_source = False
html_domain_indices = False
html_file_suffix = ".html"

htmlhelp_basename = "eoforeststac-doc"

if "sphinx.ext.pngmath" in extensions:
    pngmath_use_preview = True
    pngmath_dvipng_args = ["-gamma", "1.5", "-D", "96", "-bg", "Transparent"]

copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# -----------------------------------------------------------------------------
# LaTeX output
# -----------------------------------------------------------------------------

latex_engine = "xelatex"

_stdauthor = "Simon Besnard, GFZ Potsdam"
latex_documents = [
    (
        "user/index",
        "eoforeststac-user.tex",
        "EOForestSTAC User Guide",
        _stdauthor,
        "manual",
    ),
]

latex_elements = {
    "preamble": r"""
\makeatletter
\@ifpackagelater{sphinxpackagefootnote}{2022/02/12}
    {}%
    {%
\usepackage{expdlist}
\let\latexdescription=\description
\def\description{\latexdescription{}{} \breaklabel}
\usepackage{etoolbox}
\patchcmd\@item{{\@breaklabel} }{{\@breaklabel}}{}{}
\def\breaklabel{%
    \def\@breaklabel{%
        \leavevmode\par
        \def\leavevmode{\def\leavevmode{\unhbox\voidb@x}}%
    }%
}
    }%
\makeatother
"""
}

latex_use_modindex = False

# -----------------------------------------------------------------------------
# Texinfo output
# -----------------------------------------------------------------------------

texinfo_documents = [
    (
        "index",
        "eoforeststac",
        "eoforeststac Documentation",
        _stdauthor,
        "eoforeststac",
        "EOForestSTAC: Cloud-native access to global forest Earth Observation datasets via STAC and Zarr",
        "Programming",
        1,
    ),
]

# -----------------------------------------------------------------------------
# Intersphinx configuration
# -----------------------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "scipy": ("https://docs.scipy.org/doc/scipy", None),
    "matplotlib": ("https://matplotlib.org/stable", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "xarray": ("https://docs.xarray.dev/en/stable", None),
    "zarr": ("https://zarr.readthedocs.io/en/stable", None),
    "pytest": ("https://docs.pytest.org/en/stable", None),
    "geopandas": ("https://geopandas.org/en/stable", None),
    "pystac": ("https://pystac.readthedocs.io/en/stable", None),
}

# -----------------------------------------------------------------------------
# Autosummary
# -----------------------------------------------------------------------------

autosummary_generate = True

# Mock heavy optional imports so autodoc works without the full environment
autodoc_mock_imports = ["pdal", "tiledb"]

# -----------------------------------------------------------------------------
# Source code links
# -----------------------------------------------------------------------------


def linkcode_resolve(domain, info):
    """Determine the URL corresponding to a Python object in the GitHub repo."""
    if domain != "py":
        return None

    modname = info["module"]
    fullname = info["fullname"]

    submod = sys.modules.get(modname)
    if submod is None:
        return None

    obj = submod
    for part in fullname.split("."):
        try:
            obj = getattr(obj, part)
        except AttributeError:
            return None

    try:
        fn = inspect.getsourcefile(inspect.unwrap(obj))
    except TypeError:
        fn = None
    if not fn:
        return None

    try:
        source, lineno = inspect.getsourcelines(obj)
    except OSError:
        lineno = None

    if lineno:
        linespec = f"#L{lineno}-L{lineno + len(source) - 1}"
    else:
        linespec = ""

    fn = os.path.relpath(fn, start=os.path.dirname(eoforeststac.__file__))

    if "+" in version:
        return f"https://github.com/simonbesnard1/eoforeststac/blob/main/eoforeststac/{fn}{linespec}"
    else:
        return f"https://github.com/simonbesnard1/eoforeststac/blob/v{version}/eoforeststac/{fn}{linespec}"
