## Deploy your app to dev/prod using CI/CD
Team CI/CD pipeline automatically lints, tests, builds, and deploys your app to AWS (dev or prod) whenever you push code.

### Pre-deployment steps
Scan the codebase for any environment-specific values that should be externalised. In particular:
- AWS account IDs, region names
- API URLs / endpoints that differ between dev and prod
- Database connection strings, bucket names
- Any secret/credential-like strings in code
These should all be moved to environment variables, with the app reading them at runtime.

Use gds-idea-cdk-constructs' AppConfig and DeploymentConfig. DeploymentConfig automatically resolves dev vs prod from the AWS account you deploy to.

### Prerequisites
Make sure all tools and packages are up to date (check gds-idea-pypi (https://co-cddo.github.io/gds-idea-pypi/) and update pyproject.toml accordingly).

### Deployment Steps
1. Scaffold or migrate — idea-app init for new apps or idea-app migrate for existing. You'll have the correct workflows in .github/workflows/.
2. Audit the repo — run idea-gh audit --fix. This ensures the repo has the right settings and branches (dev, prod).
3. Grant deploy access — add your repo to the gds-idea-cdk-access repo. This permits deployment to dev/prod.
4. Update templates — from the dev branch, run idea-app update to pull in the latest CI/CD files.
5. Make sure you have tests in a tests/ folder (or placeholder), otherwise CI will fail.
6. Feature PR → dev — raise a PR from your feature branch against dev. Anyone in the team can approve.
7. Dev → prod PR — raise a PR from dev to prod. Requires approval from a senior data scientist.

### How it works in practice
- On PR to dev/prod: runs lint, tests, build, CDK diff. Fix and push again if any check fails. 
![alt text](<Screenshot 2026-04-14 at 20.06.18.png>)
- On push to dev: runs checks then deploys to the dev AWS account. Check progress in Github Actions tab.
- On push to prod: runs checks then deploys to the prod AWS account. Check progress in Github Actions tab.
![alt text](<Screenshot 2026-03-18 at 10.13.22.png>)
- Environment (dev vs prod) is resolved automatically from which branch you push to — the pipeline assumes the corresponding AWS role via OIDC (if this step fails, review the pre-deployment steps)
- Prod deployment is always reviewed — changes reach prod only via a PR from dev, which requires senior DS approval

### Process at a glance
![alt text](<Screenshot 2026-05-12 at 09.37.57.png>)