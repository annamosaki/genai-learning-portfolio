#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { PortfolioCicdStack } from "../lib/cicd-stack";
import { PortfolioServerlessStack } from "../lib/portfolio-serverless-stack";

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? "us-east-1",
};

new PortfolioServerlessStack(app, "AnnaPortfolioServerless", {
  env,
  description: "Anna portfolio - Amplify web + Lambda APIs (cost optimized)",
});

const githubConnectionArn =
  (app.node.tryGetContext("githubConnectionArn") as string | undefined) ||
  process.env.GITHUB_CONNECTION_ARN ||
  "";

if (githubConnectionArn) {
  new PortfolioCicdStack(app, "AnnaPortfolioCicd", {
    env,
    description:
      "CI/CD - GitHub push to main deploys Lambda APIs via CodeBuild",
  });
}
