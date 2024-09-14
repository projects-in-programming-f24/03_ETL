'''
This code is the first step in mimicing the role of a General Manager (GM) of an MLB (Major League Baseball) team to help them choose who are the best players to hire new contracts
This code will prompt the user for the name of their favorite MLB team.
Once that information is stored in the program, using the [API] to gather statistics for players on that team (AVG, OBP, etc).
Then, I will scrape the 'Transactions' page of the team and search for each player's name, which will show how many and what injuries they had throughout the year, including how long they had to stay out for
I'll combine all of this data into a CSV file, which could be passed as input into a machine learning model to help GMs choose which players are the best players to keep on the team in the future, based on strong performance and injury history
'''

import requests
from bs4 import BeautifulSoup
import pandas as pd

'''
ask for user input for their favorite MLB team
have dictionary associating team with MLB team id for the API (ex: Washington Nationals: 120)
access API endpoint: (ex: Washington Nationals: https://statsapi.mlb.com/api/v1/teams/120/roster)
get all players on the team and access their respective player urls (ex: Dylan Crews: https://statsapi.mlb.com/api/v1/people/686611/stats?stats=season)
store all statistics into a dictionary
'''

all_teams = requests.get("https://statsapi.mlb.com/api/v1/teams").json()
team_data = []

while len(team_data) == 0:
    teamName = input("What is your favorite MLB team? ") # enter the team name (yankees, nationals, etc) and not team code (nyy, wsh, etc)
    team_data = [team for team in all_teams['teams'] if 'id' in team['league'].keys() and (team['league']['id'] == 103 or team['league']['id'] == 104) and 'sport' in team.keys() and 'clubName' in team and team['clubName'].lower() == teamName.lower()]

abbreviation = team_data[0]['abbreviation']

roster_url = f'https://statsapi.mlb.com/api/v1/teams/{team_data[0]["id"]}/roster'
players = requests.get(roster_url).json()['roster']
allPlayers = dict()
for player in players:
    followLink = f'https://statsapi.mlb.com/{player["person"]["link"]}/stats?stats=season'
    playerData = requests.get(followLink).json()
    playerStats = playerData['stats'][0]['splits'][0]['stat']
    for v in playerStats:
        try:
            if not isinstance(playerStats[v], (int, float)): playerStats[v] = float(playerStats[v])
        except ValueError:
            pass
    allPlayers[player["person"]["fullName"]] = playerStats

# access the transactions page for the team: https://www.espn.com/mlb/team/transactions/_/name/wsh/ (get 3 letter code for the team)
# anytime "IL" is on a line, and an active player on the roster is on a line, add to that players dictionary

transactionsPage = f"https://www.espn.com/mlb/team/transactions/_/name/{abbreviation}/"
print(transactionsPage)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
} # as default user agent is disallowed in robots.txt

getTransactions = requests.get(f"https://www.espn.com/mlb/team/transactions/_/name/{abbreviation}/", headers=headers)
bs4_parse = BeautifulSoup(getTransactions.text, 'html.parser')
# using inspect element, Table__TD is the class name for all transactions
all_transactions = elements = bs4_parse.find_all('td', class_='Table__TD', 
                              text=lambda text: text and '(IL)' in text and 'Placed' in text and any(key in text for key in allPlayers.keys()))

playerInjuries = dict()
for p in allPlayers:
    playerInjuries[p] = 0

for transaction in all_transactions: # iterating through each transaction to see if valid, and adding to player injury history if so.
    transactionText = transaction.text
    findPlaced, findPlayerInjured = transactionText.rfind('Placed'), transactionText.rfind('-day IL')
    stringToSearch = transactionText[findPlaced + 7:findPlayerInjured-9] # get affected player(s) names
    injured_players = [key for key in allPlayers.keys() if key in stringToSearch] # need list as multiple playres can be put on injured list in one transaction
    for p in injured_players:
        if p in allPlayers: playerInjuries[p] += 1

for p in allPlayers: # concatenate stats and injuries data into one data structure
    allPlayers[p]["numTimesInjured"] = playerInjuries[p]

finalList = []
for p in allPlayers:
    allPlayers[p]["playerName"] = p
    finalList.append(allPlayers[p])

df = pd.DataFrame(finalList)
cols = ['playerName'] + [col for col in df.columns if col != 'playerName'] # make playerName the first column in final CSV/df
df = df[cols]

# clean CSV file - basic cleaning. more advanced cleaning can be done
df.columns = df.columns.str.lower().str.replace(' ', '_')
df = df.apply(lambda col: col.fillna(0) if col.dtype in ['int64', 'float64'] else col.fillna('Unknown')) # unknown is filled if player does not have that statistic (for example, a batter definitely won't have a numberGamesPitched in stat!)

df.to_csv(f'{teamName}_player_stats.csv', index=False)