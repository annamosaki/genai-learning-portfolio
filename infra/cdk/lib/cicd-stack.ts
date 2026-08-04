import * as cdk from "aws-cdk-lib";
import * as codebuild from "aws-cdk-lib/aws-codebuild";
import * as codepipeline from "aws-cdk-lib/aws-codepipeline";
import * as codepipeline_actions from "aws-cdk-lib/aws-codepipeline-actions";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

const GITHUB_OWNER = "annamosaki";
const GITHUB_REPO = "genai-learning-portfolio";
const GITHUB_OWNER_REPO = `${GITHUB_OWNER}/${GITHUB_REPO}`;
const GITHUB_BRANCH = "main";

/**
 * Push to GitHub `main` →
 *   1) Amplify auto-builds the four Next.js apps
 *   2) GitHub Actions (OIDC) starts CodePipeline → CodeBuild `cdk deploy`
 *
 * Requires a CodeConnections GitHub connection (AVAILABLE). Pass ARN via
 * cdk.json context `githubConnectionArn` or `-c githubConnectionArn=...`.
 */
export class PortfolioCicdStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const connectionArn =
      (this.node.tryGetContext("githubConnectionArn") as string | undefined) ||
      process.env.GITHUB_CONNECTION_ARN ||
      "";

    if (!connectionArn) {
      throw new Error(
        "Missing GitHub CodeConnections ARN. Deploy with " +
          "-c githubConnectionArn=arn:aws:codeconnections:us-east-1:ACCOUNT:connection/UUID",
      );
    }

    const artifactsBucket = new s3.Bucket(this, "PipelineArtifacts", {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      autoDeleteObjects: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      lifecycleRules: [{ expiration: cdk.Duration.days(30) }],
    });

    const project = new codebuild.PipelineProject(this, "CdkDeployProject", {
      projectName: "anna-portfolio-cdk-deploy",
      description: "Build Lambda images and cdk deploy AnnaPortfolioServerless",
      buildSpec: codebuild.BuildSpec.fromSourceFilename("infra/buildspec-cdk.yml"),
      environment: {
        buildImage: codebuild.LinuxArmBuildImage.AMAZON_LINUX_2_STANDARD_3_0,
        computeType: codebuild.ComputeType.LARGE,
        privileged: true,
      },
      cache: codebuild.Cache.local(
        codebuild.LocalCacheMode.DOCKER_LAYER,
        codebuild.LocalCacheMode.CUSTOM,
      ),
      timeout: cdk.Duration.hours(2),
    });

    project.role?.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("AdministratorAccess"),
    );

    const sourceOutput = new codepipeline.Artifact("SourceOutput");

    const pipeline = new codepipeline.Pipeline(this, "Pipeline", {
      pipelineName: "anna-portfolio-deploy",
      pipelineType: codepipeline.PipelineType.V2,
      executionMode: codepipeline.ExecutionMode.SUPERSEDED,
      artifactBucket: artifactsBucket,
    });

    pipeline.addStage({
      stageName: "Source",
      actions: [
        new codepipeline_actions.CodeStarConnectionsSourceAction({
          actionName: "GitHub",
          owner: GITHUB_OWNER,
          repo: GITHUB_REPO,
          branch: GITHUB_BRANCH,
          connectionArn,
          output: sourceOutput,
          codeBuildCloneOutput: true,
          triggerOnPush: true,
        }),
      ],
    });

    pipeline.addStage({
      stageName: "DeployApis",
      actions: [
        new codepipeline_actions.CodeBuildAction({
          actionName: "CdkDeploy",
          project,
          input: sourceOutput,
        }),
      ],
    });

    const cfnPipeline = pipeline.node.defaultChild as codepipeline.CfnPipeline;
    cfnPipeline.addPropertyOverride("Triggers", [
      {
        ProviderType: "CodeStarSourceConnection",
        GitConfiguration: {
          SourceActionName: "GitHub",
          Push: [
            {
              Branches: {
                Includes: [GITHUB_BRANCH],
              },
            },
          ],
        },
      },
    ]);

    // GitHub Actions OIDC → start pipeline on push (reliable trigger path).
    const githubOidc = new iam.OpenIdConnectProvider(this, "GitHubOidc", {
      url: "https://token.actions.githubusercontent.com",
      clientIds: ["sts.amazonaws.com"],
    });

    const ghaRole = new iam.Role(this, "GitHubActionsStartPipeline", {
      roleName: "anna-portfolio-gha-start-pipeline",
      assumedBy: new iam.WebIdentityPrincipal(
        githubOidc.openIdConnectProviderArn,
        {
          StringEquals: {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          },
          StringLike: {
            "token.actions.githubusercontent.com:sub": `repo:${GITHUB_OWNER}@*/${GITHUB_REPO}@*:*`,
          },
        },
      ),
      description: "GitHub Actions may start anna-portfolio-deploy",
    });
    ghaRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "codepipeline:StartPipelineExecution",
          "codepipeline:GetPipeline",
          "codepipeline:GetPipelineExecution",
          "codepipeline:ListPipelineExecutions",
        ],
        resources: [
          `arn:aws:codepipeline:${this.region}:${this.account}:anna-portfolio-deploy`,
        ],
      }),
    );

    new cdk.CfnOutput(this, "PipelineName", { value: pipeline.pipelineName });
    new cdk.CfnOutput(this, "CodeBuildProject", { value: project.projectName });
    new cdk.CfnOutput(this, "GitHubRepo", { value: GITHUB_OWNER_REPO });
    new cdk.CfnOutput(this, "GitHubActionsRoleArn", { value: ghaRole.roleArn });
    new cdk.CfnOutput(this, "HowToRedeploy", {
      value:
        "git push origin main  →  Amplify (web) + GHA starts CodePipeline (APIs)",
    });
  }
}
