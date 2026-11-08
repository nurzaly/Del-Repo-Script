# Del-Repo-Script

This repository is designed to help you delete a GitHub repository from your account using a script.

## Important

Before using this script, you must have a GitHub Personal Access Token (PAT) with the required permissions to delete repositories.

## Prerequisites

- A GitHub account
- A Personal Access Token (PAT)
- Git installed on your machine
- A repository you want to delete

## Usage

1. Generate a GitHub personal access token.
2. Make sure the token has permission to delete repositories.
3. Configure the script with your token and repository name.
4. Run the script to delete the repository.

## Warning

Deleting a repository is permanent and cannot be undone. Make sure you have backed up anything important before running this script.

## Example

```bash
# Example usage (update values as needed)
export GITHUB_TOKEN="your_personal_access_token"
./delete-repo.sh
```

## Notes

This project is intended for personal use and should be used responsibly.
