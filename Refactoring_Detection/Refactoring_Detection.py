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

# TODO
def get_PR_commit_range(repo_path):
    pass

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
    
def get_refactorings_in_PR_from_remote(RM_path, git_URL, PR_number, timeout, output_json):
    """
    Retreives the refactorings within a PR in a remote Github repo, 
    and places the results into a json file.

    IMPORTANT
    ---------
    In order to not get rate limited easily, place a personal 
    github token in a github-oauth.properties file. Further
    instructions are in "github-oauth.properties.template" which
    is located in the same directory as this file.

    Parameters
    ----------
    RM_path :       Path to RefactoringMiner
    git_URL :       URL of the target Github repository
    PR_number :     The number associated with the target pull request
    timeout :       How long should RefactoringMiner spend on each commit
                    before it times out and does not continue with that
                    commit anymore.
    output_json:    The address of a json file which will contain the results
                    of RefactoringMiner.
    Returns
    -------
    result :        The result that RefactoringMiner found. This is extracted
                    from the saved output json and returned for convenience.
    """
    command = [
        RM_path,
        "-gp",
        git_URL,
        str(PR_number),
        str(timeout),
        "-json",
        output_json
    ]
    
    try:
        subprocess.run(
            command, stdout= subprocess.PIPE, stderr = subprocess.PIPE, text = True, check = True
        )
        with open(output_json, 'r', encoding = 'utf-8') as result_file:
            result = json.load(result_file)
    except subprocess.CalledProcessError as e:
        print('************************\n')
        print(f'Exit Code: {e.returncode}')
        print(f'RefactoringMiner Error Output:\n{e.stderr}')
        print('************************\n')
        result = {}

    return result

#TODO
def get_refactorings_in_PR_from_local(RM_path, repo_path, PR_number, output_json):
    """
    Retreives the refactorings within a PR in a local git repo, 
    and places the results into a json file.

    Parameters
    ----------
    RM_path :       Path to RefactoringMiner
    repo_path:      Path to local git repository
    PR_number :     The number associated with the target pull request
    output_json:    The address of a json file which will contain the results
                    of RefactoringMiner.
    Returns
    -------
    result :        The result that RefactoringMiner found. This is extracted
                    from the saved output json and returned for convenience.
    """
    pass