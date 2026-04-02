from flask import Flask, request, jsonify, render_template
from zcr_improved import Zcr
from leach import Leach
from config import *
from simulator import Simulator

app = Flask(__name__)

simulator = None
protocol = None


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start():
    global simulator, protocol

    data = request.get_json(silent=True) or {}
    algo = data.get("protocol", "ZCR")

    simulator = Simulator(
        DEPLOYMENT_AREA_WIDTH_M,
        DEPLOYMENT_AREA_HEIGHT_M,
        TOTAL_SENSOR_NODES
    )

    protocol = Leach(CLUSTER_HEAD_PROBABILITY) if algo == "LEACH" else Zcr(CLUSTER_HEAD_PROBABILITY)

    return jsonify(build_response())


@app.route("/api/step", methods=["POST"])
def step():
    global simulator, protocol

    if simulator is None:
        return jsonify({"error": "not started"})

    data = request.get_json(silent=True) or {}
    steps = data.get("steps", 1)

    for _ in range(steps):
        if simulator.alive_node_count == 0:
            break
        simulator.update(protocol)

    return jsonify(build_response())


@app.route("/api/reset", methods=["POST"])
def reset():
    global simulator, protocol
    simulator = None
    protocol = None
    return jsonify({"status": "reset"})


def build_response():
    # dynamic zone
    if hasattr(protocol, "current_radius"):
        zone_radius = float(protocol.current_radius)
    else:
        zone_radius = float(FS_MULTIPATH_THRESHOLD_DISTANCE_M * 1.5)

    return {
        "protocol": protocol.name(),
        "round": simulator.current_round,
        "alive": simulator.alive_node_count,

        "width": float(DEPLOYMENT_AREA_WIDTH_M),
        "height": float(DEPLOYMENT_AREA_HEIGHT_M),

        "nodes": serialize_nodes(),

        "total_energy": float(sum(n.remaining_energy_j for n in simulator.nodes)),

        "alive_history": [int(a) for a in simulator.alive_history],
        "energy_history": [float(e) for e in simulator.energy_history],

        "finished": simulator.alive_node_count == 0
                    or simulator.current_round >= MAX_SIMULATION_ROUNDS,

        "zone_radius": zone_radius,
        "total_nodes": len(simulator.nodes),
        "max_rounds": MAX_SIMULATION_ROUNDS,
        "base_station": [
            float(BASE_STATION_POSITION[0]),
            float(BASE_STATION_POSITION[1])
        ]
    }


def serialize_nodes():
    nodes = simulator.nodes

    # 🔥 IMPORTANT: id → index mapping
    id_to_index = {n.id: i for i, n in enumerate(nodes)}

    result = []

    for i, n in enumerate(nodes):
        target = n.taregt_node_id

        if target is not None:
            target = id_to_index.get(target)

        result.append({
            "id": int(n.id),
            "x": float(n.position[0]),
            "y": float(n.position[1]),
            "alive": bool(n.is_alive),
            "is_ch": bool(n.is_cluster_head),
            "target": target,
            "energy": float(n.remaining_energy_j)
        })

    return result


if __name__ == "__main__":
    app.run(debug=True)
