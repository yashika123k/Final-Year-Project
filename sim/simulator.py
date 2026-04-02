from node import Node


class Simulator:
    def __init__(
        self,
        width: float,
        height: float,
        node_count: int,
        seed: int | None = None,
        nodes: list[Node] | None = None
    ):
        if nodes is not None:
            self.nodes = [n.clone() for n in nodes]
        else:
            self.nodes = Node.create_wsn(width, height, node_count, seed=seed)

        self.current_round: int = 0
        self.alive_node_count: int = sum(1 for n in self.nodes if n.is_alive)

        self.alive_history: list[int] = []
        self.energy_history: list[float] = []

    def update(self, protocol) -> None:
        self.current_round += 1
        protocol.run_round(self)

        total_energy = sum(max(0.0, node.remaining_energy_j) for node in self.nodes)
        self.alive_history.append(self.alive_node_count)
        self.energy_history.append(total_energy)
