# GitHub Templates for Eiro Inc. QMS

These templates integrate GitHub with the Eiro Inc. Quality Management System per SOP-004 (Software Development Lifecycle).

## Template Descriptions

### Issue Templates

| Template | Purpose | SOP Reference |
|----------|---------|---------------|
| **Software Requirement** | Document traceable requirements | SOP-004 §5.3 |
| **Design Change Request** | Request changes to approved design | SOP-002 §5.8 |
| **Bug Report** | Report software defects | SOP-004 §5.10 |
| **Feature Request** | Suggest new features | - |

### Pull Request Template

The PR template includes checklists for:
- Code quality per coding standards
- Security per SOP-011
- Testing per SOP-004
- Traceability to requirements

## Usage in QMS Workflow

### Creating Requirements
1. Create a new issue using "Software Requirement" template
2. GitHub issue number becomes the requirement ID (e.g., REQ-#42)
3. Link to User Need from DHF-001-001
4. Update Traceability Matrix when requirement is approved

### Tracking Design Changes
1. Create issue using "Design Change Request" template
2. Complete impact assessment fields
3. Obtain required approvals (comments or PR approval)
4. Link to implementing PR(s)

### Reporting Bugs
1. Create issue using "Bug Report" template
2. For Critical/High severity: also complete formal SPR form (SOP-004-ATTACH-C)
3. Link fix PR to bug issue using "Closes #XX"

### Code Review
1. Create PR using the PR template
2. Link to requirement/bug issue
3. Complete checklist
4. For safety-critical code: request Quality Representative review
5. Use Code Review Checklist (SOP-004-ATTACH-B) for formal reviews

## Traceability

GitHub provides automatic traceability through:
- Issue linking (`Closes #123`, `Relates to #456`)
- PR to issue linking
- Commit messages referencing issues (`Fixes #123`)

Export this data periodically to update the formal Traceability Matrix in the DHF.
