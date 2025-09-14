// Archivo: static/js/app.js
var app = angular.module('myApp', []);

// --- Controlador para el Login ---
app.controller("loginCtrl", function ($scope, $http) {
    $("#frmLogin").on("submit", function (event) {
        event.preventDefault();
        $.post("/iniciarSesion", $(this).serialize())
            .done(function () {
                window.location.href = '/calculadora';
            })
            .fail(function (response) {
                alert(response.responseJSON.error || "Error al iniciar sesión.");
            });
    });
});

// --- Controlador para la Calculadora ---
app.controller("calculadoraCtrl", function ($scope, $http) {
    let graficoPieInstance;
    let graficoBarrasInstance;

    // Objeto para mapear categorías a colores
    const categoryColors = {
        comida: '#FF6B6B', transporte: '#4ECDC4', entretenimiento: '#45B7D1',
        salud: '#96CEB4', servicios: '#FFEAA7', compras: '#DDA0DD', otros: '#98D8C8'
    };

    function buscarYActualizarTodo() {
        // 1. Actualizar la tabla HTML
        $.get("/tbodyGastos", function (html) {
            $("#tbodyGastos").html(html);
        });

        // 2. Obtener los datos JSON para los resúmenes y gráficos
        $.get("/gastos/json", function (gastos) {
            actualizarResumen(gastos);
            actualizarGraficos(gastos);
        });
    }

    function actualizarResumen(gastos) {
        const total = gastos.reduce((sum, g) => sum + g.amount, 0);
        const count = gastos.length;
        const promedio = count > 0 ? total / count : 0;

        $("#totalGastado").text(`$${total.toFixed(2)}`);
        $("#totalRegistros").text(count);
        $("#promedioGasto").text(`$${promedio.toFixed(2)}`);
    }

    function actualizarGraficos(gastos) {
        // --- Datos para Gráfico de Pie (por categoría) ---
        const pieData = { labels: [], values: [], colors: [] };
        const gastosPorCategoria = {};

        gastos.forEach(gasto => {
            if (!gastosPorCategoria[gasto.category]) {
                gastosPorCategoria[gasto.category] = 0;
            }
            gastosPorCategoria[gasto.category] += gasto.amount;
        });

        for (const categoria in gastosPorCategoria) {
            pieData.labels.push(categoria.charAt(0).toUpperCase() + categoria.slice(1));
            pieData.values.push(gastosPorCategoria[categoria]);
            pieData.colors.push(categoryColors[categoria] || '#CCCCCC');
        }

        // --- Datos para Gráfico de Barras (últimos 7 días) ---
        const barData = { labels: [], values: [] };
        const gastosPorDia = {};
        
        gastos.forEach(gasto => {
            if (!gastosPorDia[gasto.date]) {
                gastosPorDia[gasto.date] = 0;
            }
            gastosPorDia[gasto.date] += gasto.amount;
        });

        const sortedDates = Object.keys(gastosPorDia).sort().slice(-7);
        sortedDates.forEach(date => {
            barData.labels.push(new Date(date + 'T00:00:00').toLocaleDateString('es-ES', { month: 'short', day: 'numeric' }));
            barData.values.push(gastosPorDia[date]);
        });
        
        // --- Dibujar Gráficos ---
        dibujarGraficoPie(pieData);
        dibujarGraficoBarras(barData);
    }

    function dibujarGraficoPie(data) {
        if (graficoPieInstance) graficoPieInstance.destroy();
        const ctx = document.getElementById('graficoPie').getContext('2d');
        graficoPieInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.labels,
                datasets: [{ data: data.values, backgroundColor: data.colors }]
            }
        });
    }

    function dibujarGraficoBarras(data) {
        if (graficoBarrasInstance) graficoBarrasInstance.destroy();
        const ctx = document.getElementById('graficoBarras').getContext('2d');
        graficoBarrasInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{ label: 'Total Gastado', data: data.values, backgroundColor: '#4F46E5' }]
            },
            options: { scales: { y: { beginAtZero: true } } }
        });
    }

    // --- Eventos ---
    // Enviar formulario para agregar gasto
    $("#frmGasto").on("submit", function (event) {
        event.preventDefault();
        $.post("/gasto", $(this).serialize())
            .done(() => {
                this.reset();
                // Pusher se encargará de actualizar
            });
    });

    // Clic en botón de eliminar
    $(document).on("click", ".btn-eliminar", function () {
        const id = $(this).data("id");
        if (confirm(`¿Estás seguro de eliminar el gasto #${id}?`)) {
            $.post("/gasto/eliminar", { id: id });
            // Pusher se encargará de actualizar
        }
    });

    // --- Lógica de Pusher ---
    const pusher = new Pusher('b338714caa5dd2af623d', { cluster: 'us2' }); // RECUERDA Reemplazar con tu KEY
    const channel = pusher.subscribe('canal-gastos');
    channel.bind('evento-actualizacion', function(data) {
        console.log("¡Actualización recibida de Pusher!", data.message);
        buscarYActualizarTodo();
    });

    // Carga inicial de datos al entrar a la página
    buscarYActualizarTodo();
});
