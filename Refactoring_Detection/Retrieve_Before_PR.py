import os
import sys
import json
import requests
from pathlib import Path
import subprocess


def get_user_github_token():
    script_dir = Path(__file__).parent
    properties_file_path = script_dir / 'github-oauth.properties'
    
    try:
        with open(properties_file_path, 'r') as properties_file:
            for line in properties_file:
                line = line.strip()
                if line:
                    if not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if key.strip() == 'GITHUB_TOKEN':
                            return value.strip()
                        
        print("Error: Could not find a token in the properties file. Please check your formatting.")
        return None
        
    except FileNotFoundError:
        print(f"Error: Could not find github oauth file at {properties_file_path}")
        return None
    
def get_PR_info(project_github_name, PR_number, token):
    pr_url = 'https://api.github.com/repos/' + project_github_name + '/pulls/' + PR_number

    header = {
        'Authorization': f'token {token}'
    }
    response = requests.get(pr_url, headers=header)
    json_response = json.loads(response.content)
    return json_response

def ensure_commit_exists(commit_sha, repo_path, pr_number):
    check_commit_command = [
        'git', 'cat-file', '-e', commit_sha
    ]
    commit_exists = subprocess.run(
        check_commit_command,
        cwd= repo_path,
        capture_output=True
    )
    if commit_exists.returncode == 0:
        return True

def get_divergence_commit(target_branch, PR_head_commit, local_git_path):
    command = [
        'git',
        'merge-base',
        f'origin/{target_branch}',
        PR_head_commit
    ]
    try:
        result = subprocess.run(
                command,
                cwd=local_git_path,         
                capture_output=True,   
                text=True,             
                check=True             
            )
        return result.stdout.strip()
    except subprocess.SubprocessError as error:
        print(f'Error while trying to retrieve divergence commit SHA from Git: {error.returncode}')
        print(f'Git error message:\n{error.stderr.strip()}')
        return None

def get_file_at_commit(local_git_path, file_relative_path, commit_sha):
    command = ['git', 'show', f'{commit_sha}:{file_relative_path}']
    try:
        result = subprocess.run(
            command,
            cwd=local_git_path,         
            capture_output=True,   
            text=True,             
            check=True 
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f'Error while trying to retrieve file at commit {commit_sha}: {e.returncode}')
        print(f'Git error message:\n{e.stderr.strip()}')
        return None


def get_file_version_before_PR(local_git_path, file_relative_path, project_github_name, PR_number):
    token = get_user_github_token()
    if not token:
        print('Did not continue operation because could not retrieve token')
        return None
    
    PR_info = get_PR_info(project_github_name, PR_number, token)
    target_branch = PR_info['base']['ref']
    PR_head_commit = PR_info['head']['sha']

    if ensure_commit_exists(PR_head_commit, local_git_path, PR_number):
        divergence_commit_sha = get_divergence_commit(target_branch, PR_head_commit, local_git_path)
    else:
        print(f'Error, head commit {PR_head_commit} does not exist at all (not even in the PR)')

    file_before_PR = get_file_at_commit(local_git_path, file_relative_path, divergence_commit_sha)
    if not file_before_PR:
        print('Error, could not retrieve file.')
    return file_before_PR