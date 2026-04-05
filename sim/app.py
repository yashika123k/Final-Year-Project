from flask import Flask, jsonify, render_template, request, send_file
import io
import csv
import json

from simulator import Simulator
from leach import Leach
from zcr_improved import Zcr
from config import (
    DEPLOYMENT_AREA_WIDTH_M,
    DEPLOYMENT_AREA_HEIGHT_M,
    TOTAL_SENSOR_NODES,
    CLUSTER_HEAD_PROBABILITY,
    BASE_STATION_POSITION,
    FS_MULTIPATH_THRESHOLD_DISTANCE_M,
    MAX_SIMULATION_ROUNDS,
    ANALYSIS_MAX_ROUNDS,
    ANALYSIS_CACHE_ENABLED,
)

app = Flask(__name__)

sessions: dict[str, dict] = {}
last_compare_result = None
compare_cache: dict[int, dict] = {}


def make_protocol(protocol_name: str):
    return Leach(CLUSTER_HEAD_PROBABILITY) if protocol_name.upper() == "LEACH" else Zcr(CLUSTER_HEAD_PROBABILITY)

def normalize_protocol_name(name: str):
    name = name.upper()
    if name in ["ZCR", "AZC", "AZC-PSO"]:
        return "AZC-PSO"
    return name

def create_session(protocol_name: str, seed: int = 42):
    sim = Simulator(
        DEPLOYMENT_AREA_WIDTH_M,
        DEPLOYMENT_AREA_HEIGHT_M,
        TOTAL_SENSOR_NODES,
        seed=seed
    )
    protocol = make_protocol(protocol_name)

    sessions[protocol_name.upper()] = {
        "sim": sim,
        "protocol": protocol,
        "seed": seed
    }


def get_session(protocol_name: str):
    protocol_name = protocol_name.upper()
    if protocol_name not in sessions:
        create_session(protocol_name, 42)
    return sessions[protocol_name]


def serialize_nodes(sim):
    nodes = sim.nodes
    id_to_index = {n.id: i for i, n in enumerate(nodes)}

    out = []
    for n in nodes:
        target = n.target_node_id
        if target is not None:
            target = id_to_index.get(target)

        out.append({
            "id": int(n.id),
            "x": float(n.position[0]),
            "y": float(n.position[1]),
            "alive": bool(n.is_alive),
            "ch": bool(n.is_cluster_head),
            "target": target,
            "energy": float(max(0.0, n.remaining_energy_j))
        })
    return out


def summarize(sim):
    total_nodes = len(sim.nodes)
    first_dead_round = None
    half_dead_round = None
    last_dead_round = None

    for i, alive in enumerate(sim.alive_history, start=1):
        dead = total_nodes - alive
        if first_dead_round is None and dead >= 1:
            first_dead_round = i
        if half_dead_round is None and alive <= total_nodes / 2:
            half_dead_round = i
        if last_dead_round is None and alive == 0:
            last_dead_round = i

    return {
        "rounds_completed": int(sim.current_round),
        "alive_now": int(sim.alive_node_count),
        "dead_now": int(total_nodes - sim.alive_node_count),
        "first_dead_round": first_dead_round,
        "half_dead_round": half_dead_round,
        "last_dead_round": last_dead_round,
        "total_energy_now": float(sum(max(0.0, n.remaining_energy_j) for n in sim.nodes))
    }


def serialize(sim, protocol):
    zone_radius = float(getattr(protocol, "current_radius", FS_MULTIPATH_THRESHOLD_DISTANCE_M * 1.5))
    return {
        "protocol": protocol.name(),
        "round": int(sim.current_round),
        "alive": int(sim.alive_node_count),
        "dead": int(len(sim.nodes) - sim.alive_node_count),
        "width": float(DEPLOYMENT_AREA_WIDTH_M),
        "height": float(DEPLOYMENT_AREA_HEIGHT_M),
        "nodes": serialize_nodes(sim),
        "alive_history": [int(v) for v in sim.alive_history],
        "dead_history": [int(len(sim.nodes) - v) for v in sim.alive_history],
        "energy_history": [float(v) for v in sim.energy_history],
        "total_energy": float(sum(max(0.0, n.remaining_energy_j) for n in sim.nodes)),
        "summary": summarize(sim),
        "base_station": [
            float(BASE_STATION_POSITION[0]),
            float(BASE_STATION_POSITION[1]),
        ],
        "zone_radius": zone_radius,
        "finished": bool(sim.alive_node_count == 0 or sim.current_round >= MAX_SIMULATION_ROUNDS)
    }


