import pandas as pd
import matplotlib.pyplot as plt

TOTAL_NODES = 100


def load_protocol(filename):
    df = pd.read_csv(filename)

    alive = df.groupby("round")["alive_nodes"].mean()

    energy = df.groupby("round")["remaining_energy_j"].sum()

    avg_energy = df.groupby("round")["remaining_energy_j"].mean()

    dead = TOTAL_NODES - alive

    return alive, dead, energy, avg_energy


leach_alive, leach_dead, leach_energy, leach_avg = load_protocol("leach.csv")
zcr_alive, zcr_dead, zcr_energy, zcr_avg = load_protocol("zcr.csv")


# -------------------------
# Graph 1: Alive Nodes
# -------------------------

plt.figure(figsize=(10,6))

plt.plot(leach_alive, label="LEACH", linewidth=2)
plt.plot(zcr_alive, label="ZCR", linewidth=2)

plt.title("Alive Nodes vs Rounds")
plt.xlabel("Rounds")
plt.ylabel("Alive Nodes")

plt.grid(True)
plt.legend()


# -------------------------
# Graph 2: Dead Nodes
# -------------------------

plt.figure(figsize=(10,6))

plt.plot(leach_dead, label="LEACH", linewidth=2)
plt.plot(zcr_dead, label="ZCR", linewidth=2)

plt.title("Dead Nodes vs Rounds")
plt.xlabel("Rounds")
plt.ylabel("Dead Nodes")

plt.grid(True)
plt.legend()


# -------------------------
# Graph 3: Total Energy
# -------------------------

plt.figure(figsize=(10,6))

plt.plot(leach_energy, label="LEACH", linewidth=2)
plt.plot(zcr_energy, label="ZCR", linewidth=2)

plt.title("Total Network Energy vs Rounds")
plt.xlabel("Rounds")
plt.ylabel("Energy (Joules)")

plt.grid(True)
plt.legend()


# -------------------------
# Graph 4: Average Node Energy
# -------------------------

plt.figure(figsize=(10,6))

plt.plot(leach_avg, label="LEACH", linewidth=2)
plt.plot(zcr_avg, label="ZCR", linewidth=2)

plt.title("Average Node Energy vs Rounds")
plt.xlabel("Rounds")
plt.ylabel("Energy per Node")

plt.grid(True)
plt.legend()


plt.show()
