Installation Guide
==================

Requirements
------------

* Python 3.8 or higher
* Git (for repository operations)

Installation Methods
--------------------

From PyPI (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install analog-hub

From Source
~~~~~~~~~~~

For development or latest features:

.. code-block:: bash

   git clone https://github.com/Jianxun/analog-hub.git
   cd analog-hub
   pip install -e .

Development Installation
~~~~~~~~~~~~~~~~~~~~~~~~

For contributing to analog-hub:

.. code-block:: bash

   git clone https://github.com/Jianxun/analog-hub.git
   cd analog-hub
   pip install -e ".[dev]"

This installs analog-hub in editable mode with development dependencies including:

* pytest (testing framework)
* black (code formatter)
* mypy (type checker)
* flake8 (linter)

Verification
------------

Verify the installation by running:

.. code-block:: bash

   analog-hub --version

You should see the version number displayed.

Dependencies
------------

analog-hub requires the following packages:

* **GitPython**: For Git repository operations
* **pydantic**: For configuration validation
* **click**: For command-line interface
* **PyYAML**: For YAML configuration parsing

These dependencies are automatically installed when you install analog-hub.