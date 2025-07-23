# Todo List

## Next Session - Implementation Phase 1

### Priority 1: Project Setup
- [ ] Create Python package structure
- [ ] Set up pyproject.toml with dependencies
- [ ] Initialize git repository
- [ ] Create basic module files and __init__.py

### Priority 2: Core Models  
- [ ] Implement Pydantic models in core/config.py
- [ ] Add license fields to ExportSpec and LockEntry models
- [ ] Add YAML parsing and validation
- [ ] Create lockfile data structures with license snapshots
- [ ] Add configuration file discovery logic

### Priority 3: Git Operations
- [ ] Implement sparse checkout in core/git_ops.py
- [ ] Add ref resolution (branch/tag/commit to hash)
- [ ] Create provider config fetching
- [ ] Add error handling for git operations

### Priority 4: Installation Logic
- [ ] Implement single library installation
- [ ] Add license extraction and validation
- [ ] Add lockfile creation and updates with license snapshots
- [ ] Create library directory management
- [ ] Add checksum verification
- [ ] Implement license change detection on updates

## Phase 2 - CLI and Advanced Features
- [ ] Implement Click CLI commands (including --licenses flag)
- [ ] Add license change warnings and --allow-license-change flag
- [ ] Add comprehensive error handling
- [ ] Create test suite
- [ ] Add logging and debugging
- [ ] Plan multi-file config transition (.analog-hub/ directory)
- [ ] Write user documentation

## Completed - Planning Phase
- [x] Define project scope and core problems
- [x] Design analog-hub.yaml configuration format
- [x] Choose technology stack (Python, Pydantic, Click, GitPython)  
- [x] Design git sparse checkout strategy
- [x] Plan update workflow with fresh clone approach
- [x] Design core module architecture
- [x] Document all design decisions