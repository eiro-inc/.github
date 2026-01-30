# GitHub Templates for Eiro Inc. QMS

These templates integrate GitHub with the Eiro Inc. Quality Management System per SOP-004 (Software Development Lifecycle).

## Setup Instructions

### 1. Copy Templates to Your Repository

Copy the entire `.github` folder to the root of your Eiro Pathways repository:

```bash
cp -r .github /path/to/eiro-pathways-repo/
```

### 2. Update Configuration

Edit `.github/ISSUE_TEMPLATE/config.yml` and replace `[repo-name]` with your actual repository name.

### 3. Create Labels

You can create labels manually in GitHub (Settings → Labels), or use the GitHub CLI:

```bash
# Install gh CLI if needed: https://cli.github.com/

# Create labels from the labels.yml file
gh label create "requirement" --description "Software requirement for traceability" --color "0052CC"
gh label create "bug" --description "Software defect or anomaly" --color "D73A4A"
gh label create "enhancement" --description "New feature or enhancement request" --color "A2EEEF"
gh label create "design-change" --description "Design change request per SOP-002" --color "7057FF"
gh label create "safety-critical" --description "Safety-critical functionality (Class B/C)" --color "B60205"
gh label create "AI/ML" --description "Related to AI/ML algorithm or model" --color "5319E7"
gh label create "security" --description "Security-related" --color "D93F0B"
gh label create "priority: critical" --description "Critical priority" --color "B60205"
gh label create "priority: high" --description "High priority" --color "D93F0B"
gh label create "priority: medium" --description "Medium priority" --color "FBCA04"
gh label create "priority: low" --description "Low priority" --color "0E8A16"
gh label create "regulatory-impact" --description "May have regulatory implications" --color "C2E0C6"
gh label create "CAPA" --description "Related to CAPA" --color "F9D0C4"
gh label create "needs-test" --description "Requires test case" --color "C5DEF5"
```

### 4. Configure Branch Protection (Recommended)

In GitHub repository settings (Settings → Branches → Add rule):

**For `main` branch:**
- Require pull request reviews before merging (1 reviewer minimum)
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Include administrators

**For `develop` branch:**
- Require pull request reviews before merging (1 reviewer minimum)
- Require status checks to pass before merging

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
