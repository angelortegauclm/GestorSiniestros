document.addEventListener('DOMContentLoaded', async () => {
    let API_URL = "";
    try {
        const configResponse = await fetch('config.json');
        const configData = await configResponse.json();
        API_URL = configData.API_URL;
        console.log("Conectado a la API:", API_URL);
    } catch (error) {
        console.error("Error cargando configuración:", error);
    }

   const form = document.getElementById('formRegistro');
   const btnBuscar = document.getElementById('btnBuscar');
   const mainModal = new bootstrap.Modal(document.getElementById('mainModal'));
   
   const regex = {
       dni: /^[0-9]{8}[A-Z]$/i,
       email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
       matricula: /^[0-9]{4}[A-Z]{3}$/i 
   };

   // --- EVENTO: REGISTRO (POST) ---
   form.addEventListener('submit', async (event) => {
       event.preventDefault();

       if (!validarVacios()) return;

       if (validarFormatos()) {
           const data = capturarDatos();
           
           try {
               // LLAMADA FETCH POST
               const response = await fetch(`${API_URL}crear`, {
                   method: 'POST',
                   headers: {
                       'Content-Type': 'application/json'
                   },
                   body: JSON.stringify(data)
               });

               const result = await response.json();

               if (response.ok) {
                   mostrarModal(
                       "¡Guardado Correctamente!",
                       `<div class="text-center">
                           <p class="text-success fw-bold">${result.mensaje || 'Siniestro procesado'}</p>
                           <p>El expediente de <strong>${data.cliente.nombre}</strong> ya ha sido registrado.</p>
                        </div>`,
                       "bg-success text-white"
                   );
                   form.reset();
               } else {
                   throw new Error(result.error || "Error en el servidor");
               }
           } catch (error) {
               mostrarModal("Error de Envío", `<p class="text-danger">${error.message}</p>`, "bg-danger text-white");
           }
       }
   });

   // --- EVENTO: CONSULTA (GET) ---
   btnBuscar.addEventListener('click', async () => {
       const busqueda = document.getElementById('inputBusqueda').value.trim();
       if (!busqueda) return alert("Introduce un DNI o ID");

       const container = document.getElementById('infoResult');
       container.innerHTML = `<div class="text-center py-3"><div class="spinner-border text-primary"></div><p>Buscando...</p></div>`;
       container.style.display = 'block';

       try {
           // LLAMADA FETCH GET (Enviamos el parámetro de búsqueda en la URL)
           const response = await fetch(`${API_URL}consultar?search=${encodeURIComponent(busqueda)}`);
           const data = await response.json();

           if (response.ok) {
               visualizarInfo(data);
           } else {
               container.innerHTML = `<div class="alert alert-warning">No se encontró ningún expediente con ese ID/DNI.</div>`;
           }
       } catch (error) {
           container.innerHTML = `<div class="alert alert-danger">Error al conectar con la API: ${error.message}</div>`;
       }
   });

   // --- FUNCIONES DE APOYO ---
   function validarVacios() {
       const inputs = form.querySelectorAll('[required]');
       let valido = true;
       inputs.forEach(input => {
           if (!input.value.trim()) {
               input.classList.add('is-invalid'); 
               valido = false;
           } else {
               input.classList.remove('is-invalid');
           }
       });
       if (!valido) alert("Por favor, rellena todos los campos obligatorios.");
       return valido;
   }

   function validarFormatos() {
       const d = document.getElementById('dni').value;
       const e = document.getElementById('email').value;
       const m = document.getElementById('matricula').value;
       if (!regex.dni.test(d)) { alert("DNI inválido"); return false; }
       if (!regex.email.test(e)) { alert("Email inválido"); return false; }
       if (!regex.matricula.test(m)) { alert("Matrícula inválida"); return false; }
       return true;
   }

   function capturarDatos() {
       return {
            cliente: { 
               nombre: document.getElementById('nombre').value.trim(),
               dni: document.getElementById('dni').value.trim(),
               email: document.getElementById('email').value.trim()
           },
           vehiculo: {
               matricula: document.getElementById('matricula').value.trim(),
               marca: document.getElementById('marca').value.trim(),
               modelo: document.getElementById('modelo').value.trim(),
               anio: parseInt(document.getElementById('anio').value) || 0
           },
           poliza: {
               tipo: document.getElementById('tipo_poliza').value,
               limite: parseFloat(document.getElementById('limite').value),
               franquicia: parseFloat(document.getElementById('franquicia').value || 0)
           },
           reparacion: {
               taller: document.getElementById('taller').value.trim(),
               mo: parseFloat(document.getElementById('mano_obra').value || 0),
               piezas: parseFloat(document.getElementById('piezas').value || 0)
           }
       };
   }

   function visualizarInfo(data) {

        const container = document.getElementById('infoResult');
        container.style.display = 'block';
        
        // Mapeo directo de los campos de tu SQL (ajustado por si vienen nulos)
        const mo = parseFloat(data.mano_obra || 0);
        const piezas = parseFloat(data.piezas || 0);
        const total = parseFloat(data.total_coste || (mo + piezas));
        const pagoAseguradora = parseFloat(data.pago_aseguradora || 0);
        const pagoCliente = parseFloat(data.pago_cliente || 0);

        // Badge de estado según el valor de la DB
        let colorEstado = "bg-secondary";
        if (data.estado_reparacion?.toLowerCase().includes("pendiente")) colorEstado = "bg-warning text-dark";
        if (data.estado_reparacion?.toLowerCase().includes("finalizado")) colorEstado = "bg-success";

        // --- DOCUMENTO PDF ---
        let documentoHTML = `<p class="text-muted small italic">No hay documento asociado.</p>`;
        if (data.url_documento) {
            documentoHTML = `
                <div class="mt-4">
                    <h6 class="fw-bold border-bottom pb-1">Documentación Adjunta</h6>
                    <div class="ratio ratio-16x9 border rounded mb-2 shadow-sm bg-dark">
                        <iframe src="${data.url_documento}" title="Documento PDF" loading="lazy"></iframe>
                    </div>
                    <a href="${data.url_documento}" 
                        class="btn btn-sm btn-primary w-100" 
                        download="Siniestro_${data.id_siniestro}.pdf"
                        target="_blank">
                            <i class="bi bi-download"></i> Descargar Informe PDF
                    </a>
                </div>`;
        }

        container.innerHTML = `
            <div class="card border shadow-lg mb-5">
                <div class="card-header  d-flex justify-content-between align-items-center">
                    <span class="fw-bold">EXPEDIENTE #${data.id_siniestro}</span>
                    <span class="badge ${colorEstado}">${data.estado_reparacion || 'Sin estado'}</span>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-6">
                            <small class="text-muted d-block">CLIENTE</small>
                            <strong>${data.nombre}</strong><br>
                            <small>${data.dni} | ${data.email}</small>
                        </div>
                        <div class="col-6 text-end">
                            <small class="text-muted d-block">VEHÍCULO</small>
                            <strong>${data.marca.toUpperCase()} ${data.modelo}</strong><br>
                            <span class="badge bg-light text-dark border">${data.matricula}</span>
                        </div>
                    </div>

                    <div class="p-3 bg-light rounded border mb-3">
                        <h6 class="fw-bold mb-3"><i class="bi bi-tools"></i> Resumen Económico</h6>
                        <table class="table table-sm table-borderless mb-0">
                            <tr><td>Mano de obra</td><td class="text-end">${mo.toFixed(2)}€</td></tr>
                            <tr><td>Piezas / Recambios</td><td class="text-end">${piezas.toFixed(2)}€</td></tr>
                            <tr class="border-top">
                                <td class="fw-bold">COSTE TOTAL SINIESTRO</td>
                                <td class="text-end fw-bold">${total.toFixed(2)}€</td>
                            </tr>
                        </table>
                    </div>

                    <div class="row g-2 mb-3">
                        <div class="col-6">
                            <div class="border rounded p-2 text-center bg-white">
                                <small class="text-muted d-block">Cubre Aseguradora</small>
                                <span class="text-success fw-bold">${pagoAseguradora.toFixed(2)}€</span>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="border rounded p-2 text-center bg-white">
                                <small class="text-muted d-block">Cargo Cliente (Franquicia)</small>
                                <span class="text-danger fw-bold">${pagoCliente.toFixed(2)}€</span>
                            </div>
                        </div>
                    </div>

                    <p class="small text-muted mb-3">
                        <strong>Póliza:</strong> ${data.informacion_poliza} 
                        (Límite: ${parseFloat(data.limite).toFixed(2)}€)
                    </p>

                    ${documentoHTML}
                </div>
            </div>
        `;
    }


   function mostrarModal(titulo, cuerpo, claseHeader) {
       document.getElementById('modalTitle').innerText = titulo;
       document.getElementById('modalBody').innerHTML = cuerpo;
       document.getElementById('modalHeader').className = "modal-header " + claseHeader;
       mainModal.show();
   }

});
