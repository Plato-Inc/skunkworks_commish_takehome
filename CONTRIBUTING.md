# Contributing
We'll use a simplified [Feature Branch workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow) to facilitate collaboration on this repo:
* This repo has one primary branch called `main` and n branches for new features/work.
* Feature branches are merged into `main` via a merge commit after Brandon approves the pull request (PR).

To add a new feature follow these steps:

1. Start with the `main` branch

```
git checkout main
git fetch origin 
git reset --hard origin/main
```  
* This switches the repo to the `main` branch, pulls the latest commits and resets the repo's local copy of `main` to match the latest version.

* Create and switch to a new branch for the feature:

```
git checkout -b new-feature
```
* This checks out a branch called `new-feature` based on `main`, and the `-b` flag tells Git to create the branch if it doesn’t already exist.

2. Develop the feature

    * Write code and commit changes to the feature branch. Commits should be atomic and messages descriptive:

```
git add .
git commit -m "Implement X functionality"
```

* Regularly push the feature branch to the remote repository to safeguard the work:

```
git push -u origin new-feature
```
* This  pushes `new-feature` to the central repository (`origin`), and the `-u` flag adds it as a remote tracking branch. 

3. Keep the feature branch updated

    * Periodically, especially before making a pull request, the feature branch should be updated with the latest changes from `main` to minimize merge conflicts:

```
git checkout main
git pull origin main
git checkout new-feature
git merge main
```

4. Code review  

    * Once the feature is complete, push the latest changes and create a PR against the `main` branch. Request code reviews from Brandon.

5. Final Merge

    * After approval, the `new-feature` branch is merged into `main`.
    * It's generally a good practice to perform the merge via the UI on GitHub.
    * Delete the feature branch from the remote repository after the merge if it's no longer needed:

```
git push origin --delete new-feature
```

6. Next task
    * Switch back to the `main` branch:

```
git checkout main
```

* Pull the latest changes to ensure the local `main` branch is up-to-date:
```
git pull origin main
```
* Start the process over for the next feature or task.

## Contributing Best Practices
* Keep feature branches small and focused on a single feature or fix to streamline the review process and reduce the risk of conflicts.
* Regularly push work to remote branches to prevent loss of work and to share progress with the team.
* Frequently merge or rebase the main branch into feature branches to minimize merge conflicts.
* Delete feature branches after the feature has been merged to keep the repository clean.
* Ensure a clean commit history within the feature branch to make future reviews and potential reverts easier. 

# Future work
* Normalize line endings (`text=auto` to `.gitattributes`)
* Containerize repo once environment grows complex
* CI/CD
* Better documentation
* Wider test coverage