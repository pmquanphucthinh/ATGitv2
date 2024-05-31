import os
import requests
import subprocess
import sys
import random
import json

def add_gpg_key_to_github(github_token, public_key):
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    gpg_key_url = "https://api.github.com/user/gpg_keys"
    data = {
        "armored_public_key": public_key
    }
    response = requests.post(gpg_key_url, headers=headers, json=data)
    if response.status_code == 201:
        print("GPG key added to GitHub account successfully.")
    else:
        print(f"Failed to add GPG key: {response.status_code}")
        print(response.json())

def main(github_token):
    # Get user information
    user_info = requests.get("https://api.github.com/user", headers={"Authorization": f"token {github_token}"}).json()
    github_id = user_info["id"]
    github_username = user_info["login"]
    email = f"{github_id}+{github_username}@users.noreply.github.com"

    # Find 6 random repositories
    random_repos_response = requests.get(f"https://api.github.com/repositories?since={random.randint(1, 500)}")
    random_repos = [repo["full_name"] for repo in random_repos_response.json()[:6]]

    # Fork 3 repositories
    for repo in random_repos[:3]:
        requests.post(f"https://api.github.com/repos/{repo}/forks", headers={"Authorization": f"token {github_token}"})

    # Select a random repository
    random_repo = random.choice(random_repos)

    # Create a new repository
    repo_name = random_repo.split("/")[-1]
    create_repo_response = requests.post("https://api.github.com/user/repos", headers={"Authorization": f"token {github_token}"}, json={"name": repo_name})

    if create_repo_response.status_code == 201:
        created_repo = create_repo_response.json()["full_name"]
        print(f"Created: {created_repo}")
    else:
        print(f"Failed to create repository: {create_repo_response.status_code}")
        print(create_repo_response.json())
        sys.exit(1)

    # Generate GPG key
    subprocess.run(['gpg', '--batch', '--gen-key'], input="EOF\n%no-protection\nKey-Type: default\nKey-Length: 2048\nSubkey-Type: default\nName-Real: {}\nName-Email: {}\nExpire-Date: 0\nEOF\n".format(github_username, email), text=True, check=True)
    key_id = subprocess.run(['gpg', '--list-keys', '--with-colons'], capture_output=True, text=True).stdout.split("pub:")[1].split(":")[4]

    # Configure GPG key in GitHub
    public_key = subprocess.run(['gpg', '--armor', '-a', '--export', key_id], capture_output=True, text=True).stdout
    add_gpg_key_to_github(github_token, public_key)

    # Create and sign SoftwareUpdate.txt
    with open("SoftwareUpdate.txt", "w") as f:
        f.write("ultralytics 8.0.225 multi-video tracker bug fix (#6862)")
    subprocess.run(['gpg', '--default-key', key_id, '--sign', '--output', 'SoftwareUpdate.txt.gpg', '--detach-sign', 'SoftwareUpdate.txt'], check=True)
    os.remove("SoftwareUpdate.txt")

    # Push signed file to created repository
    subprocess.run(['git', 'clone', f"https://x-access-token:{github_token}@github.com/{created_repo}.git", 'temp_repo'], check=True)
    subprocess.run(['mv', 'SoftwareUpdate.txt.gpg', 'temp_repo/'], check=True)
    subprocess.run(['git', 'add', 'temp_repo/SoftwareUpdate.txt.gpg'], cwd='temp_repo', check=True)
    subprocess.run(['git', 'commit', '-m', 'Add signed SoftwareUpdate.txt'], cwd='temp_repo', check=True)
    subprocess.run(['git', 'push', 'origin', 'master'], cwd='temp_repo', check=True)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <GitHub_Personal_Access_Token>")
        sys.exit(1)
    main(sys.argv[1])

