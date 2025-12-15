# Documentation Guidelines

## Documentation Structure
- `README.md` (root) - User-facing quick start and overview
- `README.man1.md` - CLI reference (command-line usage)
- `README.man3.md` - Python API reference (programmatic usage)
- `README.man4.md` - KiCad plugin integration guide
- `README.man5.md` - Inventory file format specification
- `README.developer.md` - Technical architecture and extension points
- `README.tests.md` - Test suite documentation

## Writing Standards
- Use "jBOM" consistently (not JBOM, jbom, or j-BOM)
- Include "SEE ALSO" sections with markdown links between related docs
- Man page style formatting for technical references (man1, man3, etc.)
- Concise prose preferred over long bullet lists
- Include concrete examples and code snippets

## Update Requirements
- Update relevant README files when adding/changing functionality
- Keep CHANGELOG.md current (automated by semantic-release)
- Maintain cross-references between documentation files
- Verify examples and code snippets remain accurate
