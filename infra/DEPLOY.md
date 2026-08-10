# Deploy — Anna Portfolio (serverless)

## Architecture (cost-optimized)

| Layer | Service | Idle cost |
|------|---------|-----------|
| APIs (4) | Lambda container + Function URL (ARM64, response streaming) | ~$0 |
| Run/HITL state | DynamoDB on-demand | ~$0 |
| Artifacts | S3 (30-day expiry) | ~$0 |
| Web (4 Next apps) | Amplify Hosting WEB_COMPUTE | free tier then low |
| Secrets | Secrets Manager | ~$0.40/mo |

No RDS, ElastiCache, NAT, or ALB.

## Prerequisites

- AWS CLI authenticated (`aws sts get-caller-identity`)
- For **local** API deploys only: Docker (Colima is fine): `colima start`
- OpenAI key already in Secrets Manager: `anna-portfolio/openai-api-key`

## Everyday redeploy (CI/CD)

Source of truth: [github.com/annamosaki/genai-learning-portfolio](https://github.com/annamosaki/genai-learning-portfolio).

After `AnnaPortfolioCicd` is deployed with a GitHub CodeConnections ARN, this is the normal loop:

```bash
# from repo root, on main
git add -A && git commit -m "your change"
./scripts/push-deploy.sh
```

That single push:

| What changed | What runs |
|--------------|-----------|
| Web / anything | **Amplify** rebuilds the 4 Next.js apps |
| Repo `main` tip | **GitHub Actions** starts **CodePipeline** `anna-portfolio-deploy` → CodeBuild `cdk deploy` (Lambda APIs/MCPs) |

Manual API-only redeploy (no git push):

```bash
aws codepipeline start-pipeline-execution --name anna-portfolio-deploy --region us-east-1
```

Watch progress:

```bash
aws codepipeline list-pipeline-executions --pipeline-name anna-portfolio-deploy --region us-east-1 --max-items 3
aws codebuild list-builds-for-project --project-name anna-portfolio-cdk-deploy --region us-east-1 --max-items 3
```

One-time CI/CD stack (no Docker required). Create a GitHub connection in AWS Console first, then:

```bash
cd infra/cdk
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-east-1
npx cdk deploy AnnaPortfolioCicd --require-approval never \
  -c githubConnectionArn=arn:aws:codeconnections:us-east-1:$CDK_DEFAULT_ACCOUNT:connection/UUID
```

## Deploy APIs locally (optional)

```bash
cd infra/cdk
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-east-1
npx cdk bootstrap aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION
npx cdk deploy AnnaPortfolioServerless --require-approval never
```

## Push to GitHub

```bash
./scripts/push-deploy.sh

# or
git remote add origin https://github.com/annamosaki/genai-learning-portfolio.git
git push -u origin main
```

## Custom domain (`annamosaki.com`)

Route 53 hosted zone + Amplify custom domains + CloudFront in front of Lambda Function URLs:

| Host | Target |
|------|--------|
| `https://annamosaki.com` | Portfolio (Amplify) |
| `https://www.annamosaki.com` | Portfolio |
| `https://lab.annamosaki.com/demos/llm-lab` | LLM Lab |
| `https://desk.annamosaki.com/demos/agent-desk` | Agent Desk |
| `https://digest.annamosaki.com/demos/research-digest` | Research Digest |
| `https://api.annamosaki.com` | Portfolio API |
| `https://lab-api.annamosaki.com` | Lab API |
| `https://desk-api.annamosaki.com` | Desk API |
| `https://digest-api.annamosaki.com` | Digest API |
| `https://yf.annamosaki.com` | Yahoo Finance MCP |
| `https://edgar.annamosaki.com` | Edgar MCP |

## Estimated monthly cost (light portfolio traffic)

Roughly **$1–5/mo** plus Secrets Manager (~$0.40) and any OpenAI usage billed separately.
