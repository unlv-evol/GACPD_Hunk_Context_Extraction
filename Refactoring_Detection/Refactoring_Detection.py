#
import subprocess
import sys
import json


def get_result_important_dates(pr_result_file_adress):

    divergence_date =""
    cutoff_date = ""
    with open(pr_result_file_adress, 'r', encoding = "utf-8") as pr_results:
        for line in pr_results:
            stripped_line = line.strip()
            if stripped_line.startswith("REPO DIVERGENCE DATE:"):
                divergence_date = stripped_line.split(':', 1)[1].strip()
            if stripped_line.startswith("CUTOFF DATE:"):
                cutoff_date = stripped_line.split(':', 1)[1].strip()

    return divergence_date, cutoff_date

def get_last_commit_before_date(repository_path, date):
    command = [
        "git",
        "-C",
        repository_path,
        "log",
        "-1",
        f"--before={date}",
        "--format=%H",
    ]

    try:
        command_result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        commit_sha = command_result.stdout.strip()

        if commit_sha:
            return commit_sha
        else:
            print(f"No commits found before {date}")
            return None

    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e.stderr}")
        return None


def get_refactorings_between_commits(RM_path, repo_path, output_json , divergence_commit_sha = None, cutoff_commit_sha = None):
    command = [
        RM_path,
        "-bc",
        repo_path,
        divergence_commit_sha,
        cutoff_commit_sha,
        "-json",
        output_json
    ]

    result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
    
def get_refactorings_in_PR(RM_path, repo_path, output_json, timeout, PR_number = None):
    command = [
        RM_path,
        "-gp",
        PR_number,
        timeout,
        "-json",
        output_json
    ]
    
    result = subprocess.run(
        command, stdout= subprocess.PIPE, stderr = subprocess.PIPE, text = True, check = True
    )
    

