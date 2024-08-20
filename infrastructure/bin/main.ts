import { App } from 'aws-cdk-lib';
import { InfraStack } from '../lib/infra-stack';

const app = new App();
new InfraStack(app, 'KadaStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});

app.synth();