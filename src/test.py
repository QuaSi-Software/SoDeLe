import json

from sodele import SodeleInput, simulate_pv_plants

if __name__ == "__main__":

    data = "./src/calculation_test.json"

    with open(data, "r") as f:
        data = json.load(f)

    sodelInput = SodeleInput(**data)
    res = simulate_pv_plants(sodelInput)