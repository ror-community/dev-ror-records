# ror-records
Test repository for developing deployment process for ROR record updates.

## Deployment steps

### Create JSON files for new and updated ROR records
TODO: Write doc here or link to docs elsewhere?

### Create new rc (release candidate) branch

#### Github UI
1. Go to [ror-community/ror-records](https://github.com/ror-community/ror-records)
2. Click the branches dropdown in the upper left (should say 'main' by default)
3. Click dummy-rc to switch to the dummy-rc branch
4. Click the branches dropdown again (should now say 'dummy-rc')
5. Enter the name of your new rc branch in the "Find or create branch" field. Names for new release candidate branches should follow the convention v[MAJOR VERSION].[MINOR VERSION].[PATCH VERSION IF APPLICABLE]-rc, ex: v1.3-rc.
6. Click Create branch: [NEW BRANCH NAME] from 'dummy-rc'

#### Git CLI
These steps assume that you have already [installed and configured git](https://git-scm.com/downloads) on your computer, and that you have cloned the [ror-records](https://github.com/ror-community/ror-records) repository locally.

1. In the ror-records checkout the dummy-rc branch

    git checkout dummy-rc

2. Make sure your local dummy-rc branch matches the remote branch (make sure to git stash any local changes before doing this!)

    git fetch origin
    git reset --hard origin/dummy-rc

3. Checkout a rc branch based on dummy-rc. Names for new release candidate branches should follow the convention v[MAJOR VERSION].[MINOR VERSION].[PATCH VERSION IF APPLICABLE]-rc, ex: v1.3-rc.

   git checkout -b v1.3-rc

### Push new/updated ROR JSON files to rc branch

#### Github UI
1. In the ror-records repository, click the Branches dropdown at left and choose the vX.X-rc branch that you created in the previous steps.
2. Click the Add file button at right and choose Upload files
3. Add JSON files for new and updated ROR records as prompted
4. Under Commit changes, type a commit message in the first text box, leave the radio button set to "Commit directly to the vX.X-rc branch" and click Commit changes.
5. Repeat steps 1-4 if additional files need to be added to the release candidate.

#### Git CLI
1. Place the JSON files for new and updated records in your local copy of the ror-records repository.
2. Add and commit the files

        git add *
        git commit -m "add new and updated ROR records to v1.3-rc"

3. Push the files and new branch to the remote ror-records repository

        git push origin v1.3-rc

4. Repeat steps 1-3 if additional files need to be added to the release candidate.

### Generate relationships
Relationships are not included in the intitial ROR record JSON files. Relationships are generated using a script [generaterelationships.py](https://github.com/ror-community/ror-api/blob/dev/rorapi/management/commands/generaterelationships.py) triggered by a Github action [Create relationships](https://github.com/ror-community/ror-records/blob/dummy-rc/.github/workflows/generate_relationships.yml), which should be run after all new and updated JSON records to be included in the release are uploaded to the vX.X-rc branch.

1. Create relationships list as a CSV and name the file relationships.csv (TODO: directions about CSV formatting). **IMPORTANT! File must be named relationships.csv**
2. Commit and push the relationships.csv file to the current rc branch

        git add relationships.csv
        git commit -m "adding relationships list to v1.3-rc"
        git push origin v1.3-rc

3. Go to https://github.com/ror-community/ror-records/actions/workflows/generate_relationships.yml (Actions > Create relationships in the ror-records repository)
4. Click Run workflow at right, choose the vX.X-rc branch that you just pushed relationships.csv to, and click the green Run workflow button.
5. It will take a few minutes for the workflow to run. If sucessful, the workflow will update ROR record JSON files in the vX.X-rc branch that you specified, a green checkbox will be shown on the workflow runs list in Github, and a success messages will be posted to the #ror-curation-releases Slack channel. If the workflow run is unsuccessful, an red X will be shown on the workflow runs list in Github and an error message will be posted to Slack. To see the error details, click the generate-relationships box on the workflow run page in Github.
6. If this workflow fails, there's likely a mistake in the relationships.csv or one or more of the ROR record JSON files that needs to be corrected. In that case, make the needed corrections, commit and push the files to the vX.X-rc branch and repeat steps 3-5 to re-run the Create relationships workflow.

### Validate files
Before finalizing a release candidate, JSON files for new and updated ROR records should be validated to check that they comply with the ROR schema and contained properly formatted JSON. Validation is performed by a script [run_validations.py](https://github.com/ror-community/validation-suite/blob/main/run_validations.py) triggered by a Github action [Validate files](https://github.com/ror-community/ror-records/blob/demo-rc/.github/workflows/validate.yml
), which should be run after all new and updated JSON records to be included in the release are uploaded to the vX.X-rc branch.

1. Go to https://github.com/ror-community/ror-records/actions/workflows/validate.yml (Actions > Create relationships in the ror-records repository)
2. Click Run workflow at right, choose the current vX.X-rc branch and click the green Run workflow button.
3. It will take a few minutes for the workflow to run. If sucessful, a green checkbox will be shown on the workflow runs list in Github, and a success messages will be posted to the #ror-curation-releases Slack channel. If the workflow run is unsuccessful, an red X will be shown on the workflow runs list in Github and an error message will be posted to Slack. To see the error details, click the validate-filtes box on the workflow run page in Github.
4. If this workflow fails, there's an issue with the data in one of more ROR record JSON files that needs to be corrected. In that case, check the error details, make the needed corrections, commit and push the files to the vX.X-rc branch and repeat steps 1-3 to re-run the Validate files workflow.

**IMPORTANT! Validate files workflow must succeed before proceeding to deployment**

### Deploy to Staging
Deploying to staging.ror.org/search and api.staging.ror.org requires making a Github pull request and merging it. This trigggers an automated deployment process. Note that only specific Github users are allowed to open and merge pull requests.

1. Go to https://github.com/ror-community/ror-records/pulls (Pull requests tab in ror-records repository)
2. Click New pull request at right
3. Click the Base dropdown at left and choose Staging. Important! Do not make a pull request against the default Main branch.
4. Click the Compare dropdown and choose the vX.X.-rc branch that you have been working with in the previous steps.
5. Click Create pull request TO DO: What should our standard PR message be?
6. Double-check that the Base dropdown is set to Staging and that the list of updated files appears to be correct, then click Create pull request
7. A Github action [Staging pull request](https://github.com/ror-community/ror-records/blob/dummy-rc/.github/workflows/staging_pull_request.yml) will be triggered which (1) verifies that the user is allowed to perform a release to staging and (2) runs the file validation script again. If sucessful, a green checkbox will be shown in the pull request details, and a success messages will be posted to the #ror-curation-releases Slack channel.
8. Once the Staging pull request workflow has completed successfully, click Merge pull request
9. A Github action [Deploy to staging](https://github.com/ror-community/ror-records/blob/dummy-rc/.github/workflows/merge.yml) will be triggered, which pushes the new and updated JSON files to AWS S3 and indexes the data into the ROR Elasticsearch instance. If sucessful, a green checkbox will be shown in the pull request details, and a success messages will be posted to the #ror-curation-releases Slack channel. The new data should now be available in https://staging.ror.org/search and https://api.staging.ror.org

### Test Staging release
TODO: develop a list of standard queries to run in the API and UI

### Deploy to Production
Deploying to ror.org/search and api.ror.org requires making a Github pull request and merging it, then tagging and publishing a new release. This trigggers an automated deployment process. Note that only specific Github users are allowed to open/merge pull requests and create releases.

1. Go to https://github.com/ror-community/ror-records/pulls (Pull requests tab in ror-records repository)
2. Click New pull request at right
3. Click the Base dropdown at left and choose Main.
4. Click the Compare dropdown and choose Staging.
5. Click Create pull request TO DO: What should our standard PR message be?
6. Double-check that the Base dropdown is set to Main and that the list of updated files appears to be correct, then click Create pull request
7. A Github action Production pull request will be triggered, which does TBD. If sucessful, a green checkbox will be shown in the pull request details, and a success messages will be posted to the #ror-curation-releases Slack channel.
8. Once the Production pull request workflow has completed successfully, click Merge pull request.
9. Go to https://github.com/ror-community/ror-records/releases (Release tab in ror-records repository)
10. Click Draft new release at right
11. Click the Choose a tag dropdown and enter the version number for the release, ex v1.3. This should be the same number as the release candidate branch, without the  "-rc". Click Create new tag X.X on publish.
12. In the Release name field, enter "ROR release X.X" (replace X.X with the release tag number)
13. TO DO: What release notes should we enter here?
14. Click Publish release
9. A Github action Deploy to production will be triggered, which pushes the new and updated JSON files to AWS S3, indexes the data into the production ROR Elasticsearch instance and generates  a new data dump file in TBD. If sucessful, a green checkbox will be shown in the pull request details, and a success messages will be posted to the #ror-curation-releases Slack channel. The new data should now be available in https://ror.org/search and https://api.ror.org

### Test and announce production release
TODO: develop a list of standard queries to run in the API and UI
TODO: develop standard text and  list of channels that we announce new release to
TODO: process for notifying requestors that their curation request has been completed


