# AMS-Compose Documentation

This directory contains the Sphinx documentation for AMS-Compose.

## Building Documentation

To build the HTML documentation:

```bash
cd docs
sphinx-build -b html . _build/html
```

Or use the Makefile:

```bash
cd docs
make html
```

The built documentation will be available in `_build/html/index.html`.

## Documentation Structure

The documentation is organized into the following sections:

- **Getting Started**: Installation, quick start, and basic configuration
- **User Guide**: Core concepts, library management, supply chain features
- **CLI Reference**: Command-line interface documentation
- **Configuration**: File formats and configuration options
- **Examples**: Real-world usage examples for analog design workflows
- **Architecture**: System design and implementation details
- **API Reference**: Python API documentation (auto-generated)
- **Developer Guide**: Contributing, testing, and development practices
- **Reference**: Troubleshooting, FAQ, changelog, and license

## Documentation Status

🚧 **This is a documentation scaffold** - All sections contain placeholder content that needs to be written in future sessions.

The structure provides a comprehensive framework for documenting:
- User-facing features and workflows
- Technical implementation details
- Development practices and architecture decisions
- Real-world examples for analog IC design teams

## Configuration

The documentation uses:
- **Sphinx** with Read the Docs theme
- **MyST Parser** for Markdown support
- **Napoleon** for Google-style docstrings
- **Autodoc** for automatic API documentation generation

See `conf.py` for detailed configuration.