import sys
import json

import requests
import pandas as pd

from filters import INELIGIBLE_PRS


if len(sys.argv) != 2:
    raise ValueError('Must provide a csv file')

CSV_FILE = sys.argv[1]
if not CSV_FILE.endswith('.csv'):
    raise ValueError('File must be a csv')


QUERY = "type:pr created:2023-08-19..2023-09-30 -repo:cc-bhu/github-demo"
LEADERBOARD_FILE = "leaderboard.json"


def generate_query(users):
    """Generate a query string to fetch PR."""
    query = QUERY
    for user in users:
        query += f" author:{user} -user:{user}"

    return query


def get_prs(users):
    """Get PRs for all users."""
    query = generate_query(users)
    page = 1
    prs = []
    while True:
        print(f"Fetching page {page}")
        url = f"https://api.github.com/search/issues?q={query}&per_page=100&page={page}"
        response = requests.get(
            url,
            headers={'Accept': 'application/vnd.github.v3+json'},
            timeout=10
        )

        response.raise_for_status()
        if not response.json()["items"]:
            break

        prs.extend(response.json()["items"])
        page += 1

    return {"total_count": len(prs), "items": prs}


def build_pr_identifier(url):
    """Generate a PR identifier."""

    splits = url.split("/")
    return f"{splits[-4]}/{splits[-3]}#{splits[-1]}"


def _process(prs):
    """Process the pull requests response."""

    # Create a dataframe of all Pull Requests
    df = pd.DataFrame(prs["items"])
    df = df[["id", "title", "html_url", "state", "user", "pull_request", "created_at"]]

    # Extract the user login
    df["user"] = df["user"].apply(lambda x: x["login"])

    # Convert html_url to Pull Request Identifier
    df["ref"] = df["html_url"].apply(lambda x: build_pr_identifier(x))

    # Extract the merged status
    df["isMerged"] = df["pull_request"].apply(lambda x: True if x['merged_at'] else False)
    df["merged_at"] = df["pull_request"].apply(lambda x: x['merged_at'] if x['merged_at'] else None)

    # Convert to datetime
    df["createdAt"] = pd.to_datetime(df["created_at"])
    df["mergedAt"] = pd.to_datetime(df["merged_at"])

    # Drop the unnecessary columns
    df = df.drop(columns=["pull_request", "created_at", "merged_at"])
    df.rename(columns={"html_url": "url"}, inplace=True)

    # Reorder the columns
    df = df[["id", "ref", "title", "url", "state", "user", "isMerged", "createdAt", "mergedAt"]]

    # Filter out the ineligible PRs
    df = df[~df["ref"].isin(INELIGIBLE_PRS)]

    return df


def generate_leaderboard(df, names):
    """Prepare the leaderboard."""

    def create_dict(x, names):
        pulls = x.to_dict(orient="records")
        merged = sum([1 if i["isMerged"] else 0 for i in pulls])
        open = sum([1 if i["state"] == "open" else 0 for i in pulls])

        return {
            "name": names[x.user.iloc[0].lower()]["name"],
            "total": len(x),
            "merged": merged,
            "open": open,
            "completed": merged>=3,
            "pullRequests": pulls
        }

    users = df.groupby("user").apply(
        lambda x: create_dict(x, names)
    ).sort_index(ascending=True)

    # count total merged PRs
    leaderboard = {
        "total": sum(i["total"] for i in users.to_list()),
        "merged": sum(i["merged"] for i in users.to_list()),
        "leaderboard": json.loads(users.to_json())
    }

    return leaderboard


def main():
    """Main function."""
    participants = pd.read_csv(CSV_FILE).dropna()
    users = participants["username"].to_list()
    names = participants.set_index("username").to_dict(orient="index")

    prs = get_prs(users)
    if not prs["total_count"]:
        print("No PRs found")
        return

    df = _process(prs)
    leaderboard = generate_leaderboard(df, names)

    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=4)


if __name__ == "__main__":
    main()
