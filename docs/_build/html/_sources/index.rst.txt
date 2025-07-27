analog-hub Documentation
========================

**analog-hub** is a dependency management tool designed specifically for analog IC design repositories. 
It provides efficient management of design libraries, schematics, layouts, and other analog design files across distributed repositories.

.. toctree::
   :maxdepth: 2
   :caption: User Guide:
   
   user-guide/installation
   user-guide/quickstart
   user-guide/configuration
   user-guide/commands

.. toctree::
   :maxdepth: 2
   :caption: API Reference:
   
   api/analog_hub

.. toctree::
   :maxdepth: 1
   :caption: Developer Guide:
   
   developer/contributing
   developer/architecture
   developer/testing

Key Features
============

* **Smart Library Management**: Efficient extraction and installation of analog design libraries
* **Git Integration**: Seamless integration with Git repositories for version control
* **Branch/Tag Support**: Install libraries from specific branches, tags, or commits
* **Path-based Extraction**: Extract only the needed design files from repositories
* **Lockfile Management**: Track installed libraries and their versions
* **Analog IC Focus**: Optimized for analog design workflows and file types

Quick Start
===========

Install analog-hub:

.. code-block:: bash

   pip install analog-hub

Initialize a project:

.. code-block:: bash

   analog-hub init

Install libraries:

.. code-block:: bash

   analog-hub install

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

