(function () {
    "use strict";

    const WIDGET_ID = "chatbot-widget";
    const SESSION_KEY = "chatbot_session_uuid";

    // true = utiliza la API real de Django.
    const USAR_IA = true;
    const MOCK_API = false;
    const MOCK_SCENARIO = "ok";
    const MOCK_BASE = "/static/";
    const API_BASE = "http://127.0.0.1:8000";

    const PROVINCIAS = [
        "Salamanca", "Ávila", "Segovia", "Valladolid", "Zamora",
        "León", "Palencia", "Burgos", "Soria"
    ];

    // build.mjs reemplaza este marcador con chatbot.css.
    const STYLES = "__CHATBOT_CSS__";

    const TEMPLATE = `
        <style>${STYLES}</style>
        <button type="button" class="chatbot-button" id="chatbot-toggle"
            aria-label="Abrir chatbot" aria-expanded="false">Chat</button>

        <section class="chatbot-panel" id="chatbot-panel" role="dialog"
            aria-modal="true" aria-labelledby="chatbot-title" hidden>
            <header class="chatbot-header">
                <h2 id="chatbot-title">Asistente CEFYE</h2>
                <button type="button" class="chatbot-close" id="chatbot-close"
                    aria-label="Cerrar">&times;</button>
            </header>

            <div class="chatbot-messages" id="chatbot-messages" aria-live="polite"></div>
            <div class="chatbot-options" id="chatbot-options" hidden></div>

            <form class="chatbot-form" id="chatbot-form" hidden>
                <textarea id="chatbot-question" rows="2"
                    placeholder="Escribe tu consulta..." aria-label="Consulta"></textarea>
                <button type="submit" class="chatbot-send" id="chatbot-send">Enviar</button>
            </form>

            <form class="chatbot-lead" id="chatbot-lead" hidden>
                <div class="chatbot-privacy">
                    <strong>Política de privacidad</strong>
                    <p>Los datos que nos facilites serán tratados por CEFYE con la finalidad de atender tu solicitud de información sobre cursos y formación, así como contactar contigo en relación con dicha solicitud.</p>
                    <p>Puedes consultar información adicional sobre el tratamiento de tus datos, tus derechos y la forma de ejercerlos en nuestra
                        <a href="/politica-de-privacidad/" target="_blank" rel="noopener noreferrer" class="chatbot-privacy-link">Política de Privacidad</a>.
                    </p>
                </div>
                <label class="chatbot-checkbox">
                    <input id="chatbot-privacy-accept" type="checkbox" required>
                    <span>He leído y acepto la política de privacidad.</span>
                </label>
                <label for="chatbot-name">Nombre</label>
                <input id="chatbot-name" type="text" autocomplete="name" required>
                <label for="chatbot-email">Correo electrónico</label>
                <input id="chatbot-email" type="email" autocomplete="email">
                <label for="chatbot-phone">Teléfono</label>
                <input id="chatbot-phone" type="tel" autocomplete="tel">
                <label for="chatbot-colectivo">Colectivo</label>
                <input id="chatbot-colectivo" type="text" autocomplete="organization-title" required>
                <button type="submit" id="chatbot-lead-submit">Solicitar información</button>
            </form>
        </section>
    `;

    let host = document.getElementById(WIDGET_ID);
    if (!host) {
        host = document.createElement("div");
        host.id = WIDGET_ID;
        document.body.appendChild(host);
    }

    const root = host.shadowRoot || host.attachShadow({ mode: "open" });
    root.innerHTML = TEMPLATE;
    const $ = id => root.getElementById(id);

    const ui = {
        toggle: $("chatbot-toggle"),
        panel: $("chatbot-panel"),
        close: $("chatbot-close"),
        messages: $("chatbot-messages"),
        options: $("chatbot-options"),
        form: $("chatbot-form"),
        question: $("chatbot-question"),
        send: $("chatbot-send"),
        lead: $("chatbot-lead"),
        privacyAccept: $("chatbot-privacy-accept"),
        name: $("chatbot-name"),
        email: $("chatbot-email"),
        phone: $("chatbot-phone"),
        colectivo: $("chatbot-colectivo"),
        leadSubmit: $("chatbot-lead-submit")
    };

    const state = {
        etapa: "provincia",
        provincia: null,
        sessionUuid: null,
        loading: false,
        finalizado: false,
        fallbackIntentos: 0
    };

    function getSession() {
        let id = sessionStorage.getItem(SESSION_KEY);
        if (!id) {
            id = crypto.randomUUID
                ? crypto.randomUUID()
                : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
            sessionStorage.setItem(SESSION_KEY, id);
        }
        return id;
    }

    function addMessage(text, type = "bot") {
        const message = document.createElement("p");
        message.className = `chatbot-message chatbot-message--${type}`;
        // Texto plano de manera intencionada: no se interpreta HTML del modelo.
        message.textContent = String(text ?? "");
        ui.messages.appendChild(message);
        ui.messages.scrollTop = ui.messages.scrollHeight;
    }

    function textoCurso(valor, limite = 800) {
        if (valor === null || valor === undefined) return "";

        // Decodifica entidades HTML sin insertar el contenido como HTML visible.
        const decodificador = document.createElement("textarea");
        decodificador.innerHTML = String(valor);

        return decodificador.value
            .replace(/<[^>]*>/g, " ")
            .replace(/[\u200B-\u200F\uFEFF\u00A0]/g, " ")
            .replace(/\s+/g, " ")
            .trim()
            .slice(0, limite);
    }

    function limpiarContenidoCurso(valor, titulo = "", limite = 500) {
        // El campo contenido suele contener texto extraído de la página web,
        // incluidos menús, metadatos y texto duplicado.
        let texto = textoCurso(valor, 6000);
        if (!texto) return "";

        // Retirar la parte auxiliar de navegación de la página.
        const cortesNavegacion = [
            /¿?\s*quieres\s+más\s+información\??/i,
            /\bsign\s*in\b/i,
            /\breset\s+password\b/i
        ];

        for (const patron of cortesNavegacion) {
            const indice = texto.search(patron);
            if (indice >= 0) texto = texto.slice(0, indice).trim();
        }

        // En contenidos con temario, priorizar el temario sobre los metadatos.
        const marcadorTemario = /(?:^|\s)(?:1\.\s*(?:competencias|contenidos|objetivos|m[oó]dulo|unidad|temario|bloque|actividades)|temario\s*:|contenidos?\s+(?:del\s+curso|del\s+m[oó]dulo)|objetivos?\s+del\s+curso)\b/i;
        const coincidenciaTemario = marcadorTemario.exec(texto);

        if (coincidenciaTemario) {
            texto = texto.slice(coincidenciaTemario.index).trim();

            // Esta frase suele cerrar el temario y preceder a metadatos repetidos.
            const finTemario = texto.search(/\bSin\s+requisitos\s+de\s+acceso\b/i);
            if (finTemario >= 0) texto = texto.slice(0, finTemario).trim();
        } else {
            // Quitar el título repetido al comienzo aunque la web haya variado
            // los espacios alrededor de guiones o signos de puntuación.
            const tituloLimpio = textoCurso(titulo, 250);
            if (tituloLimpio) {
                const escaparRegex = valor => valor.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
                const tituloPattern = escaparRegex(tituloLimpio).replace(/\s+/g, "\\s*");
                const regexTitulo = new RegExp("^\\s*" + tituloPattern + "\\s*[:—–.\\-]*\\s*", "i");
                texto = texto.replace(regexTitulo, "").trim();
            }

            // Si solo queda el bloque de metadatos del scraping, no lo presentamos
            // como si fuera una descripción del curso.
            const primerDatoScraping = /\b(?:IMPARTIDO\s+POR|ESPECIALIDAD\s+FORMATIVA|PERSONAS\s+DESEMPLEADAS\s+Y\s+TRABAJADORAS|SIGN\s*IN|RESET\s+PASSWORD)\b/i.exec(texto);
            if (primerDatoScraping) {
                texto = texto.slice(0, primerDatoScraping.index).trim();
            }
        }

        texto = texto
            .replace(/\b(?:Provincia|Localidad|Modalidad|Duraci[oó]n|Colectivo|Enlace\s+oficial)\s*:\s*.*$/i, "")
            .replace(/\s+/g, " ")
            .trim()
            .replace(/^[-–—|;,\s]+|[-–—|;,\s]+$/g, "");

        if (!texto) return "";
        if (texto.length > limite) {
            const corte = texto.lastIndexOf(" ", limite);
            texto = texto.slice(0, corte > limite * 0.6 ? corte : limite).trimEnd() + "…";
        }

        return texto;
    }

    function addCourseCards(cursos) {
        if (!Array.isArray(cursos) || cursos.length === 0) return;

        const listado = document.createElement("div");
        listado.className = "chatbot-courses";
        listado.setAttribute("aria-label", "Cursos disponibles");

        cursos.forEach((curso, indice) => {
            const titulo = textoCurso(curso.titulo, 250) || "Curso sin título identificado";
            const tarjeta = document.createElement("article");
            tarjeta.className = "chatbot-course-card";

            const encabezado = document.createElement("button");
            encabezado.type = "button";
            encabezado.className = "chatbot-course-title";
            encabezado.textContent = `${indice + 1}. ${titulo}`;
            encabezado.setAttribute("aria-expanded", "false");

            const ubicacion = [
                textoCurso(curso.localidad, 120),
                textoCurso(curso.provincia, 120)
            ].filter(Boolean).join(", ");

            const meta = document.createElement("div");
            meta.className = "chatbot-course-meta";
            meta.textContent = ubicacion;

            const detalles = document.createElement("div");
            detalles.className = "chatbot-course-details";
            detalles.hidden = true;

            encabezado.addEventListener("click", () => {
                detalles.hidden = !detalles.hidden;
                encabezado.setAttribute("aria-expanded", String(!detalles.hidden));
            });

            const campos = [
                ["contenido", "Descripción"],
                ["objetivos", "Objetivos"],
                ["competencias", "Competencias"],
                ["familia_profesional", "Familia profesional"],
                ["sector", "Sector profesional"],
                ["destinatarios", "Destinatarios"],
                ["colectivo", "Colectivo"],
                ["duracion", "Duración"],
                ["modalidad", "Modalidad"],
                ["requisitos", "Requisitos"],
                ["certificado", "Certificado"],
                ["fecha_inicio", "Fecha de inicio"],
                ["horario", "Horario"],
                ["precio", "Precio"]
            ];

            campos.forEach(([clave, etiqueta]) => {
                const valor = clave === "contenido"
                    ? limpiarContenidoCurso(curso[clave], curso.titulo, 500)
                    : textoCurso(curso[clave]);
                if (!valor) return;

                // Evita mostrar dos veces el mismo colectivo/destinatario.
                if (clave === "colectivo") {
                    const destinatarios = textoCurso(curso.destinatarios);
                    if (destinatarios && destinatarios.toLocaleLowerCase() === valor.toLocaleLowerCase()) {
                        return;
                    }
                }

                const fila = document.createElement("div");
                fila.className = "chatbot-course-row";
                const nombreCampo = document.createElement("strong");
                nombreCampo.textContent = `${etiqueta}: `;
                const valorCampo = document.createElement("span");
                valorCampo.textContent = valor;
                fila.append(nombreCampo, valorCampo);
                detalles.appendChild(fila);
            });

            if (!detalles.childElementCount) {
                const aviso = document.createElement("p");
                aviso.className = "chatbot-course-row chatbot-course-empty";
                aviso.textContent = "La ficha disponible no contiene más detalles.";
                detalles.appendChild(aviso);
            }

            const acciones = document.createElement("div");
            acciones.className = "chatbot-course-actions";
            const urlTexto = textoCurso(curso.url_oficial, 2000);

            if (urlTexto) {
                try {
                    const url = new URL(urlTexto);
                    if (["https:", "http:"].includes(url.protocol)) {
                        const enlace = document.createElement("a");
                        enlace.className = "chatbot-course-link";
                        enlace.href = url.href;
                        enlace.target = "_blank";
                        enlace.rel = "noopener noreferrer";
                        enlace.textContent = "Consultar ficha oficial";
                        acciones.appendChild(enlace);
                    }
                } catch (_) {
                    // No mostrar como enlace una URL mal formada.
                }
            }

            const consultar = document.createElement("button");
            consultar.type = "button";
            consultar.className = "chatbot-course-ask";
            consultar.textContent = "Preguntar sobre este curso";
            consultar.addEventListener("click", () => {
                if (state.loading || state.finalizado) return;
                clearOptions();
                ui.lead.hidden = true;
                ui.form.hidden = false;
                const preguntaCurso = `Quiero más información sobre: ${titulo}`;
                addMessage(preguntaCurso, "user");
                procesarPregunta(preguntaCurso);
            });
            acciones.appendChild(consultar);
            detalles.appendChild(acciones);

            tarjeta.append(encabezado, meta, detalles);
            listado.appendChild(tarjeta);
        });

        ui.messages.appendChild(listado);
        ui.messages.scrollTop = ui.messages.scrollHeight;
    }

    function showTyping() {
        hideTyping();
        const typing = document.createElement("div");
        typing.id = "chatbot-typing";
        typing.className = "chatbot-typing";
        typing.innerHTML = "<span></span><span></span><span></span>";
        ui.messages.appendChild(typing);
        ui.messages.scrollTop = ui.messages.scrollHeight;
    }

    function hideTyping() {
        const typing = $("chatbot-typing");
        if (typing) typing.remove();
    }

    function clearOptions() {
        ui.options.innerHTML = "";
        ui.options.hidden = true;
    }

    function showOptions(options) {
        clearOptions();
        ui.options.hidden = false;
        options.forEach(option => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "chatbot-option";
            button.textContent = option;
            button.addEventListener("click", () => {
                if (state.loading) return;
                clearOptions();
                addMessage(option, "user");
                selectOption(option);
            });
            ui.options.appendChild(button);
        });
    }

    function start() {
        state.etapa = "provincia";
        state.provincia = null;
        state.fallbackIntentos = 0;
        state.finalizado = false;
        ui.messages.innerHTML = "";
        clearOptions();
        ui.form.hidden = true;
        ui.lead.hidden = true;
        ui.privacyAccept.checked = false;
        ui.name.value = "";
        ui.email.value = "";
        ui.phone.value = "";
        ui.colectivo.value = "";

        addMessage(
            "👋 ¡Bienvenido al chat de CEFYE!\n\n" +
            "Estoy aquí para ayudarte a encontrar el curso que mejor se adapte a tus objetivos.\n\n" +
            "Para empezar, ¿en qué provincia te gustaría realizar la formación?"
        );
        showOptions(PROVINCIAS);
    }

    function selectOption(value) {
        if (state.etapa !== "provincia") return;
        state.provincia = value;
        state.etapa = "pregunta";
        ui.form.hidden = false;
        addMessage(`Perfecto. ¿Qué formación te interesa buscar en ${value}?`);
        procesarPregunta("Consulta automatica de catálogo");
    }

    function respuestaLocal(pregunta) {
        const texto = pregunta.toLowerCase();
        if (texto.includes("curso") || texto.includes("cursos") || texto.includes("formación")) {
            return {
                entendida: true,
                texto: "Puedo ayudarte con información sobre cursos disponibles, requisitos, modalidad y opciones de formación. ¿Qué temática o curso buscas?",
                cursos: []
            };
        }
        return {
            entendida: true,
            texto: "No he podido identificar exactamente lo que necesitas. ¿Qué área formativa te interesa?",
            cursos: []
        };
    }

    async function pedirRespuestaIA(payload) {
        if (MOCK_API) {
            const archivo = MOCK_SCENARIO === "fallback"
                ? "mock_ask_fallback.json"
                : "mock_ask.json";
            await new Promise(resolve => setTimeout(resolve, 700));
            const response = await fetch(MOCK_BASE + archivo);
            if (!response.ok) throw new Error(`No se encontró el archivo de prueba: ${archivo}`);
            return response.json();
        }

        const response = await fetch(API_BASE + "/api/chat/ask/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) {
            if (response.status === 429) {
                throw new Error("Has realizado demasiadas consultas seguidas. Por favor, espera un minuto.");
            }
            throw new Error(data.error || `Error HTTP ${response.status}`);
        }
        return data;
    }

    async function consultarIA(pregunta) {
        if (!USAR_IA) {
            await new Promise(resolve => setTimeout(resolve, 400));
            return respuestaLocal(pregunta);
        }

        const filtros = state.provincia ? { provincia: state.provincia } : {};
        const data = await pedirRespuestaIA({
            pregunta,
            provincia: state.provincia,
            filtros,
            sesion_uuid: state.sessionUuid
        });

        const texto = data.respuesta || data.texto_respuesta || "";
        return {
            entendida: Boolean(texto),
            // Una respuesta fallback no debe abrir el formulario de contacto
            // automáticamente. Solo lo activa una decisión explícita del backend.
            solicitarDatos: data.requiere_accion_comercial === true,
            texto,
            cursos: Array.isArray(data.cursos) ? data.cursos : []
        };
    }

    async function procesarPregunta(pregunta) {
        state.loading = true;
        ui.send.disabled = true;
        showTyping();

        try {
            const respuesta = await consultarIA(pregunta);
            hideTyping();

            if (respuesta.texto) addMessage(respuesta.texto);
            if (respuesta.cursos && respuesta.cursos.length > 0) {
                addCourseCards(respuesta.cursos);
            }

            if (respuesta.solicitarDatos === true) {
                showLead();
                return;
            }

            state.fallbackIntentos = 0;
            state.etapa = "pregunta";
            ui.form.hidden = false;
            ui.question.focus();
        } catch (error) {
            console.error("Chatbot:", error);
            hideTyping();
            addMessage(error.message || "No hemos podido procesar tu consulta. Inténtalo de nuevo.");
            ui.form.hidden = false;
            ui.question.focus();
        } finally {
            state.loading = false;
            ui.send.disabled = false;
        }
    }

    function showLead() {
        ui.form.hidden = true;
        clearOptions();
        addMessage("Para poder brindarte más información y ayudarte personalmente, necesitamos algunos datos de contacto.");
        addMessage("Por favor, indícanos tu nombre, al menos un medio de contacto (correo o teléfono) y tu colectivo.");
        ui.lead.hidden = false;
        ui.privacyAccept.checked = false;
        ui.name.focus();
    }

    async function enviarLead(payload) {
        if (MOCK_API) {
            await new Promise(resolve => setTimeout(resolve, 700));
            const response = await fetch(MOCK_BASE + "mock_lead.json");
            if (!response.ok) throw new Error("No se encontró el mock del envío de lead.");
            return response.json();
        }

        const response = await fetch(API_BASE + "/api/chat/lead/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Error HTTP ${response.status}`);
        return data;
    }

    async function sendLead() {
        state.loading = true;
        ui.leadSubmit.disabled = true;
        showTyping();
        try {
            const payload = {
                nombre: ui.name.value.trim(),
                email: ui.email.value.trim(),
                telefono: ui.phone.value.trim(),
                provincia: state.provincia,
                colectivo: ui.colectivo.value.trim(),
                sesion_uuid: state.sessionUuid,
                consentimiento_rgpd: ui.privacyAccept.checked
            };
            const data = await enviarLead(payload);
            hideTyping();
            ui.lead.hidden = true;
            addMessage(data.mensaje || "¡Gracias! Hemos recibido tus datos. Nuestro equipo se pondrá en contacto contigo para darte más información.");
            state.finalizado = true;
        } catch (error) {
            console.error("Lead:", error);
            hideTyping();
            addMessage("No hemos podido enviar tus datos. Inténtalo de nuevo.");
        } finally {
            state.loading = false;
            ui.leadSubmit.disabled = false;
        }
    }

    ui.form.addEventListener("submit", event => {
        event.preventDefault();
        if (state.loading || state.finalizado) return;
        const pregunta = ui.question.value.trim();
        if (!pregunta) return;
        addMessage(pregunta, "user");
        ui.question.value = "";
        procesarPregunta(pregunta);
    });

    ui.lead.addEventListener("submit", event => {
        event.preventDefault();
        if (state.loading) return;

        const nombre = ui.name.value.trim();
        const email = ui.email.value.trim();
        const telefono = ui.phone.value.trim();
        const colectivo = ui.colectivo.value.trim();

        if (!nombre || !colectivo) {
            if (!nombre) ui.name.focus();
            else ui.colectivo.focus();
            return;
        }
        if (!email && !telefono) {
            ui.email.focus();
            addMessage("Indica al menos un medio de contacto: correo electrónico o teléfono.");
            return;
        }
        if (!ui.privacyAccept.checked) {
            ui.privacyAccept.focus();
            return;
        }

        addMessage(`Nombre: ${nombre}`, "user");
        if (email) addMessage(`Email: ${email}`, "user");
        if (telefono) addMessage(`Teléfono: ${telefono}`, "user");
        addMessage(`Colectivo: ${colectivo}`, "user");
        sendLead();
    });

    ui.toggle.addEventListener("click", () => {
        if (ui.panel.hidden) {
            ui.panel.hidden = false;
            ui.toggle.setAttribute("aria-expanded", "true");
            if (!ui.messages.children.length) start();
        } else {
            ui.panel.hidden = true;
            ui.toggle.setAttribute("aria-expanded", "false");
        }
    });

    ui.close.addEventListener("click", () => {
        ui.panel.hidden = true;
        ui.toggle.setAttribute("aria-expanded", "false");
        ui.toggle.focus();
    });

    ui.question.addEventListener("keydown", event => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            ui.form.requestSubmit();
        }
        if (event.key === "Escape") {
            ui.panel.hidden = true;
            ui.toggle.setAttribute("aria-expanded", "false");
            ui.toggle.focus();
        }
    });

    state.sessionUuid = getSession();
})();