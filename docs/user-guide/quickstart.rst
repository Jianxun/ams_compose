Quick Start Guide
=================

This guide will help you get started with analog-hub in minutes.

Initialize a Project
--------------------

Create a new analog-hub project:

.. code-block:: bash

   mkdir my-analog-project
   cd my-analog-project
   analog-hub init

This creates an ``analog-hub.yaml`` configuration file with sample libraries.

Basic Configuration
-------------------

Edit the ``analog-hub.yaml`` file to specify your library dependencies:

.. code-block:: yaml

   libraries:
     - name: "core_analog"
       url: "https://github.com/example/analog-library.git"
       ref: "v1.0.0"
       paths:
         - "lib/ota_designs"
         - "lib/amplifiers"

     - name: "process_models"
       url: "https://github.com/example/process-lib.git"
       ref: "main"
       paths:
         - "models/sky130"

Install Libraries
-----------------

Install all configured libraries:

.. code-block:: bash

   analog-hub install

This will:

1. Clone the specified repositories
2. Extract the configured paths
3. Install libraries to ``designs/libs/``
4. Create a lockfile to track versions

Working with Libraries
----------------------

List installed libraries:

.. code-block:: bash

   analog-hub list

Update libraries to latest versions:

.. code-block:: bash

   analog-hub update

Validate library integrity:

.. code-block:: bash

   analog-hub validate

Clean up unused mirrors:

.. code-block:: bash

   analog-hub clean

Example Workflow
----------------

Here's a typical workflow for an analog IC design project:

.. code-block:: bash

   # 1. Start a new project
   mkdir analog-amplifier-design
   cd analog-amplifier-design
   analog-hub init

   # 2. Configure libraries (edit analog-hub.yaml)
   # Add your library dependencies

   # 3. Install libraries
   analog-hub install

   # 4. Work on your design using the installed libraries
   # Your design files go in the project root
   # Library files are available in designs/libs/

   # 5. Update libraries when needed
   analog-hub update

   # 6. Validate before important milestones
   analog-hub validate

Next Steps
----------

* Read the :doc:`configuration` guide for advanced configuration options
* See the :doc:`commands` reference for all available commands
* Check out the :doc:`../developer/architecture` for understanding how analog-hub works