def compare_winner(leach_data, zcr_data):
    l = leach_data["summary"]
    z = zcr_data["summary"]

    score_leach = 0
    score_azc = 0

    # FIRST NODE DEATH 
    if (z["first_dead_round"] or 0) > (l["first_dead_round"] or 0):
        score_azc += 2
    else:
        score_leach += 1

    # HALF NODE DEATH
    if (z["half_dead_round"] or 0) > (l["half_dead_round"] or 0):
        score_azc += 2
    else:
        score_leach += 1

    # NETWORK LIFETIME
    if z["rounds_completed"] > l["rounds_completed"]:
        score_azc += 2
    else:
        score_leach += 1

    # ENERGY LEFT
    if z["total_energy_now"] > l["total_energy_now"]:
        score_azc += 1
    else:
        score_leach += 1

    # CURRENT ALIVE NODES
    if z["alive_now"] > l["alive_now"]:
        score_azc += 2
    else:
        score_leach += 1

    # Energy per node
    if (z["total_energy_now"] / max(1, z["alive_now"])) > (l["total_energy_now"] / max(1, l["alive_now"])):
        score_azc += 1


    # FINAL DECISION
    if score_azc > score_leach:
        return "AZC-PSO"
    else:
        return "LEACH"


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/simulation")
def simulation():
    return render_template("simulation.html")


@app.route("/analysis")
def analysis():
    return render_template("analysis.html")


@app.route("/theory")
def theory():
    return render_template("theory.html")


@app.route("/conclusion")
def conclusion():
    return render_template("conclusion.html")


@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.get_json(silent=True) or {}
    protocol_name = data.get("protocol", "LEACH").upper()
    seed = int(data.get("seed", 42))

    create_session(protocol_name, seed)
    s = get_session(protocol_name)
    return jsonify(serialize(s["sim"], s["protocol"]))


@app.route("/api/state", methods=["POST"])
def api_state():
    data = request.get_json(silent=True) or {}
    protocol_name = data.get("protocol", "LEACH").upper()
    s = get_session(protocol_name)
    return jsonify(serialize(s["sim"], s["protocol"]))


@app.route("/api/step", methods=["POST"])
def api_step():
    data = request.get_json(silent=True) or {}
    protocol_name = data.get("protocol", "LEACH").upper()
    steps = max(1, min(int(data.get("steps", 1)), 25))

    s = get_session(protocol_name)

    for _ in range(steps):
        if s["sim"].alive_node_count == 0 or s["sim"].current_round >= MAX_SIMULATION_ROUNDS:
            break
        s["sim"].update(s["protocol"])

    return jsonify(serialize(s["sim"], s["protocol"]))


@app.route("/api/reset", methods=["POST"])
def api_reset():
    data = request.get_json(silent=True) or {}
    protocol_name = data.get("protocol", "LEACH").upper()
    seed = int(data.get("seed", 42))

    create_session(protocol_name, seed)
    s = get_session(protocol_name)
    return jsonify(serialize(s["sim"], s["protocol"]))


