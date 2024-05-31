import os
import requests
import subprocess
import sys
import random
import json

github_username = ""

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

def main(github_token, github_username):
    global github_username  # Declaring the variable as global to modify it
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
    try:
        with open("gpg_input.txt", "w") as f:
            f.write("EOF\n%no-protection\nKey-Type: default\nKey-Length: 2048\nSubkey-Type: default\nName-Real: {}\nName-Email: {}\nExpire-Date: 0\nEOF\n".format(github_username, email))
        subprocess.run(['gpg', '--batch', '--gen-key'], stdin=open("gpg_input.txt", "r"), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error generating GPG key: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error creating gpg_input.txt: {e}")
        sys.exit(1)

# Xóa file tạm thời
os.remove("gpg_input.txt")

# Lấy ID của khóa
try:
    list_keys_output = subprocess.run(['gpg', '--list-keys', '--with-colons'], capture_output=True, text=True, check=True).stdout
    print("List keys output:")
    print(list_keys_output)
    key_id = list_keys_output.split("pub:")[1].split(":")[4]
except subprocess.CalledProcessError as e:
    print(f"Error retrieving key ID: {e}")
    sys.exit(1)
except IndexError as e:
    print(f"Error retrieving key ID: {e}")
    sys.exit(1)


    # Configure GPG key in GitHub
    public_key = subprocess.run(['gpg', '--armor', '-a', '--export', key_id], capture_output=True, text=True).stdout
    add_gpg_key_to_github(github_token, public_key)

    # Create and sign SoftwareUpdate.txt
    with open("SoftwareUpdate.txt", "w") as f:
        f.write("ultralytics 8.0.225 multi-video tracker bug fix (#6862)")
    subprocess.run(['gpg', '--default-key', key_id, '--sign', '--output', 'SoftwareUpdate.txt.gpg', '--detach-sign', 'SoftwareUpdate.txt'], check=True)
    os.remove("SoftwareUpdate.txt")

# Push signed file to created repository
    try:
        subprocess.run(['git', 'clone', f"https://x-access-token:{github_token}@github.com/{created_repo}.git", 'temp_repo'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        sys.exit(1)

    try:
        subprocess.run(['mv', 'SoftwareUpdate.txt.gpg', 'temp_repo/'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error moving signed file to repository: {e}")
        sys.exit(1)

    try:
        subprocess.run(['git', 'add', 'temp_repo/SoftwareUpdate.txt.gpg'], cwd='temp_repo', check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error adding file to repository: {e}")
        sys.exit(1)

    try:
        subprocess.run(['git', 'commit', '-m', 'Add signed SoftwareUpdate.txt'], cwd='temp_repo', check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error committing changes: {e}")
        sys.exit(1)

    try:
        subprocess.run(['git', 'push', 'origin', 'master'], cwd='temp_repo', check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error pushing changes to repository: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <GitHub_Personal_Access_Token>")
        sys.exit(1)
    main(sys.argv[1])
