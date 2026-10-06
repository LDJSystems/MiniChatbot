(function () {
    "use strict";
    
    const WIDGET_ID = "chatbot-widget";
    const SESSION_KEY = "chatbot_session_uuid";

    /*
     * false = chatbot funcionando sin IA (respuestas locales)
     * true  = utiliza la IA (o el mock, según MOCK_API)
     */
    const USAR_IA = true;

    /*
     * Solo importa si USAR_IA es true.
     *
     * MOCK_API = true  -> respuestas de prueba (archivos JSON)
     * MOCK_API = false -> IA real de Dev A (/api/chat/ask/)
     */
    const MOCK_API = true;

    /*
     * Solo importa si MOCK_API es true.
     *
     * "ok"       -> respuesta normal del bot
     * "fallback" -> el bot "no sabe" y sale el formulario de leads
     */
    const MOCK_SCENARIO = "ok";

    // Carpeta donde Django sirve los JSON de prueba
    const MOCK_BASE = "/static/";

    const PROVINCIAS = [
        "Salamanca",
        "Ávila",
        "Segovia",
        "Valladolid",
        "Zamora",
        "León",
        "Palencia",
        "Burgos",
        "Soria"
    ];

    const CURSOS = [
        "Administración y gestión",
        "Comercio y marketing",
        "Informática y comunicaciones",
        "Sanidad",
        "Otro"
    ];

    const STYLES = `
        :host {
            all: initial;
            font-family: Arial, Helvetica, sans-serif;
        }

        *, *::before, *::after {
            box-sizing: border-box;
        }

        [hidden] {
            display: none !important;
        }

        .chatbot-button {
            position: fixed;
            right: 20px;
            bottom: 20px;
            width: 60px;
            height: 60px;
            border: 0;
            border-radius: 50%;
            background: #0b5cff;
            color: #fff;
            cursor: pointer;
            z-index: 2147483647;
            box-shadow: 0 4px 12px rgba(0,0,0,.3);
        }

        .chatbot-panel {
            position: fixed;
            right: 20px;
            bottom: 90px;
            width: 340px;
            max-width: calc(100vw - 40px);
            height: 500px;
            max-height: 70vh;
            display: flex;
            flex-direction: column;
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,.25);
            overflow: hidden;
            z-index: 2147483647;
        }

        .chatbot-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: #0b5cff;
            color: #fff;
        }

        .chatbot-header h2 {
            margin: 0;
            font-size: 16px;
        }

        .chatbot-close {
            background: none;
            border: 0;
            color: #fff;
            font-size: 22px;
            cursor: pointer;
        }

        .chatbot-messages {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .chatbot-message {
            margin: 0;
            padding: 8px 12px;
            border-radius: 10px;
            max-width: 85%;
            font-size: 14px;
            line-height: 1.4;
            white-space: pre-line;
        }

        .chatbot-message--bot {
            background: #eef1f6;
            color: #222;
            align-self: flex-start;
        }

        .chatbot-message--user {
            background: #0b5cff;
            color: #fff;
            align-self: flex-end;
        }

        .chatbot-options {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            padding: 8px 12px;
            max-height: 160px;
            overflow-y: auto;
        }

        .chatbot-option {
            padding: 6px 12px;
            border: 1px solid #0b5cff;
            border-radius: 16px;
            background: #fff;
            color: #0b5cff;
            cursor: pointer;
            font-size: 13px;
        }

        .chatbot-option:hover {
            background: #0b5cff;
            color: #fff;
        }

        .chatbot-form,
        .chatbot-lead {
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding: 12px;
            border-top: 1px solid #ddd;
        }

        .chatbot-form textarea,
        .chatbot-lead input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 6px;
            font: inherit;
        }

        .chatbot-send,
        .chatbot-lead button {
            padding: 8px;
            border: 0;
            border-radius: 6px;
            background: #0b5cff;
            color: #fff;
            cursor: pointer;
        }

        /* Política de privacidad */

        .chatbot-privacy {
            padding: 8px;
            background: #f5f6f8;
            border-radius: 6px;
            font-size: 12px;
            line-height: 1.4;
            color: #444;
        }

        .chatbot-privacy strong {
            display: block;
            margin-bottom: 6px;
            color: #222;
        }

        .chatbot-privacy p {
            margin: 0 0 6px;
        }

        .chatbot-privacy p:last-child {
            margin-bottom: 0;
        }

        .chatbot-privacy-link {
            color: #0b5cff;
            text-decoration: underline;
        }

        .chatbot-checkbox {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            font-size: 12px;
            line-height: 1.4;
        }

        .chatbot-checkbox input {
            width: auto;
            margin-top: 2px;
            flex: 0 0 auto;
        }

        .chatbot-typing {
            display: flex;
            gap: 4px;
            align-items: center;
            width: fit-content;
            padding: 10px 12px;
            background: #eef1f6;
            border-radius: 10px;
        }

        .chatbot-typing span {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #777;
            animation: typing 1.2s infinite ease-in-out;
        }

        .chatbot-typing span:nth-child(2) {
            animation-delay: .15s;
        }

        .chatbot-typing span:nth-child(3) {
            animation-delay: .3s;
        }

        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
                opacity: .4;
            }

            30% {
                transform: translateY(-4px);
                opacity: 1;
            }
        }

        @media (max-width: 480px) {
            .chatbot-button {
                right: 15px;
                bottom: 15px;
                width: 56px;
                height: 56px;
            }

            .chatbot-panel {
                right: 10px;
                bottom: 80px;
                width: calc(100vw - 20px);
                max-width: none;
                height: 70vh;
            }
        }
    `;

    const TEMPLATE = `
        <style>${STYLES}</style>

        <button
            type="button"
            class="chatbot-button"
            id="chatbot-toggle"
            aria-label="Abrir chatbot"
            aria-expanded="false">
            Chat
        </button>

        <section
            class="chatbot-panel"
            id="chatbot-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="chatbot-title"
            hidden>

            <header class="chatbot-header">
                <h2 id="chatbot-title">Asistente CEFYE</h2>

                <button
                    type="button"
                    class="chatbot-close"
                    id="chatbot-close"
                    aria-label="Cerrar">
                    &times;
                </button>
            </header>

            <div
                class="chatbot-messages"
                id="chatbot-messages"
                aria-live="polite">
            </div>

            <div
                class="chatbot-options"
                id="chatbot-options"
                hidden>
            </div>

            <form
                class="chatbot-form"
                id="chatbot-form"
                hidden>

                <textarea
                    id="chatbot-question"
                    rows="2"
                    placeholder="Escribe tu consulta..."
                    aria-label="Consulta">
                </textarea>

                <button
                    type="submit"
                    class="chatbot-send"
                    id="chatbot-send">
                    Enviar
                </button>
            </form>

            <form
                class="chatbot-lead"
                id="chatbot-lead"
                hidden>

                <div class="chatbot-privacy">

                    <strong>
                        Política de privacidad
                    </strong>

                    <p>
                        Los datos que nos facilites serán tratados por
                        CEFYE con la finalidad de atender tu solicitud
                        de información sobre cursos y formación, así como
                        contactar contigo en relación con dicha solicitud.
                    </p>

                    <p>
                        Puedes consultar información adicional sobre el
                        tratamiento de tus datos, tus derechos y la forma
                        de ejercerlos en nuestra
                        <a
                            href="/politica-de-privacidad/"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="chatbot-privacy-link">
                            Política de Privacidad
                        </a>.
                    </p>

                </div>

                <label class="chatbot-checkbox">

                    <input
                        id="chatbot-privacy-accept"
                        type="checkbox"
                        required>

                    <span>
                        He leído y acepto la política de privacidad.
                    </span>

                </label>

                <label for="chatbot-name">
                    Nombre
                </label>

                <input
                    id="chatbot-name"
                    type="text"
                    autocomplete="name"
                    required>

                <label for="chatbot-email">
                    Correo electrónico
                </label>

                <input
                    id="chatbot-email"
                    type="email"
                    autocomplete="email">

                <label for="chatbot-phone">
                    Teléfono
                </label>

                <input
                    id="chatbot-phone"
                    type="tel"
                    autocomplete="tel">

                <label for="chatbot-colectivo">
                    Colectivo
                </label>

                <input
                    id="chatbot-colectivo"
                    type="text"
                    autocomplete="organization-title"
                    required>

                <button
                    type="submit"
                    id="chatbot-lead-submit">
                    Solicitar información
                </button>

            </form>
        </section>
    `;

    let host = document.getElementById(WIDGET_ID);

    if (!host) {
        host = document.createElement("div");
        host.id = WIDGET_ID;
        document.body.appendChild(host);
    }

    const root =
        host.shadowRoot ||
        host.attachShadow({ mode: "open" });

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
        campoEstudio: null,
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
                : `${Date.now()}-${Math.random()
                    .toString(16)
                    .slice(2)}`;

            sessionStorage.setItem(SESSION_KEY, id);
        }

        return id;
    }

    function addMessage(text, type = "bot") {
        const message = document.createElement("p");

        message.className =
            `chatbot-message chatbot-message--${type}`;

        message.textContent = text;

        ui.messages.appendChild(message);

        ui.messages.scrollTop =
            ui.messages.scrollHeight;
    }

    function showTyping() {
        hideTyping();

        const typing =
            document.createElement("div");

        typing.id = "chatbot-typing";
        typing.className = "chatbot-typing";

        typing.innerHTML =
            "<span></span><span></span><span></span>";

        ui.messages.appendChild(typing);

        ui.messages.scrollTop =
            ui.messages.scrollHeight;
    }

    function hideTyping() {
        const typing =
            $("chatbot-typing");

        if (typing) {
            typing.remove();
        }
    }

    function clearOptions() {
        ui.options.innerHTML = "";
        ui.options.hidden = true;
    }

    function showOptions(options) {
        clearOptions();

        ui.options.hidden = false;

        options.forEach(option => {

            const button =
                document.createElement("button");

            button.type = "button";
            button.className = "chatbot-option";
            button.textContent = option;

            button.onclick = () => {

                if (state.loading) return;

                clearOptions();

                addMessage(option, "user");

                selectOption(option);
            };

            ui.options.appendChild(button);
        });
    }

    function start() {

        state.etapa = "provincia";
        state.provincia = null;
        state.campoEstudio = null;
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
            `👋 ¡Bienvenido al chat de CEFYE!

Estoy aquí para ayudarte a encontrar el curso que mejor se adapte a tus objetivos.

Para empezar, ¿en qué provincia te gustaría realizar la formación?`
        );

        showOptions(PROVINCIAS);
    }

    function selectOption(value) {

        if (state.etapa === "provincia") {

            state.provincia = value;
            state.etapa = "campo";

            addMessage(
                "Perfecto. ¿En qué área formativa estás interesado?"
            );

            showOptions(CURSOS);

            return;
        }

        if (state.etapa === "campo") {

            state.campoEstudio = value;
            state.etapa = "pregunta";

            addMessage(
                "¡Estupendo! Ya puedo ayudarte. ¿Qué dudas tienes o qué información sobre los cursos te gustaría conocer?"
            );

            ui.form.hidden = false;

            ui.question.focus();
        }
    }

    /*
     * CHAT SIN IA
     */
    function respuestaLocal(pregunta) {

        const texto =
            pregunta.toLowerCase();

        if (
            texto.includes("curso") ||
            texto.includes("cursos") ||
            texto.includes("formación")
        ) {

            return {
                entendida: true,

                texto:
                    `Tenemos formación relacionada con ${state.campoEstudio}.

Puedo ayudarte con información sobre los cursos disponibles, requisitos, modalidad y opciones de formación.

¿Qué información concreta quieres conocer?`
            };
        }

        if (
            texto.includes("precio") ||
            texto.includes("coste") ||
            texto.includes("cuesta")
        ) {

            return {
                entendida: true,

                texto:
                    "Podemos informarte sobre los cursos disponibles y sus condiciones. Si quieres información concreta sobre precios, podemos revisar tu caso y contactar contigo."
            };
        }

        if (
            texto.includes("horario") ||
            texto.includes("horarios")
        ) {

            return {
                entendida: true,

                texto:
                    "Los horarios pueden variar según el curso y la modalidad. Puedo ayudarte a identificar la formación que te interesa."
            };
        }

        if (
            texto.includes("online") ||
            texto.includes("presencial")
        ) {

            return {
                entendida: true,

                texto:
                    "La modalidad depende del curso y de la formación disponible en tu provincia. Podemos ayudarte a encontrar las opciones disponibles."
            };
        }

        return {
            entendida: false,

            texto:
                "No he podido identificar exactamente lo que necesitas."
        };
    }

    /*
     * "La camarera": decide de dónde salen las respuestas
     * (archivo de prueba o IA real) y devuelve el JSON tal cual.
     */
    async function pedirRespuestaIA(payload) {

        // Interruptor encendido: respuesta de mentira
        if (MOCK_API) {

            const archivo =
                MOCK_SCENARIO === "fallback"
                    ? "mock_ask_fallback.json"
                    : "mock_ask.json";

            await new Promise(
                resolve => setTimeout(resolve, 700)
            );

            const response =
                await fetch(MOCK_BASE + archivo);

            if (!response.ok) {
                throw new Error(
                    `No se encontró el archivo de prueba: ${archivo}`
                );
            }

            return response.json();
        }

        // Interruptor apagado: IA real
        const response =
            await fetch(
                "/api/chat/ask/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(payload)
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(
                data.error ||
                `Error HTTP ${response.status}`
            );
        }

        return data;
    }

    /*
     * PUNTO DE CONEXIÓN CON LA IA
     */
    async function consultarIA(pregunta) {

        // Sin IA: tus respuestas locales de siempre
        if (!USAR_IA) {

            await new Promise(
                resolve => setTimeout(resolve, 700)
            );

            return respuestaLocal(pregunta);
        }

const data =
            await pedirRespuestaIA({
                pregunta,
                provincia: state.provincia,
                campo_estudio: state.campoEstudio,
                sesion_uuid: state.sessionUuid
            });

        // Traducimos el contrato del mock/IA a las propiedades del widget
        return {
            entendida: 
                data.fallback_activado !== true,

            // Si el fallback está activo O requiere acción comercial, solicitamos datos
            solicitarDatos: 
                data.fallback_activado === true || data.requiere_accion_comercial === true,

            // Lee 'respuesta' o 'texto_respuesta' por si acaso cambia la clave
            texto: 
                data.respuesta || data.texto_respuesta || ""
        };
    }

    async function procesarPregunta(pregunta) {

        state.loading = true;

        ui.send.disabled = true;

        showTyping();

        try {

            const respuesta =
                await consultarIA(pregunta);

            hideTyping();

            if (respuesta.texto) {
                addMessage(respuesta.texto);
            }

            if (respuesta.solicitarDatos === true) {

                showLead();

                return;
            }

            if (respuesta.entendida === false) {

                state.fallbackIntentos++;

                if (
                    state.fallbackIntentos === 1
                ) {

                    addMessage(
                        "Puedes explicármelo de otra forma y volveré a intentarlo."
                    );

                    ui.form.hidden = false;

                    ui.question.focus();

                    return;
                }

                if (
                    state.fallbackIntentos >= 2
                ) {

                    showLead();

                    return;
                }
            }

            state.fallbackIntentos = 0;

            state.etapa = "pregunta";

            ui.form.hidden = false;

            ui.question.focus();

        } catch (error) {

            console.error(
                "Chatbot:",
                error
            );

            hideTyping();

            addMessage(
                "No hemos podido procesar tu consulta. Inténtalo de nuevo."
            );

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

        addMessage(
            "Para poder brindarte más información y ayudarte personalmente, necesitamos algunos datos de contacto."
        );

        addMessage(
            "Por favor, indícanos tu nombre, al menos un medio de contacto (correo o teléfono) y tu colectivo."
        );

        ui.lead.hidden = false;

        ui.privacyAccept.checked = false;

        ui.name.focus();
    }

    async function enviarLead(payload) {

        // En desarrollo podemos probar el contrato completo
        // sin depender todavía del backend de Dev A.
        if (MOCK_API) {

            await new Promise(
                resolve => setTimeout(resolve, 700)
            );

            const response =
                await fetch(
                    MOCK_BASE + "mock_lead.json"
                );

            if (!response.ok) {
                throw new Error(
                    "No se encontró el mock del envío de lead."
                );
            }

            return response.json();
        }

        const response =
            await fetch(
                "/api/chat/lead/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(payload)
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                `Error HTTP ${response.status}`
            );
        }

        return data;
    }

    async function sendLead() {

        state.loading = true;

        ui.leadSubmit.disabled = true;

        showTyping();

        try {

            const payload = {
                nombre:
                    ui.name.value.trim(),

                email:
                    ui.email.value.trim(),

                telefono:
                    ui.phone.value.trim(),

                provincia:
                    state.provincia,

                campo_estudio:
                    state.campoEstudio,

                colectivo:
                    ui.colectivo.value.trim(),

                sesion_uuid:
                    state.sessionUuid,

                consentimiento_rgpd:
                    ui.privacyAccept.checked
            };

            const data =
                await enviarLead(payload);

            hideTyping();

            ui.lead.hidden = true;

            addMessage(
                data.mensaje ||
                "¡Gracias! Hemos recibido tus datos. Nuestro equipo se pondrá en contacto contigo para darte más información."
            );

            state.finalizado = true;

        } catch (error) {

            console.error(
                "Lead:",
                error
            );

            hideTyping();

            addMessage(
                "No hemos podido enviar tus datos. Inténtalo de nuevo."
            );

        } finally {

            state.loading = false;

            ui.leadSubmit.disabled = false;
        }
    }

    ui.form.addEventListener(
        "submit",
        event => {

            event.preventDefault();

            if (
                state.loading ||
                state.finalizado
            ) {
                return;
            }

            const pregunta =
                ui.question.value.trim();

            if (!pregunta) return;

            addMessage(
                pregunta,
                "user"
            );

            ui.question.value = "";

            procesarPregunta(pregunta);
        }
    );

    ui.lead.addEventListener(
        "submit",
        event => {

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

            // Contrato: email requerido si no hay teléfono y viceversa.
            if (!email && !telefono) {
                ui.email.focus();
                addMessage(
                    "Indica al menos un medio de contacto: correo electrónico o teléfono."
                );
                return;
            }

            if (!ui.privacyAccept.checked) {
                ui.privacyAccept.focus();
                return;
            }

            addMessage(
                `Nombre: ${ui.name.value.trim()}`,
                "user"
            );

            if (email) {
                addMessage(
                    `Email: ${email}`,
                    "user"
                );
            }

            if (telefono) {
                addMessage(
                    `Teléfono: ${telefono}`,
                    "user"
                );
            }

            addMessage(
                `Colectivo: ${colectivo}`,
                "user"
            );

            sendLead();
        }
    );

    ui.toggle.addEventListener(
        "click",
        () => {

            // Si el chat está cerrado, lo abrimos
            if (ui.panel.hidden) {

                ui.panel.hidden = false;

                ui.toggle.setAttribute(
                    "aria-expanded",
                    "true"
                );

                // Solo iniciar la conversación si todavía no existe
                if (!ui.messages.children.length) {
                    start();
                }

            } else {

                // Si está abierto, lo minimizamos
                // sin borrar la conversación
                ui.panel.hidden = true;

                ui.toggle.setAttribute(
                    "aria-expanded",
                    "false"
                );
            }
        }
    );

    ui.close.addEventListener(
        "click",
        () => {

            ui.panel.hidden = true;

            ui.toggle.setAttribute(
                "aria-expanded",
                "false"
            );

            ui.toggle.focus();
        }
    );

    ui.question.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                ui.form.requestSubmit();
            }

            if (event.key === "Escape") {

                ui.panel.hidden = true;

                ui.toggle.setAttribute(
                    "aria-expanded",
                    "false"
                );

                ui.toggle.focus();
            }
        }
    );

    state.sessionUuid = getSession();

})();