def run_fast_compare(seed: int):
    base_sim = Simulator(
        DEPLOYMENT_AREA_WIDTH_M,
        DEPLOYMENT_AREA_HEIGHT_M,
        TOTAL_SENSOR_NODES,
        seed=seed
    )

    leach_sim = Simulator(
        DEPLOYMENT_AREA_WIDTH_M,
        DEPLOYMENT_AREA_HEIGHT_M,
        TOTAL_SENSOR_NODES,
        nodes=base_sim.nodes
    )
    zcr_sim = Simulator(
        DEPLOYMENT_AREA_WIDTH_M,
        DEPLOYMENT_AREA_HEIGHT_M,
        TOTAL_SENSOR_NODES,
        nodes=base_sim.nodes
    )

    leach_protocol = Leach(CLUSTER_HEAD_PROBABILITY)
    zcr_protocol = Zcr(CLUSTER_HEAD_PROBABILITY)

    while leach_sim.alive_node_count > 0 and leach_sim.current_round < ANALYSIS_MAX_ROUNDS:
        leach_sim.update(leach_protocol)

    while zcr_sim.alive_node_count > 0 and zcr_sim.current_round < ANALYSIS_MAX_ROUNDS:
        zcr_sim.update(zcr_protocol)

    leach_data = serialize(leach_sim, leach_protocol)
    zcr_data = serialize(zcr_sim, zcr_protocol)

    return {
        "seed": seed,
        "leach": leach_data,
        "zcr": zcr_data,
        "winner": compare_winner(leach_data, zcr_data)
    }


@app.route("/api/compare", methods=["POST"])
def api_compare():
    global last_compare_result

    data = request.get_json(silent=True) or {}
    seed = int(data.get("seed", 42))

    if ANALYSIS_CACHE_ENABLED and seed in compare_cache:
        last_compare_result = compare_cache[seed]
        return jsonify(last_compare_result)

    result = run_fast_compare(seed)

    if ANALYSIS_CACHE_ENABLED:
        compare_cache[seed] = result

    last_compare_result = result
    return jsonify(result)


@app.route("/export/csv/<protocol>")
def export_csv(protocol):
    protocol = protocol.upper()
    s = get_session(protocol)
    sim = s["sim"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["round", "alive_nodes", "dead_nodes", "total_energy"])

    if len(sim.alive_history) == 0:
        writer.writerow([0, len(sim.nodes), 0, sum(max(0.0, n.remaining_energy_j) for n in sim.nodes)])
    else:
        for i in range(len(sim.alive_history)):
            alive = sim.alive_history[i]
            dead = len(sim.nodes) - alive
            energy = sim.energy_history[i]
            writer.writerow([i + 1, alive, dead, energy])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{protocol.lower()}_simulation.csv"
    )


@app.route("/export/json/<protocol>")
def export_json(protocol):
    protocol = protocol.upper()
    s = get_session(protocol)
    sim = s["sim"]

    data = {
        "protocol": protocol,
        "round": sim.current_round,
        "alive_history": sim.alive_history,
        "dead_history": [len(sim.nodes) - v for v in sim.alive_history],
        "energy_history": sim.energy_history,
        "summary": summarize(sim),
        "nodes": serialize_nodes(sim)
    }

    return send_file(
        io.BytesIO(json.dumps(data, indent=2).encode()),
        mimetype="application/json",
        as_attachment=True,
        download_name=f"{protocol.lower()}_simulation.json"
    )


@app.route("/export/compare/json")
def export_compare_json():
    global last_compare_result

    if last_compare_result is None:
        return jsonify({"error": "Run comparison first"}), 400

    return send_file(
        io.BytesIO(json.dumps(last_compare_result, indent=2).encode()),
        mimetype="application/json",
        as_attachment=True,
        download_name="compare_result.json"
    )


@app.route("/export/compare/csv")
def export_compare_csv():
    global last_compare_result

    if last_compare_result is None:
        return jsonify({"error": "Run comparison first"}), 400

    leach = last_compare_result["leach"]
    zcr = last_compare_result["zcr"]

    max_len = max(len(leach["alive_history"]), len(zcr["alive_history"]))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "round",
        "leach_alive", "zcr_alive",
        "leach_dead", "zcr_dead",
        "leach_energy", "zcr_energy"
    ])

    for i in range(max_len):
        writer.writerow([
            i + 1,
            leach["alive_history"][i] if i < len(leach["alive_history"]) else "",
            zcr["alive_history"][i] if i < len(zcr["alive_history"]) else "",
            leach["dead_history"][i] if i < len(leach["dead_history"]) else "",
            zcr["dead_history"][i] if i < len(zcr["dead_history"]) else "",
            leach["energy_history"][i] if i < len(leach["energy_history"]) else "",
            zcr["energy_history"][i] if i < len(zcr["energy_history"]) else "",
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="compare_result.csv"
    )


if __name__ == "__main__":
    app.run(debug=True)
