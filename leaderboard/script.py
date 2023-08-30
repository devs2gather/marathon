import sys
import json

import requests
import pandas as pd


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
    url = f"https://api.github.com/search/issues?q={query}"
    response = requests.get(
        url,
        headers={'Accept': 'application/vnd.github.v3+json'},
        timeout=10
    )
    response.raise_for_status()
    return response.json()


def _process(prs):
    """Process the pull requests response."""

    # Create a dataframe of all Pull Requests
    df = pd.DataFrame(prs["items"])
    df = df[["id", "title", "html_url", "user", "pull_request"]]

    # Extract the user login
    df["user"] = df["user"].apply(lambda x: x["login"])

    # Extract the merged status
    df["is_merged"] = df["pull_request"].apply(lambda x: True if x['merged_at'] else False)
    df["merged_at"] = df["pull_request"].apply(lambda x: x['merged_at'] if x['merged_at'] else None)
    df["merged_at"] = pd.to_datetime(df["merged_at"])
    df = df.drop(columns=["pull_request"])

    # Rename columns
    df.columns = ["id", "title", "url", "user", "isMerged", "mergedAt"]

    return df


def generate_leaderboard(df, names):
    """Prepare the leaderboard."""

    def create_dict(x, names):
        pulls = x.to_dict(orient="records")

        return {
            "name": names[x.user.iloc[0].lower()]["name"],
            "total": len(x),
            "merged": sum([1 if i["isMerged"] else 0 for i in pulls]),
            "pullRequests": pulls
        }

    return df.groupby("user").apply(
        lambda x: create_dict(x, names)
    ).sort_index(ascending=True).to_json()


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
    leaderboard = json.loads(generate_leaderboard(df, names))
    leaderboard = {
        "total": prs["total_count"],
        "leaderboard": leaderboard
    }

    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=4)


if __name__ == "__main__":
    main()
