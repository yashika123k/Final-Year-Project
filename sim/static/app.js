let running = false

const canvas = document.getElementById("canvas")
const ctx = canvas.getContext("2d")

const graphCtx = document.getElementById("graph").getContext("2d")

// =====================
// GRAPH
// =====================
let chart = new Chart(graphCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Alive Nodes',
            data: [],
            borderWidth: 2
        }]
    }
})


// =====================
// START SIM
// =====================
function startSim(algo){

    fetch("/api/start", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({protocol: algo})
    })

    running = true

    chart.data.labels = []
    chart.data.datasets[0].data = []
    chart.update()

    loop()
}


// =====================
// LOOP
// =====================
async function loop(){

    if(!running) return

    let res = await fetch("/api/step", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({steps: 1})
    })

    let data = await res.json()

    // DEBUG (optional)
    // console.log(data)

    draw(data)
    updateGraph(data)

    if(!data.finished){
        setTimeout(loop, 100)
    } else {
        running = false
    }
}


// =====================
// DRAW
// =====================
function draw(data){

    ctx.clearRect(0,0,800,500)

    let scaleX = 800 / 500
    let scaleY = 500 / 500

    // =====================
    // BASE STATION
    // =====================
    let bsx = data.base_station[0] * scaleX
    let bsy = data.base_station[1] * scaleY

    // =====================
    // ZONE CIRCLE
    // =====================
    if(data.zone_radius !== undefined){

        let zone_radius = data.zone_radius * scaleX

        ctx.strokeStyle = "rgba(100,100,255,0.5)"
        ctx.beginPath()
        ctx.arc(bsx, bsy, zone_radius, 0, Math.PI*2)
        ctx.stroke()
    }

    // =====================
    // LINKS
    // =====================
    data.nodes.forEach(n => {

        if(!n.alive) return

        let x = n.x * scaleX
        let y = n.y * scaleY

        // 🔥 HANDLE TYPO (target vs taregt)
        let targetId = (n.target !== undefined) ? n.target : n.taregt_node_id

        if(targetId !== null && targetId !== undefined){

            let target = data.nodes[targetId]

            let tx = target.x * scaleX
            let ty = target.y * scaleY

            // 🔵 CH → CH relay
            if(n.is_ch){
                ctx.strokeStyle = "#00ffcc"
            }
            // ⚪ Node → CH
            else{
                ctx.strokeStyle = "#666"
            }

            ctx.beginPath()
            ctx.moveTo(x,y)
            ctx.lineTo(tx,ty)
            ctx.stroke()

        } else {

            // 🟡 ANY → BASE STATION
            ctx.strokeStyle = "#ffcc00"

            ctx.beginPath()
            ctx.moveTo(x,y)
            ctx.lineTo(bsx,bsy)
            ctx.stroke()
        }
    })


    // =====================
    // NODES
    // =====================
    data.nodes.forEach(n => {

        let x = n.x * scaleX
        let y = n.y * scaleY

        if(!n.alive){
            ctx.fillStyle = "red"
        } 
        else if(n.is_ch){
            ctx.fillStyle = "lime"
        } 
        else{
            ctx.fillStyle = "white"
        }

        ctx.beginPath()
        ctx.arc(x,y,4,0,Math.PI*2)
        ctx.fill()
    })


    // =====================
    // BASE STATION DRAW
    // =====================
    ctx.fillStyle = "#00aaff"
    ctx.fillRect(bsx-6, bsy-6, 12, 12)
}


// =====================
// GRAPH UPDATE
// =====================
function updateGraph(data){

    chart.data.labels.push(data.round)
    chart.data.datasets[0].data.push(data.alive)

    chart.update()
}
