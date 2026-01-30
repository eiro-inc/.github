# Software Development Lifecycle Guide

> **Official Document**: This guide summarizes [SOP-004: Software Development Lifecycle](https://drive.google.com/drive/folders/YOUR_QMS_FOLDER) maintained in the Eiro QMS on Google Drive. For audit purposes, always reference the controlled `.docx` version.

## Overview

This guide establishes software development lifecycle (SDLC) processes for Eiro Pathways and other Software as a Medical Device (SaMD) products in compliance with IEC 62304 and FDA regulatory requirements.

**Effective Date**: February 2, 2026
**Classification**: FDA Regulated | IEC 62304 Compliant | De Novo Ready

---

## Quick Reference

### Software Safety Classification

| Class | Description | Code Coverage | Safety-Critical Paths |
|-------|-------------|---------------|----------------------|
| **Class A** | No direct safety impact | Basic testing | N/A |
| **Class B** | Indirect safety impact | 80% minimum | 100% |
| **Class C** | Direct safety impact | 90% minimum | 100% |

**Eiro Pathways Classification**: Class B

---

## GitHub Workflow

### Branch Strategy

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Production releases only | Protected |
| `develop` | Development integration | Protected |
| `feature/[issue-number]` | Feature development | — |
| `hotfix/[issue-number]` | Critical fixes | — |
| `release/[version]` | Release preparation | — |

### Protected Branch Rules (main & develop)

- ✅ Require pull request reviews before merge
- ✅ Require status checks to pass (unit tests, coverage, linting)
- ✅ Require branches to be up to date
- ✅ Dismiss stale PR approvals

### Issue Labels

| Label | Purpose |
|-------|---------|
| `requirement` | Software requirement |
| `bug` | Defect found in testing or field |
| `critical-defect` | Critical defect needing immediate fix |
| `safety-critical` | Affects patient safety |
| `AI/ML` | AI/ML related changes |
| `problem-report` | Field anomaly reported via SPR |

### Pull Request Workflow

1. Create PR for every code change
2. Link PR to GitHub Issue (requirement or bug)
3. Complete code review (minimum 1 reviewer)
4. All CI checks must pass (tests, coverage, linting)
5. Obtain approval before merge to protected branches

### Releases

- Use GitHub Releases with semantic versioning (v1.0.0, v1.0.1, etc.)
- Include release notes documenting features and fixes
- Archive release documentation in Design History File

---

## Code Review Checklist

When reviewing PRs, verify:

**Code Quality**
- [ ] Code follows project coding standards
- [ ] No unnecessary complexity
- [ ] Appropriate error handling
- [ ] No hardcoded values that should be configurable

**Functionality**
- [ ] Implements requirements correctly
- [ ] Edge cases handled
- [ ] No regressions introduced

**Testing**
- [ ] Unit tests added/updated
- [ ] Code coverage meets class requirements (80% Class B)
- [ ] Safety-critical paths have 100% coverage

**Documentation & Traceability**
- [ ] PR links to GitHub Issue
- [ ] Comments explain non-obvious logic
- [ ] API changes documented

**Security**
- [ ] No sensitive data exposed
- [ ] Input validation present
- [ ] Dependencies are approved SOUP

For the full checklist, use [SOP-004-ATTACH-B: Code Review Checklist](https://drive.google.com/drive/folders/YOUR_QMS_FOLDER) from the QMS.

---

## Design History File Structure

All project artifacts must be organized in the QMS Design History File:

```
QMS/04_Design_History_File/[Project]/
├── Software_Development_Plan/
│   └── SDP_v[version].docx
├── Software_Requirements/
│   ├── Requirements_Specification.docx
│   └── RTM_Software_Requirements.xlsx
├── Software_Architectural_Design/
│   ├── Architecture_Design_Document.docx
│   └── [Architecture diagrams]
├── Software_Detailed_Design/
│   ├── Software_Design_Specification.docx
│   └── [Component designs]
├── Coding_Standards/
│   └── Coding_Standards_Guidelines.docx
├── Verification/
│   ├── Unit_Testing/
│   ├── Integration_Testing/
│   └── System_Testing/
├── Design_Reviews/
│   └── [Review minutes and checklists]
├── Release_v[version]/
│   ├── Release_Notes.docx
│   ├── Release_Approval_Record.pdf
│   ├── Final_Test_Report.docx
│   └── Final_RTM.xlsx
├── Software_Maintenance/
│   └── Problem_Reports/
├── SOUP_Management/
│   ├── SOUP_Inventory.xlsx
│   └── [Evaluation forms]
└── Configuration_Management/
    └── [Build and CI/CD records]
```

---

## SOUP (Third-Party Software) Management

Before adding any third-party library or framework:

1. **Check if already approved** — See SOUP Inventory in QMS
2. **If new**, complete [SOP-004-ATTACH-D: SOUP Evaluation Form](https://drive.google.com/drive/folders/YOUR_QMS_FOLDER)
3. **Evaluation criteria**:
   - License compatibility (watch for GPL/copyleft)
   - Security track record
   - Maintenance and community support
   - Performance impact
4. **Get approval** before adding to project
5. **Pin versions** — No floating version numbers
6. **Monitor for vulnerabilities** — Subscribe to security advisories

---

## AI/ML Development Requirements

For AI/ML components (applies to Eiro Pathways):

### Documentation Required
- Model type and architecture
- Training data requirements and sources
- Feature selection and preprocessing steps
- Validation strategy
- Performance metrics (accuracy, sensitivity, specificity, AUC)
- Re-training procedures

### Testing Requirements
- Model accuracy and performance validation
- Fairness testing across demographic groups
- Robustness testing (edge cases, adversarial examples)
- Bias detection and mitigation documentation

### SOUP Considerations
ML frameworks (TensorFlow, PyTorch, scikit-learn, etc.) must be evaluated as SOUP.

---

## Problem Reporting

When you discover a software defect:

1. **Create GitHub Issue** with `bug` label (add `critical-defect` if severe)
2. **For field issues**, also complete [SOP-004-ATTACH-C: Software Problem Report](https://drive.google.com/drive/folders/YOUR_QMS_FOLDER)
3. **Severity levels**:
   - **Critical**: Patient safety impact or system unusable
   - **High**: Major feature broken, no workaround
   - **Medium**: Feature impaired, workaround exists
   - **Low**: Minor issue, cosmetic

---

## Records Retention

All software development records must be retained for **7 years** (5-year device life + 2 years).

Records include:
- GitHub repository history (indefinite)
- Pull requests and code reviews
- Test results and coverage reports
- Design review minutes
- Release documentation
- Problem reports

---

## Implementation Checklist

### Phase 1: Project Setup
- [ ] Create GitHub repository under `eiro-inc`
- [ ] Configure branch protection rules
- [ ] Set up CI/CD pipeline (tests, coverage, linting)
- [ ] Create DHF folder structure in QMS

### Phase 2: Development
- [ ] Complete Software Development Plan
- [ ] Perform safety classification (use Attachment A)
- [ ] Document requirements as GitHub Issues
- [ ] Maintain Requirements Traceability Matrix
- [ ] Conduct code reviews (use Attachment B checklist)
- [ ] Document SOUP components (use Attachment D)

### Phase 3: Release
- [ ] Complete system testing (100% requirement coverage)
- [ ] Conduct design review
- [ ] Prepare release documentation
- [ ] Obtain release approval signatures
- [ ] Create GitHub Release with semantic version tag
- [ ] Archive all records in DHF

---

## FDA Audit Readiness

### Key Evidence to Maintain

| Evidence | Location |
|----------|----------|
| Software Development Plan | QMS DHF |
| Safety Classification | QMS DHF (Attachment A) |
| Requirements Traceability | QMS DHF + GitHub Issues |
| Code Reviews | GitHub PRs + Attachment B |
| Test Results | CI/CD logs + QMS DHF |
| SOUP Inventory | QMS DHF (Attachment D) |
| Problem Reports | GitHub Issues + Attachment C |
| Release Approvals | QMS DHF |

### Exporting GitHub Evidence for Audit

```bash
# Export issues
gh issue list --repo eiro-inc/[repo] --state all --json number,title,labels,state,createdAt,closedAt > issues.json

# Export PRs
gh pr list --repo eiro-inc/[repo] --state all --json number,title,state,mergedAt,reviews > prs.json

# Export releases
gh release list --repo eiro-inc/[repo] > releases.txt
```

---

## Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| SOP-004 (full) | QMS Google Drive | Official controlled procedure |
| Attachment A | QMS Google Drive | Safety Classification Worksheet |
| Attachment B | QMS Google Drive | Code Review Checklist |
| Attachment C | QMS Google Drive | Software Problem Report |
| Attachment D | QMS Google Drive | SOUP Evaluation Form |
| SOP-001 | QMS Google Drive | Document Control |
| SOP-002 | QMS Google Drive | Design Control |
| SOP-003 | QMS Google Drive | Risk Management |

---

## Questions?

- **Quality/Regulatory**: Contact Quality Management
- **GitHub/Technical**: Contact Development Team Lead
- **AI/ML**: Contact AI/ML Subject Matter Expert

---

*This guide is maintained alongside the official SOP-004 in the Eiro QMS. Last updated: February 2, 2026*
