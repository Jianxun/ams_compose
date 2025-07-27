Command Reference
=================

analog-hub provides several commands for managing analog design libraries.

Global Options
--------------

All commands support these global options:

.. code-block:: bash

   --help          Show help message
   --version       Show version information
   --verbose, -v   Enable verbose output
   --quiet, -q     Suppress output

Commands Overview
-----------------

.. code-block:: bash

   analog-hub init      # Initialize a new project
   analog-hub install   # Install all libraries
   analog-hub update    # Update libraries to latest versions
   analog-hub list      # List installed libraries
   analog-hub validate  # Validate library integrity
   analog-hub clean     # Clean up unused files

init
----

Initialize a new analog-hub project with a sample configuration file.

.. code-block:: bash

   analog-hub init [OPTIONS]

**Options:**

* ``--force, -f``: Overwrite existing configuration file

**Examples:**

.. code-block:: bash

   # Initialize new project
   analog-hub init
   
   # Force overwrite existing config
   analog-hub init --force

**Output:**

Creates ``analog-hub.yaml`` with sample library configuration.

install
-------

Install all libraries defined in the configuration file.

.. code-block:: bash

   analog-hub install [OPTIONS]

**Options:**

* ``--force, -f``: Force reinstallation even if library is up-to-date
* ``--library, -l LIBRARY``: Install only the specified library

**Examples:**

.. code-block:: bash

   # Install all libraries
   analog-hub install
   
   # Force reinstall all libraries
   analog-hub install --force
   
   # Install specific library
   analog-hub install --library core_analog

**Behavior:**

1. Reads ``analog-hub.yaml`` configuration
2. Creates mirrors in ``.mirror/`` directory
3. Extracts specified paths to ``designs/libs/``
4. Updates ``.analog-hub.lock`` lockfile

update
------

Update libraries to their latest versions according to the configuration.

.. code-block:: bash

   analog-hub update [OPTIONS]

**Options:**

* ``--library, -l LIBRARY``: Update only the specified library
* ``--dry-run``: Show what would be updated without making changes

**Examples:**

.. code-block:: bash

   # Update all libraries
   analog-hub update
   
   # Update specific library
   analog-hub update --library core_analog
   
   # Check what would be updated
   analog-hub update --dry-run

**Behavior:**

1. Fetches latest changes from remote repositories
2. Updates libraries that have new commits
3. Preserves libraries that are already up-to-date
4. Updates lockfile with new versions

list
----

Display information about installed libraries.

.. code-block:: bash

   analog-hub list [OPTIONS]

**Options:**

* ``--format FORMAT``: Output format (``table``, ``json``, ``yaml``)
* ``--installed-only``: Show only installed libraries
* ``--outdated``: Show only libraries with available updates

**Examples:**

.. code-block:: bash

   # List all libraries
   analog-hub list
   
   # Show as JSON
   analog-hub list --format json
   
   # Show only outdated libraries
   analog-hub list --outdated

**Output:**

.. code-block:: text

   Library Name    | Status    | Version      | Path
   ----------------|-----------|--------------|------------------
   core_analog     | Installed | a1b2c3d      | designs/libs/core_analog
   process_models  | Outdated  | x9y8z7w      | designs/libs/process_models

validate
--------

Validate the integrity of installed libraries.

.. code-block:: bash

   analog-hub validate [OPTIONS]

**Options:**

* ``--library, -l LIBRARY``: Validate only the specified library
* ``--fix``: Attempt to fix validation errors

**Examples:**

.. code-block:: bash

   # Validate all libraries
   analog-hub validate
   
   # Validate specific library
   analog-hub validate --library core_analog
   
   # Validate and fix issues
   analog-hub validate --fix

**Validation Checks:**

* Library directories exist
* Files match expected checksums
* Lockfile consistency
* Configuration file validity

clean
-----

Clean up unused mirror directories and temporary files.

.. code-block:: bash

   analog-hub clean [OPTIONS]

**Options:**

* ``--mirrors``: Clean only mirror directories
* ``--dry-run``: Show what would be cleaned without removing files
* ``--force, -f``: Skip confirmation prompts

**Examples:**

.. code-block:: bash

   # Clean all unused files
   analog-hub clean
   
   # Clean only mirrors
   analog-hub clean --mirrors
   
   # Preview cleanup without removing files
   analog-hub clean --dry-run

**Behavior:**

1. Identifies unused mirror directories
2. Removes temporary extraction files
3. Cleans up orphaned lockfile entries

Exit Codes
----------

analog-hub commands return standard exit codes:

* ``0``: Success
* ``1``: General error
* ``2``: Configuration error
* ``3``: Git operation error
* ``4``: File system error

Error Handling
--------------

analog-hub provides detailed error messages and suggests solutions:

.. code-block:: text

   Error: Library 'missing_lib' not found in configuration
   Suggestion: Add the library to analog-hub.yaml or check the library name

   Error: Git repository not accessible: https://github.com/private/repo.git
   Suggestion: Check your Git credentials and repository permissions

Common Error Messages:

* **Configuration not found**: Run ``analog-hub init`` to create configuration
* **Invalid Git reference**: Check that the specified branch/tag/commit exists
* **Permission denied**: Verify Git credentials and repository access
* **Network error**: Check internet connection and repository availability