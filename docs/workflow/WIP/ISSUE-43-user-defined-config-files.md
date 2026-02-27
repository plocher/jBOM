# Issue #43: User-Defined Config Files with Hierarchy

## Problem Statement

Currently, jBOM only uses built-in fabricator configuration files. Users cannot:
- Override built-in configurations
- Add custom fabricator definitions
- Use project-specific configurations
- Maintain organization-specific config hierarchies

## Requirements

### Config File Hierarchy (Search Order)
1. **Environment Variable**: `JBOM_CONFIG_DIR` (if set)
2. **Project Directory**: `.jbom/fabricators/` in current working directory
3. **Git Repo Root**: `.jbom/fabricators/` in repository root (if in git repo)
4. **User Home**: `~/.jbom/fabricators/`
5. **Built-in Fallback**: Built-in configurations in source tree

### User Config Capabilities
- **Custom Fabricators**: Define new fabricator configurations
- **Override Built-ins**: Override specific aspects of built-in configurations
- **Extend Configurations**: Add new fields/presets to existing fabricators
- **Project-Specific**: Per-project fabricator customizations
- **Organization Configs**: Team/company-wide configuration sharing via `JBOM_CONFIG_DIR`

### Config File Format
- Same YAML format as built-in `.fab.yaml` files
- Support for partial overrides (merge with built-in configs)
- Validation of user-defined configurations

## Implementation Notes

### BDD Test Integration
- Tests should be able to create temporary configs in sandbox
- Test fabricator configs should be discoverable via the hierarchy
- Should not pollute source tree with test configurations

### Legacy jBOM Compatibility
- Legacy jBOM had some user config support - research and leverage lessons learned
- Maintain backward compatibility where possible

## Acceptance Criteria

- [ ] Config hierarchy search implemented and documented
- [ ] Users can create custom fabricator definitions
- [ ] Users can override built-in configurations
- [ ] `JBOM_CONFIG_DIR` environment variable support
- [ ] Project-local `.jbom/fabricators/` directory support
- [ ] BDD tests can use sandbox configurations
- [ ] Config validation and error handling
- [ ] Documentation and examples for user configs

## Dependencies

- Should be implemented after Issue #42 (field system) is complete
- Will improve BDD test robustness by enabling scenario-specific configs

## Related Issues

- Issue #42: Fabricator Field System (prerequisite)
- Future: Organization config templates/sharing
