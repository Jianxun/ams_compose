Configuration Guide
===================

analog-hub uses a YAML configuration file to define library dependencies and project settings.

Configuration File Structure
-----------------------------

The ``analog-hub.yaml`` file defines your project's library dependencies:

.. code-block:: yaml

   libraries:
     - name: "library_name"
       url: "repository_url"
       ref: "version_reference"
       paths:
         - "path/to/extract"

Library Configuration
---------------------

Each library entry supports the following fields:

name
~~~~
**Required.** A unique identifier for the library.

.. code-block:: yaml

   name: "core_analog_lib"

url
~~~
**Required.** The Git repository URL for the library.

.. code-block:: yaml

   url: "https://github.com/example/analog-library.git"
   # or
   url: "git@github.com:example/analog-library.git"

ref
~~~
**Optional.** The Git reference to install (branch, tag, or commit SHA). Defaults to ``main``.

.. code-block:: yaml

   ref: "v1.2.3"        # Tag
   ref: "main"          # Branch  
   ref: "develop"       # Branch
   ref: "abc123def"     # Commit SHA

paths
~~~~~
**Required.** List of paths to extract from the repository.

.. code-block:: yaml

   paths:
     - "lib/amplifiers"
     - "lib/filters"
     - "models/sky130"

Configuration Examples
----------------------

Basic Library
~~~~~~~~~~~~~

.. code-block:: yaml

   libraries:
     - name: "basic_lib"
       url: "https://github.com/example/basic-lib.git"
       paths:
         - "lib"

Multiple Paths
~~~~~~~~~~~~~~

.. code-block:: yaml

   libraries:
     - name: "comprehensive_lib"
       url: "https://github.com/example/big-lib.git"
       ref: "v2.0.0"
       paths:
         - "analog/amplifiers"
         - "analog/filters"
         - "digital/gates"
         - "models"

Development Branch
~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   libraries:
     - name: "experimental_lib"
       url: "https://github.com/example/experimental.git"
       ref: "feature/new-designs"
       paths:
         - "experimental"

Specific Commit
~~~~~~~~~~~~~~~

.. code-block:: yaml

   libraries:
     - name: "stable_lib"
       url: "https://github.com/example/stable.git"
       ref: "a1b2c3d4e5f6"
       paths:
         - "stable_designs"

Best Practices
--------------

Version Pinning
~~~~~~~~~~~~~~~

Pin important libraries to specific versions for reproducible builds:

.. code-block:: yaml

   libraries:
     - name: "production_lib"
       url: "https://github.com/company/production-lib.git"
       ref: "v1.0.0"  # Pinned version
       paths:
         - "lib"

Path Organization
~~~~~~~~~~~~~~~~~

Use specific paths to avoid unnecessary files:

.. code-block:: yaml

   # Good: Specific paths
   paths:
     - "lib/amplifiers/ota"
     - "lib/amplifiers/diffamp"
   
   # Avoid: Too broad
   paths:
     - "."  # Entire repository

Naming Conventions
~~~~~~~~~~~~~~~~~~

Use descriptive library names:

.. code-block:: yaml

   # Good
   name: "sky130_analog_lib"
   name: "company_ota_designs"
   
   # Avoid
   name: "lib1"
   name: "stuff"

Configuration Validation
-------------------------

analog-hub validates your configuration file and provides helpful error messages:

.. code-block:: bash

   analog-hub validate

Common validation errors:

* **Missing required fields**: ``name``, ``url``, or ``paths`` not specified
* **Invalid URL format**: Repository URL is not a valid Git URL
* **Duplicate names**: Multiple libraries with the same name
* **Empty paths**: No paths specified or paths list is empty

Environment Variables
---------------------

You can use environment variables in your configuration:

.. code-block:: yaml

   libraries:
     - name: "private_lib"
       url: "${PRIVATE_REPO_URL}"
       ref: "${LIBRARY_VERSION:-main}"
       paths:
         - "lib"

This allows for flexible configuration across different environments.