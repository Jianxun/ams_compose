# Analog-Hub Development Guidelines

Test-driven development guidelines for the analog-hub dependency management tool, designed for multi-session continuity and consistent development practices.

## Development Workflow

### 1. Session Start Protocol
- Review `context/memory.md` to understand current project state
- Check `context/todo.md` for current sprint tasks and priorities
- Select a specific task from Priority 1 (HIGH) items first
- Use TodoWrite tool to mark selected task as `in_progress`

### 2. Test-Driven Development Cycle
- **Red**: Write failing tests that define expected behavior
- **Green**: Implement minimum code to pass tests
- **Refactor**: Improve code while maintaining test coverage
- Run full test suite after each change

### 3. Analog-Hub Specific Practices
- **Module Structure**: Follow `analog_hub/core/`, `analog_hub/cli/`, `analog_hub/utils/` organization
- **Configuration**: Use Pydantic models for YAML validation
- **Git Operations**: Use GitPython for repository operations
- **CLI Commands**: Use Click framework with descriptive help text
- **Error Handling**: Provide user-friendly error messages for analog IC designers

## Testing Organization

### Test Structure
```
tests/
├── test_config.py          # Configuration parsing and validation
├── test_mirror.py          # Repository mirroring operations  
├── test_extractor.py       # Path extraction and copying
├── test_installer.py       # Installation orchestration
├── cli/
│   ├── test_install.py     # CLI install command
│   ├── test_update.py      # CLI update command
│   └── test_list.py        # CLI list command
└── fixtures/
    ├── sample_configs/     # Test analog-hub.yaml files
    └── mock_repos/         # Test repository structures
```

### Testing Guidelines
- Use pytest with descriptive test names: `test_install_extracts_correct_library_path`
- Mock git operations in unit tests, use real repos in integration tests
- Test both success and failure scenarios for git operations
- Validate generated `.analog-hub-meta.yaml` files in tests
- Test configuration validation with invalid YAML structures

## Code Quality Standards

### Python Standards
- Follow PEP 8 with 88-character line limit (Black formatter)
- Use type hints for all function parameters and return values
- Document classes and functions with Google-style docstrings
- Import organization: standard library, third-party, local modules

### Analog-Hub Conventions
- Use descriptive variable names reflecting analog design context
- Error messages should be helpful for analog IC designers
- Log git operations at appropriate levels (debug for verbose, info for user actions)
- Preserve file permissions when copying analog design files

## Cross-Session Continuity

### Session End Protocol
1. Update TodoWrite tool with completed tasks
2. Update `context/memory.md` with:
   - New architectural decisions
   - Implementation challenges and solutions
   - Performance findings
   - Test results and coverage
3. Commit changes with descriptive messages
4. Mark current task as `completed` in TodoWrite

### Context Documentation
- **Memory**: Record design decisions, git operation findings, performance metrics
- **Todo**: Maintain clear priorities, break down complex tasks into subtasks
- **Implementation Notes**: Document any analog design specific considerations

## Git Operations Testing

### Unit Testing Strategy
- Mock GitPython operations for fast unit tests
- Test error conditions: network failures, invalid refs, missing paths
- Validate mirror directory structure and cleanup
- Test sparse checkout path extraction logic

### Integration Testing Strategy  
- Use real test repositories for end-to-end validation
- Test with various git hosting providers (GitHub, GitLab, self-hosted)
- Validate with actual analog design files (schematics, layouts, models)
- Test branch/tag/commit reference resolution

## Error Handling Guidelines

### User-Facing Errors
- Provide clear guidance for configuration errors
- Suggest fixes for common git operation failures
- Include helpful context for analog designers unfamiliar with git
- Log technical details for debugging while showing user-friendly messages

### Technical Error Handling
- Gracefully handle network timeouts and git server issues
- Clean up partial operations on failure
- Validate file integrity after extraction
- Handle permission issues in analog design file copying

## Task Completion Criteria

### Definition of Done
- [ ] All tests pass (unit and integration)
- [ ] Code coverage maintained or improved
- [ ] Documentation updated (docstrings and context files)
- [ ] CLI help text accurate and helpful
- [ ] Error handling tested with invalid inputs
- [ ] Real analog design repository tested (if applicable)
- [ ] TodoWrite tool updated with task completion
- [ ] Context files updated with findings

### Integration Checklist
- [ ] New module integrates with existing CLI commands
- [ ] Configuration changes validated with Pydantic models
- [ ] Git operations handle edge cases (empty repos, large files)
- [ ] Extracted libraries maintain file structure and permissions

## Performance Considerations

### Git Operations
- Minimize network operations through smart mirroring
- Track and optimize clone/extraction times for large repositories
- Document performance characteristics in context/memory.md
- Consider parallel operations for multiple library installs

### File Operations  
- Preserve analog design file metadata and permissions
- Handle large design files efficiently
- Validate checksums for library integrity
- Clean up temporary directories properly

Remember: The analog-hub tool serves analog IC designers who may not be git experts. Prioritize clear error messages and reliable operations over performance optimizations.