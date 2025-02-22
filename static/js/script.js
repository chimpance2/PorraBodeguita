$(document).ready(function () {
    const claveAdmin = "admin123"; // Clave de administrador

    // Verificar la clave del administrador
    $("#btn-verificar-clave").click(function () {
        let claveIngresada = $("#clave-admin").val().trim();
        if (claveIngresada === claveAdmin) {
            $("#admin-options").show();
        } else {
            alert("Clave incorrecta.");
        }
    });

    // Descargar el PDF de predicciones
    $("#btn-descargar-pdf").click(function () {
        window.location.href = "/descargar_predicciones";
    });

    // Botón para bloquear predicciones
    $("#btn-bloquear").click(function () {
        let claveIngresada = $("#clave-admin").val().trim();
        if (claveIngresada !== claveAdmin) {
            alert("Acceso denegado. Clave incorrecta.");
            return;
        }
        $.ajax({
            url: "/bloquear_predicciones",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ clave: claveIngresada, bloquear: true }),
            success: function (response) {
                alert(response.mensaje);
            },
            error: function (xhr) {
                let error = JSON.parse(xhr.responseText);
                alert(error.error);
            }
        });
    });

    // Cargar los partidos de la semana
    function cargarPartidos() {
        $.get("/obtener_partidos", function (data) {
            if (data.partidos) {
                let partidos = data.partidos;
                $("#partido1-label").text(`${partidos[0].equipo1} vs ${partidos[0].equipo2}`);
                $("#partido2-label").text(`${partidos[1].equipo1} vs ${partidos[1].equipo2}`);
                $("#partido3-label").text(`${partidos[2].equipo1} vs ${partidos[2].equipo2}`);
                let opciones = "";
                for (let i = 0; i <= 10; i++) {
                    opciones += `<option value="${i}">${i}</option>`;
                }
                $("#partido1-local").html(opciones);
                $("#partido1-visitante").html(opciones);
                $("#partido2-local").html(opciones);
                $("#partido2-visitante").html(opciones);
            } else {
                console.error("Error al obtener los partidos.");
            }
        });
    }

    // Cargar las predicciones existentes
    function cargarPredicciones() {
        $.get("/predicciones", function (data) {
            let lista = $("#lista-predicciones");
            lista.empty();
            if (data.predicciones && data.predicciones.length > 0) {
                data.predicciones.forEach(prediccion => {
                    let resultadosFormateados = prediccion.resultados.join("<br>");
                    lista.append(`
                        <li class="list-group-item">
                            <strong style="background-color: yellow; padding: 3px;">
                                ${prediccion.nombre}
                            </strong>
                            <br>
                            ${resultadosFormateados}
                            <br>
                            (${prediccion.fecha} ${prediccion.hora})
                        </li>
                    `);
                });
            } else {
                lista.append(`
                    <li class="list-group-item text-muted">
                        No hay predicciones registradas aún.
                    </li>
                `);
            }
        });
    }

    // Manejar el envío del formulario de predicción
    $("#form-prediccion").submit(function (event) {
        event.preventDefault();
        let nombre = $("#nombre").val().trim().toUpperCase();
        if (!nombre) {
            alert("Por favor, introduce tu nombre.");
            return;
        }
        let resultado1 = $("#partido1-local").val() + ":" + $("#partido1-visitante").val();
        let resultado2 = $("#partido2-local").val() + ":" + $("#partido2-visitante").val();
        let resultado3 = $("#partido3").val();
        let prediccion = {
            nombre: nombre,
            resultados: [resultado1, resultado2, resultado3]
        };
        $.get("/predicciones", function (data) {
            let usuarioExiste = data.predicciones.some((p) => {
                return p.nombre.replace(/[🔹\s]/g, "").includes(nombre);
            });
            let metodo = usuarioExiste ? "PUT" : "POST";
            let url = usuarioExiste ? "/modificar_prediccion" : "/agregar_prediccion";
            $.ajax({
                url: url,
                type: metodo,
                contentType: "application/json",
                data: JSON.stringify(prediccion),
                success: function (response) {
                    alert(response.mensaje + (response.warning ? "\n" + response.warning : ""));
                    cargarPredicciones();
                    $("#form-prediccion")[0].reset();
                },
                error: function (xhr) {
                    let error = JSON.parse(xhr.responseText);
                    alert(error.error);
                }
            });
        });
    });

    // Manejar la actualización de partidos (sección admin)
    $("#form-actualizar-partidos").submit(function (event) {
        event.preventDefault();
        let claveIngresada = $("#clave-admin").val().trim();
        if (claveIngresada !== claveAdmin) {
            alert("Acceso denegado. Clave incorrecta.");
            return;
        }
        let nuevosPartidos = [
            {
                id: 1,
                equipo1: $("#equipo1-partido1").val().trim() || "EquipoA",
                equipo2: $("#equipo2-partido1").val().trim() || "EquipoB"
            },
            {
                id: 2,
                equipo1: $("#equipo1-partido2").val().trim() || "EquipoC",
                equipo2: $("#equipo2-partido2").val().trim() || "EquipoD"
            },
            {
                id: 3,
                equipo1: $("#equipo1-partido3").val().trim() || "EquipoE",
                equipo2: $("#equipo2-partido3").val().trim() || "EquipoF"
            }
        ];
        $.ajax({
            url: "/actualizar_partidos",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ clave: claveIngresada, partidos: nuevosPartidos }),
            success: function (response) {
                alert(response.mensaje);
                cargarPartidos();
                cargarPredicciones();
            },
            error: function (xhr) {
                let error = JSON.parse(xhr.responseText);
                alert(error.error);
            }
        });
    });

    cargarPartidos();
    cargarPredicciones();
});
