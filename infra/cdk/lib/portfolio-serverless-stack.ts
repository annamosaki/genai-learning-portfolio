import * as cdk from "aws-cdk-lib";
import * as amplify from "aws-cdk-lib/aws-amplify";
import * as codecommit from "aws-cdk-lib/aws-codecommit";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as ecr_assets from "aws-cdk-lib/aws-ecr-assets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as ses from "aws-cdk-lib/aws-ses";
import { Construct } from "constructs";
import * as path from "path";

const REPO_ROOT = path.join(__dirname, "../../..");

type ApiDef = {
  id: string;
  dockerfile: string;
  memory: number;
  timeoutSec: number;
  port: string;
};

export class PortfolioServerlessStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Secret is managed outside deploys (set once). CI must not overwrite it.
    const openaiSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      "OpenAiSecret",
      "anna-portfolio/openai-api-key",
    );
    const appSecrets = secretsmanager.Secret.fromSecretNameV2(
      this,
      "AppSecrets",
      "anna-portfolio/app-secrets",
    );

    // Amazon SES — send Research Digest newsletters from the verified domain.
    // Domain identity + DKIM are managed in Route53 for annamosaki.com.
    const zone = route53.HostedZone.fromLookup(this, "RootZone", {
      domainName: "annamosaki.com",
    });
    new ses.EmailIdentity(this, "SesDomain", {
      identity: ses.Identity.publicHostedZone(zone),
      mailFromDomain: "mail.annamosaki.com",
    });

    const artifacts = new s3.Bucket(this, "Artifacts", {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      lifecycleRules: [{ expiration: cdk.Duration.days(30) }],
    });

    const runs = new dynamodb.Table(this, "Runs", {
      partitionKey: { name: "pk", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "sk", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: "ttl",
    });

    const repo = new codecommit.Repository(this, "SourceRepo", {
      repositoryName: "anna-portfolio",
      description: "Anna Mosaki portfolio monorepo (Amplify + Lambda)",
    });

    const mcpDefs: ApiDef[] = [
      {
        id: "YfMcp",
        dockerfile: "infra/docker/Dockerfile.yf-mcp",
        memory: 1024,
        timeoutSec: 120,
        port: "8211",
      },
      {
        id: "EdgarMcp",
        dockerfile: "infra/docker/Dockerfile.edgar-mcp",
        memory: 2048,
        timeoutSec: 180,
        port: "8210",
      },
    ];

    const mcpUrls: Record<string, string> = {};
    for (const mcp of mcpDefs) {
      const fn = new lambda.DockerImageFunction(this, mcp.id, {
        code: lambda.DockerImageCode.fromImageAsset(REPO_ROOT, {
          file: mcp.dockerfile,
          platform: ecr_assets.Platform.LINUX_ARM64,
        }),
        architecture: lambda.Architecture.ARM_64,
        memorySize: mcp.memory,
        timeout: cdk.Duration.seconds(mcp.timeoutSec),
        environment: {
          AWS_LWA_INVOKE_MODE: "response_stream",
          AWS_LWA_READINESS_CHECK_PATH: "/health",
          AWS_LWA_READINESS_CHECK_TIMEOUT: "30000",
          AWS_LWA_PORT: mcp.port,
          PORT: mcp.port,
          SERVERLESS: "1",
          EDGAR_IDENTITY: "Anna Mosaki mosakianna@gmail.com",
          EDGAR_LOCAL_DATA_DIR: "/tmp/edgar",
          EDGAR_CACHE_DIR: "/tmp/edgar_cache",
          HOME: "/tmp",
          YFMCP_HOST: "0.0.0.0",
          YFMCP_PORT: mcp.port,
        },
      });

      const fnUrl = fn.addFunctionUrl({
        authType: lambda.FunctionUrlAuthType.NONE,
        invokeMode: lambda.InvokeMode.RESPONSE_STREAM,
        cors: {
          allowedOrigins: ["*"],
          allowedMethods: [lambda.HttpMethod.ALL],
          allowedHeaders: ["*"],
          maxAge: cdk.Duration.days(1),
        },
      });
      mcpUrls[mcp.id] = fnUrl.url;
      new cdk.CfnOutput(this, `${mcp.id}Url`, { value: fnUrl.url });
    }

    const apis: ApiDef[] = [
      {
        id: "PortfolioApi",
        dockerfile: "infra/docker/Dockerfile.portfolio-api",
        memory: 1024,
        timeoutSec: 120,
        port: "8000",
      },
      {
        id: "LabApi",
        dockerfile: "infra/docker/Dockerfile.lab-api",
        memory: 1536,
        timeoutSec: 180,
        port: "8100",
      },
      {
        id: "DeskApi",
        dockerfile: "infra/docker/Dockerfile.desk-api",
        memory: 2048,
        timeoutSec: 600,
        port: "8200",
      },
      {
        id: "DigestApi",
        dockerfile: "infra/docker/Dockerfile.digest-api",
        memory: 1024,
        timeoutSec: 300,
        port: "8300",
      },
    ];

    const apiUrls: Record<string, string> = {};

    // Pretty hostnames (CloudFront → Function URLs). Prefer these over raw lambda-url hosts.
    const customApi = {
      PortfolioApi: "https://api.annamosaki.com/",
      LabApi: "https://lab-api.annamosaki.com/",
      DeskApi: "https://desk-api.annamosaki.com/",
      DigestApi: "https://digest-api.annamosaki.com/",
      YfMcp: "https://yf.annamosaki.com/",
      EdgarMcp: "https://edgar.annamosaki.com/mcp",
    };

    for (const api of apis) {
      const extraEnv: Record<string, string> = {};
      if (api.id === "LabApi" || api.id === "DeskApi") {
        extraEnv.YFMCP_URL = customApi.YfMcp;
        extraEnv.EDGAR_MCP_URL = customApi.EdgarMcp;
        extraEnv.EDGAR_IDENTITY = "Anna Mosaki mosakianna@gmail.com";
      }
      if (api.id === "DigestApi") {
        extraEnv.ARTIFACT_DIR = "/tmp/artifacts/signal-desk";
        extraEnv.NEWSLETTER_FROM = "Research Digest <digest@annamosaki.com>";
        extraEnv.DIGEST_PUBLIC_URL = "https://digest.annamosaki.com/demos/research-digest";
        extraEnv.DIGEST_API_PUBLIC_URL = "https://digest-api.annamosaki.com";
        extraEnv.SUBSCRIBERS_TABLE = runs.tableName;
      }

      const fn = new lambda.DockerImageFunction(this, api.id, {
        code: lambda.DockerImageCode.fromImageAsset(REPO_ROOT, {
          file: api.dockerfile,
          platform: ecr_assets.Platform.LINUX_ARM64,
        }),
        architecture: lambda.Architecture.ARM_64,
        memorySize: api.memory,
        timeout: cdk.Duration.seconds(api.timeoutSec),
        environment: {
          AWS_LWA_INVOKE_MODE: "response_stream",
          AWS_LWA_READINESS_CHECK_PATH: "/health",
          AWS_LWA_PORT: api.port,
          PORT: api.port,
          ARTIFACT_BUCKET: artifacts.bucketName,
          RUNS_TABLE: runs.tableName,
          SERVERLESS: "1",
          OPENAI_SECRET_ARN: openaiSecret.secretArn,
          APP_SECRETS_ARN: appSecrets.secretArn,
          CORS_ORIGINS: "*",
          AUTO_APPROVE_ON_TIMEOUT: "true",
          APPROVAL_TIMEOUT_SECONDS: "120",
          ...extraEnv,
        },
      });

      artifacts.grantReadWrite(fn);
      runs.grantReadWriteData(fn);
      openaiSecret.grantRead(fn);
      appSecrets.grantRead(fn);

      if (api.id === "DigestApi") {
        fn.addToRolePolicy(
          new iam.PolicyStatement({
            actions: ["ses:SendEmail", "ses:SendRawEmail", "sesv2:SendEmail"],
            resources: ["*"],
          }),
        );
      }

      const fnUrl = fn.addFunctionUrl({
        authType: lambda.FunctionUrlAuthType.NONE,
        invokeMode: lambda.InvokeMode.RESPONSE_STREAM,
        cors: {
          allowedOrigins: ["*"],
          allowedMethods: [lambda.HttpMethod.ALL],
          allowedHeaders: ["*"],
          maxAge: cdk.Duration.days(1),
        },
      });

      apiUrls[api.id] = fnUrl.url;
      new cdk.CfnOutput(this, `${api.id}Url`, { value: fnUrl.url });
    }

    const amplifyRole = new iam.Role(this, "AmplifyRole", {
      assumedBy: new iam.ServicePrincipal("amplify.amazonaws.com"),
      description: "Amplify SSR hosting role for Anna portfolio",
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("AdministratorAccess-Amplify"),
      ],
    });
    repo.grantPull(amplifyRole);

    const webDefs = [
      {
        id: "PortfolioWeb",
        name: "anna-portfolio-web",
        appRoot: "apps/web",
        env: [
          { name: "NEXT_PUBLIC_API_BASE_URL", value: customApi.PortfolioApi },
          { name: "NEXT_PUBLIC_LAB_API_URL", value: customApi.LabApi },
          { name: "NEXT_PUBLIC_AGENT_DESK_API_URL", value: customApi.DeskApi },
          { name: "NEXT_PUBLIC_RESEARCH_DIGEST_API_URL", value: customApi.DigestApi },
          { name: "NEXT_PUBLIC_YFMCP_URL", value: customApi.YfMcp },
          { name: "NEXT_PUBLIC_EDGAR_MCP_URL", value: customApi.EdgarMcp.replace(/\/mcp$/, "/") },
          { name: "LLM_LAB_URL", value: "https://lab.annamosaki.com" },
          { name: "AGENT_DESK_URL", value: "https://desk.annamosaki.com" },
          { name: "RESEARCH_DIGEST_URL", value: "https://digest.annamosaki.com" },
          { name: "AMPLIFY_MONOREPO_APP_ROOT", value: "apps/web" },
        ],
      },
      {
        id: "LabWeb",
        name: "anna-llm-lab-web",
        appRoot: "projects/01-llm-lab/web",
        env: [
          { name: "ZONE_BASE_PATH", value: "/demos/llm-lab" },
          { name: "LAB_API_URL", value: customApi.LabApi },
          { name: "NEXT_PUBLIC_PORTFOLIO_URL", value: "https://annamosaki.com" },
          { name: "AMPLIFY_MONOREPO_APP_ROOT", value: "projects/01-llm-lab/web" },
        ],
      },
      {
        id: "DeskWeb",
        name: "anna-agent-desk-web",
        appRoot: "projects/02-agent-desk/web",
        env: [
          { name: "ZONE_BASE_PATH", value: "/demos/agent-desk" },
          { name: "NEXT_PUBLIC_ZONE_BASE_PATH", value: "/demos/agent-desk" },
          { name: "AGENT_DESK_API_URL", value: customApi.DeskApi },
          { name: "NEXT_PUBLIC_AGENT_DESK_API_URL", value: customApi.DeskApi },
          { name: "NEXT_PUBLIC_PORTFOLIO_URL", value: "https://annamosaki.com" },
          { name: "AMPLIFY_MONOREPO_APP_ROOT", value: "projects/02-agent-desk/web" },
        ],
      },
      {
        id: "DigestWeb",
        name: "anna-research-digest-web",
        appRoot: "projects/03-research-digest/web",
        env: [
          { name: "ZONE_BASE_PATH", value: "/demos/research-digest" },
          { name: "NEXT_PUBLIC_ZONE_BASE_PATH", value: "/demos/research-digest" },
          { name: "RESEARCH_DIGEST_API_URL", value: customApi.DigestApi },
          { name: "NEXT_PUBLIC_RESEARCH_DIGEST_API_URL", value: customApi.DigestApi },
          { name: "NEXT_PUBLIC_PORTFOLIO_URL", value: "https://annamosaki.com" },
          { name: "AMPLIFY_MONOREPO_APP_ROOT", value: "projects/03-research-digest/web" },
        ],
      },
    ];

    for (const web of webDefs) {
      const app = new amplify.CfnApp(this, web.id, {
        name: web.name,
        platform: "WEB_COMPUTE",
        iamServiceRole: amplifyRole.roleArn,
        repository: repo.repositoryCloneUrlHttp,
        environmentVariables: web.env,
        buildSpec: buildSpecFor(web.appRoot),
      });

      new amplify.CfnBranch(this, `${web.id}Main`, {
        appId: app.attrAppId,
        branchName: "main",
        enableAutoBuild: true,
        stage: "PRODUCTION",
      });

      new cdk.CfnOutput(this, `${web.id}AppId`, { value: app.attrAppId });
      new cdk.CfnOutput(this, `${web.id}Domain`, {
        value: `https://main.${app.attrDefaultDomain}`,
      });
    }

    new cdk.CfnOutput(this, "ArtifactsBucket", { value: artifacts.bucketName });
    new cdk.CfnOutput(this, "RunsTable", { value: runs.tableName });
    new cdk.CfnOutput(this, "CodeCommitCloneUrl", {
      value: repo.repositoryCloneUrlHttp,
    });
    new cdk.CfnOutput(this, "CodeCommitName", { value: repo.repositoryName });
  }
}

function buildSpecFor(appRoot: string): string {
  const workspaceExpr = `node -p "require('./${appRoot}/package.json').name"`;
  return [
    "version: 1",
    "applications:",
    `  - appRoot: ${appRoot}`,
    "    frontend:",
    "      phases:",
    "        preBuild:",
    "          commands:",
    "            - export REPO_ROOT=$(git rev-parse --show-toplevel)",
    "            - cd $REPO_ROOT && npm ci",
    "        build:",
    "          commands:",
    "            - export REPO_ROOT=$(git rev-parse --show-toplevel)",
    `            - cd $REPO_ROOT && npm run build --workspace=$(${workspaceExpr})`,
    "      artifacts:",
    "        baseDirectory: .next",
    "        files:",
    "          - '**/*'",
    "      cache:",
    "        paths:",
    "          - node_modules/**/*",
  ].join("\n");
}
