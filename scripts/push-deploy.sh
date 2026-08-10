#!/usr/bin/env bash
# Push local main to GitHub. That triggers:
#   - Amplify builds (4 Next.js apps) once connected to GitHub
#   - CodePipeline anna-portfolio-deploy (Lambda/CDK via CodeBuild)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REMOTE="${1:-origin}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$BRANCH" != "main" ]]; then
  echo "Current branch is '$BRANCH'. CI/CD auto-deploys from main only."
  echo "Merge/rebase onto main first."
  exit 1
fi

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "Remote '$REMOTE' not found. Adding GitHub origin..."
  git remote add "$REMOTE" \
    "https://github.com/annamosaki/genai-learning-portfolio.git"
fi

echo "Pushing main → $REMOTE (Amplify + CodePipeline)..."
git push -u "$REMOTE" main

echo
echo "Web: Amplify console (apps anna-*-web)"
echo "APIs: aws codepipeline list-pipeline-executions --pipeline-name anna-portfolio-deploy --max-items 3 --region us-east-1"
echo "Manual API redeploy: aws codepipeline start-pipeline-execution --name anna-portfolio-deploy --region us-east-1"
