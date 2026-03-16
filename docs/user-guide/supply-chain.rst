Supply Chain Management
=======================

.. note::
   This section is a placeholder for future content.

Two-Tier Dependency Model
--------------------------

*[To be documented: checkin=true vs checkin=false libraries]*

.gitignore Integration
----------------------

*[To be documented: Automatic version control exclusion]*

License Tracking
----------------

*[To be documented: License detection and compliance monitoring]*

Library Metadata
----------------

Each extracted library directory includes a provenance sidecar file named
``.ams-compose-metadata.yaml``. This file captures stable origin details
(``repository``, ``reference``, ``commit``, ``source_path``) and license context.

To reduce version-control churn, metadata is deterministic and excludes volatile
timestamp fields.
