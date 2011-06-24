import garlicsim
from garlicsim_lib.simpacks import prisoner

import csv
import json

NUMBER_OF_PLAYERS = 100
NUMBER_OF_STEPS = 10

csv_filename = "dexy--sim-output.csv"
csv_file = open(csv_filename, "w")
data_writer = csv.writer(csv_file)

data_writer.writerow(["step", "agent", "points", "strategy"])

state = prisoner.State.create_messy_root(NUMBER_OF_PLAYERS)
i = -1

def collect_data():
    for j, agent in enumerate(state.players):
        strategy = agent.__class__.__name__
        data_writer.writerow([i, j, agent.points, strategy])

collect_data()

for i in range(NUMBER_OF_STEPS):
    state = garlicsim.simulate(state)
    collect_data()

csv_file.close()

json_filename = "dexy--sim-params.json"
json_file = open(json_filename, "w")

json.dump({
    'number_of_players' : NUMBER_OF_PLAYERS,
    'number_of_steps' : NUMBER_OF_STEPS
}, json_file)

json_file.close()
