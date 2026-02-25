---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: [QUICK-01]

must_haves:
  truths:
    - "E:/Nextcloud-Yeni/TonbilAiFirevallv5 directory exists with full project structure"
    - "All source files (frontend/src, backend/app, config, deploy, docs) are present in the new directory"
    - "Build artifacts (node_modules, dist, __pycache__, .git) are NOT copied"
    - "New directory has a fresh git repo initialized"
  artifacts:
    - path: "E:/Nextcloud-Yeni/TonbilAiFirevallv5/frontend/src/App.tsx"
      provides: "Frontend entry point copied"
    - path: "E:/Nextcloud-Yeni/TonbilAiFirevallv5/backend/app/main.py"
      provides: "Backend entry point copied"
    - path: "E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md"
      provides: "Project instructions copied"
    - path: "E:/Nextcloud-Yeni/TonbilAiFirevallv5/.git"
      provides: "Fresh git repository"
  key_links: []
---

<objective>
Copy the entire TonbilAiFirewallV41 project to a new directory named TonbilAiFirevallv5 at E:/Nextcloud-Yeni/TonbilAiFirevallv5.

Purpose: Create a clean v5 copy of the project for continued development, free from old git history and build artifacts.
Output: A complete project directory at E:/Nextcloud-Yeni/TonbilAiFirevallv5 with all source files, ready for development.
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
Source: E:/Nextcloud-Yeni/TonbilAiFirewallV41
Target: E:/Nextcloud-Yeni/TonbilAiFirevallv5

The source project contains:
- frontend/ (React 18 + TypeScript + Vite, ~154MB with node_modules)
- backend/ (Python/FastAPI, ~1.7MB)
- config/, deploy/, docs/ (supporting directories)
- CLAUDE.md, README.md, setup.sh, .env.example, .gitignore
- .planning/ directory (GSD planning state)
- frontend/node_modules/ (~151MB - EXCLUDE)
- frontend/dist/ (~1.3MB - EXCLUDE, build output)
- .git/ (old git history - EXCLUDE)

Exclusions based on .gitignore: node_modules/, dist/, __pycache__/, .env, .venv/, *.pyc, .vscode/, .idea/, *.log, .DS_Store
</context>

<tasks>

<task type="auto">
  <name>Task 1: Copy project to TonbilAiFirevallv5 excluding build artifacts</name>
  <files>E:/Nextcloud-Yeni/TonbilAiFirevallv5/</files>
  <action>
    Use robocopy (Windows) or equivalent to copy the entire TonbilAiFirewallV41 project to E:/Nextcloud-Yeni/TonbilAiFirevallv5 with the following exclusions:

    EXCLUDE directories:
    - node_modules
    - dist
    - .git
    - __pycache__
    - .venv
    - venv
    - .vscode
    - .idea
    - .planning (old planning state, not relevant for v5)
    - logs

    EXCLUDE files:
    - .env
    - .env.local
    - .env.production
    - *.pyc
    - *.pyo
    - *.log
    - *.pid
    - *.sock

    Command approach:
    ```bash
    robocopy "E:/Nextcloud-Yeni/TonbilAiFirewallV41" "E:/Nextcloud-Yeni/TonbilAiFirevallv5" /E /XD node_modules dist .git __pycache__ .venv venv .vscode .idea .planning logs /XF .env .env.local .env.production *.pyc *.pyo *.log *.pid *.sock
    ```

    After copy, verify the directory structure is complete by listing key directories.
  </action>
  <verify>
    <automated>ls "E:/Nextcloud-Yeni/TonbilAiFirevallv5/frontend/src/App.tsx" && ls "E:/Nextcloud-Yeni/TonbilAiFirevallv5/backend/app/main.py" && ls "E:/Nextcloud-Yeni/TonbilAiFirevallv5/CLAUDE.md" && test ! -d "E:/Nextcloud-Yeni/TonbilAiFirevallv5/node_modules" && test ! -d "E:/Nextcloud-Yeni/TonbilAiFirevallv5/.git" && echo "PASS: all source files present, no build artifacts"</automated>
  </verify>
  <done>All source files from TonbilAiFirewallV41 are present in TonbilAiFirevallv5, with no node_modules, dist, .git, or __pycache__ directories</done>
</task>

<task type="auto">
  <name>Task 2: Initialize fresh git repo and install dependencies</name>
  <files>E:/Nextcloud-Yeni/TonbilAiFirevallv5/.git</files>
  <action>
    1. Initialize a fresh git repository in E:/Nextcloud-Yeni/TonbilAiFirevallv5:
       ```bash
       cd "E:/Nextcloud-Yeni/TonbilAiFirevallv5" && git init
       ```

    2. Create initial commit with all source files:
       ```bash
       cd "E:/Nextcloud-Yeni/TonbilAiFirevallv5" && git add -A && git commit -m "Initial commit: TonbilAiFirevallv5 project fork from V41"
       ```

    3. Install frontend npm dependencies:
       ```bash
       cd "E:/Nextcloud-Yeni/TonbilAiFirevallv5/frontend" && npm install
       ```

    This ensures the new project is immediately ready for development with a clean git history and working dependencies.
  </action>
  <verify>
    <automated>cd "E:/Nextcloud-Yeni/TonbilAiFirevallv5" && git log --oneline -1 && ls frontend/node_modules/.package-lock.json && echo "PASS: git initialized and npm installed"</automated>
  </verify>
  <done>Fresh git repo with initial commit exists, frontend node_modules are installed, project is ready for development</done>
</task>

</tasks>

<verification>
1. E:/Nextcloud-Yeni/TonbilAiFirevallv5 exists with all expected subdirectories (frontend/src, backend/app, config, deploy, docs)
2. No build artifacts leaked (node_modules, dist, .git from source, __pycache__)
3. Fresh git repo with clean initial commit
4. Frontend dependencies installed (node_modules present from fresh npm install)
</verification>

<success_criteria>
- TonbilAiFirevallv5 directory contains complete project source (frontend/src/**, backend/app/**, config/**, etc.)
- Zero build artifacts from the source project
- `git log` in new directory shows a single clean initial commit
- `ls frontend/node_modules` confirms fresh dependencies installed
</success_criteria>

<output>
After completion, create `.planning/quick/1-yapiyi-tamamen-yeni-bir-klasore-yaz-ismi/1-SUMMARY.md`
</output>
