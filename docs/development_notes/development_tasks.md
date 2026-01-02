## Expectations

You are a detail oriented and organized collaborator who is helping me develop an open source utility application that will be used by electrical engineers as they create electronic projects using the KiCad electronic design CAD package.

jBOM is a github/pypi project that utilizes a PR-based feature branch methodology with semantic git commits.

The project favors a Behavioral- and test-driven development process (BDD with TDD).  You will find extensive gherkin tests in ./features/* as well as unit tests in ./tests/*

Agent notes can be found in WARP.md files in many folders.

## Problem
- jBOM has evolved somewhat organically and haphazardly, and has not followed Behavioral- and test-based development practices consistently.
- We have created a solid functional test environment using gherkin and behave to capture an initial set of requirements.
- Those functional tests now exist, but all of them are placeholders whose step definitions don't actually do anything.
## Goal
- `Definition of Done`: each feature in ./features/(domain)/* successfully executes its corresponding step definitions found in ./features/steps/(domain)/*

## Tasks
### 1. Review the jBOM artifacts
Gain a deep and broad understanding of the jBOM project by
- using the information in the WARP.md files in each folder to set baseline expectations,
- using the information on README.md and docs/README.man*.md for an understanding of the current functionality, and
- using the code base in src/* for the current implementation.
- review the (possibly out of date) historical requirements.* documents
- notice the three jBOM usage models:  CLI, Python API and KiCad Add-on package integration
- notice the modular nature of the current implementation
- notice the poc/* exploration into adding an extended inventory search for distributors as an example of future directions
When complete, continue on to task 2
### 2. Develop a plan to achieve the above goal
- This effort involves the evolution of each step definition into a working artifact
- we may find that these of these initial placeholder feature tests are incomplete, misguided or even wrong.  We will fix them.
- This project will require a balance of step logic creation and iterative test refinement
- offer suggestions on ways to improve this plan if you identify better ways of solving this problem.
- present a plan of action with sufficiently detailed task list to show that the scope of work is well understood.
- do not embark on executing the plan until after I have reviewed your plan.
### 3. execute the plan
- Development expectations
    - All project development activities shall use git branching, semantic commits, github Pull Request and ci/cd release flow best practices.
    - Commit Messages MUST follow **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`, etc.) to trigger automated semantic versioning.
    - Use **single quotes** for commit messages to avoid shell expansion issues (especially with `!`).
    - This repo uses pre-commit hooks (flake8, etc.). If a hook modifies a file, you must `git add` the file again and retry the commit.
    - Use `git mv`, `git rm`, `git add` to track changes properly.
