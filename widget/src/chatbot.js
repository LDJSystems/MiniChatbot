(function () {
    "use strict";

    const WIDGET_ID = "chatbot-widget";
    const SESSION_KEY = "chatbot_session_uuid";

    const STYLES = ` 
        :host {
            all: initial;
            font-family: Arial, Helvetica, sans-serif;
        }
    
        *,
        *::before,
        *::after {
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
            border-radius: 50%;
            border: 0;
            background: #0b5cff;
            color: #fff;
            font-size: 14px;
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
            z-index: 2147483647;
            font-family: Arial, sans-serif;
            overflow: hidden;
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
            white-space: pre-line;
            line-height: 1.4;
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
            background: #fff;
            color: #0b5cff;
            border-radius: 16px;
            cursor: pointer;
            font-size: 13px;
        }

        .chatbot-option:hover,
        .chatbot-option:focus {
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
            padding: 8px;
            font: inherit;
            border: 1px solid #ccc;
            border-radius: 6px;
            box-sizing: border-box;
            width: 100%;
        }

        .chatbot-send,
        .chatbot-lead button {
            padding: 8px;
            border: 0;
            background: #0b5cff;
            color: #fff;
            border-radius: 6px;
            cursor: pointer;
        }

        .chatbot-button:hover {
            transform: scale(1.05);
        }

        .chatbot-button:focus-visible,
        .chatbot-close:focus-visible,
        .chatbot-option:focus-visible,
        .chatbot-send:focus-visible {
            outline: 3px solid rgba(11, 92, 255, .35);
            outline-offset: 2px;
        }

        .chatbot-typing {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 10px 12px;
            background: #eef1f6;
            border-radius: 10px;
            align-self: flex-start;
        }

        .chatbot-typing span {
            width: 6px;
            height: 6px;
            background: #777;
            border-radius: 50%;
            animation: chatbotTyping 1.2s infinite ease-in-out;
        }

        .chatbot-typing span:nth-child(2) {
            animation-delay: .15s;
        }

        .chatbot-typing span:nth-child(3) {
            animation-delay: .3s;
        }

        @keyframes chatbotTyping {
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

    const state = {
        isOpen: false,
        isLoading: false,
        sessionUuid: null,

        etapa: "provincia", // etapas: 'provincia', 'campo_estudio', 'pregunta', 'lead'

        provincia: null,
        campoEstudio: null,
        pregunta: null,

        nombre: null,
        email: null,
        telefono: null,

        fallbackActivado: false,
        fallbackIntentos: 0
    };

    const TEMPLATE = `
        <style>${STYLES}</style>

        <button
            type="button"
            class="chatbot-button"
            id="chatbot-toggle"
            aria-label="Abrir chatbot"
            aria-expanded="false"
            aria-controls="chatbot-panel"
        >
            Chat
        </button>

        <section
            class="chatbot-panel"
            id="chatbot-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="chatbot-title"
            hidden
        >
            <header class="chatbot-header">
                <h2 id="chatbot-title">Asistente CEFYE</h2>

                <button
                    type="button"
                    class="chatbot-close"
                    id="chatbot-close"
                    aria-label="Cerrar chatbot"
                >
                    &times;
                </button>
            </header>

            <div
                class="chatbot-messages"
                id="chatbot-messages"
                aria-live="polite"
                aria-atomic="false"
            ></div>

            <div
                class="chatbot-options"
                id="chatbot-options"
                role="group"
                aria-label="Opciones"
                hidden
            ></div>

            <form class="chatbot-form" id="chatbot-form" hidden>
                <textarea
                    id="chatbot-question"
                    rows="2"
                    placeholder="Escribe tu consulta..."
                    aria-label="Respuesta"
                ></textarea>

                <button
                    type="submit"
                    class="chatbot-send"
                    id="chatbot-send"
                >
                    Enviar
                </button>
            </form>

            <form class="chatbot-lead" id="chatbot-lead" hidden>
                <label for="chatbot-name">Nombre</label>
                <input id="chatbot-name" name="nombre" type="text" autocomplete="name" required>

                <label for="chatbot-email">Email</label>
                <input id="chatbot-email" name="email" type="email" autocomplete="email" required>

                <label for="chatbot-phone">Teléfono</label>
                <input id="chatbot-phone" name="telefono" type="tel" autocomplete="tel" required>

                <button type="submit" id="chatbot-lead-submit">
                    Solicitar contacto
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

    const root = host.shadowRoot || host.attachShadow({ mode: "open" });
    root.innerHTML = TEMPLATE;

    const ui = {
        toggle: root.getElementById("chatbot-toggle"),
        panel: root.getElementById("chatbot-panel"),
        close: root.getElementById("chatbot-close"),

        messages: root.getElementById("chatbot-messages"),
        options: root.getElementById("chatbot-options"),

        form: root.getElementById("chatbot-form"),
        question: root.getElementById("chatbot-question"),
        send: root.getElementById("chatbot-send"),

        lead: root.getElementById("chatbot-lead"),
        name: root.getElementById("chatbot-name"),
        email: root.getElementById("chatbot-email"),
        phone: root.getElementById("chatbot-phone"),
        leadSubmit: root.getElementById("chatbot-lead-submit")
    };

    function createNewSessionUuid() {
        const uuid =
            typeof crypto !== "undefined" &&
            typeof crypto.randomUUID === "function"
                ? crypto.randomUUID()
                : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

        sessionStorage.setItem(SESSION_KEY, uuid);
        return uuid;
    }

    function getSessionUuid() {
        const existing = sessionStorage.getItem(SESSION_KEY);
        return existing ? existing : createNewSessionUuid();
    }

    function addMessage(text, role) {
        const message = document.createElement("p");
        message.className = `chatbot-message chatbot-message--${role}`;
        message.textContent = text;

        ui.messages.appendChild(message);

        setTimeout(() => {
            ui.messages.scrollTop = ui.messages.scrollHeight;
        }, 10);
    }

    /*
     * Muestra la animación de los tres puntos (Escribiendo...)
     */
    function showTyping() {
        hideTyping(); // Previene duplicados

        const typingEl = document.createElement("div");
        typingEl.id = "chatbot-typing";
        typingEl.className = "chatbot-typing";
        typingEl.innerHTML = "<span></span><span></span><span></span>";

        ui.messages.appendChild(typingEl);

        setTimeout(() => {
            ui.messages.scrollTop = ui.messages.scrollHeight;
        }, 10);
    }

    /*
     * Oculta la animación de los tres puntos
     */
    function hideTyping() {
        const typingEl = root.getElementById("chatbot-typing");
        if (typingEl) {
            typingEl.remove();
        }
    }

    function clearOptions() {
        ui.options.innerHTML = "";
        ui.options.hidden = true;
    }

    function renderOptions(options) {
        clearOptions();
        ui.options.hidden = false;

        options.forEach(function (option) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "chatbot-option";
            button.textContent = option;
            button.setAttribute("aria-label", option);

            button.addEventListener("click", function () {
                selectOption(option);
            });

            ui.options.appendChild(button);
        });

        const firstButton = ui.options.querySelector("button");
        if (firstButton) {
            firstButton.focus();
        }
    }

    function selectOption(value) {
        if (state.isLoading) return;

        clearOptions();
        addMessage(value, "user");
        processOptionAnswer(value);
    }

    /*
     * Control del flujo por etapas
     */
    function askNextQuestion() {
        clearOptions();

        if (state.etapa === "provincia") {
            ui.form.hidden = true;
            addMessage(
                `👋 ¡Bienvenido al chat de CEFYE!\nEstoy aquí para ayudarte a encontrar el curso que mejor se adapte a tus objetivos.\nPara empezar, ¿en qué provincia te gustaría realizar la formación?`,
                "bot"
            );
            renderOptions(PROVINCIAS);
            return;
        }

        if (state.etapa === "campo_estudio") {
            ui.form.hidden = true;
            addMessage("Perfecto. ¿En qué área formativa estás interesado?", "bot");
            renderOptions(CURSOS);
            return;
        }

        if (state.etapa === "pregunta") {
            clearOptions();
            addMessage("¡Estupendo! ¿Qué dudas tienes o en qué curso te gustaría obtener más información?", "bot");
            
            // Se habilita la caja de texto para que interactúe la IA
            ui.form.hidden = false;
            ui.question.hidden = false;
            ui.send.hidden = false;
            ui.question.focus();
        }
    }

    function processTextAnswer(value) {
        if (state.etapa === "pregunta") {
            state.pregunta = value;
            sendQuestion();
            return true;
        }
        return false;
    }

    function resetConversation() {
        ui.messages.innerHTML = "";
        clearOptions();

        ui.lead.hidden = true;
        ui.form.hidden = true;

        ui.question.value = "";
        ui.name.value = "";
        ui.email.value = "";
        ui.phone.value = "";

        state.isLoading = false;
        state.etapa = "provincia";
        state.provincia = null;
        state.campoEstudio = null;
        state.pregunta = null;
        state.nombre = null;
        state.email = null;
        state.telefono = null;
        state.fallbackActivado = false;
        state.fallbackIntentos = 0;

        state.sessionUuid = createNewSessionUuid();

        askNextQuestion();
    }

    function open() {
        if (state.isOpen) return;

        resetConversation();
        state.isOpen = true;
        ui.panel.hidden = false;
        ui.toggle.setAttribute("aria-expanded", "true");

        setTimeout(focusFirstElement, 0);
    }

    function close() {
        state.isOpen = false;
        ui.panel.hidden = true;
        ui.toggle.setAttribute("aria-expanded", "false");
        ui.toggle.focus();
    }

    function getFocusableElements() {
        const elements = root.querySelectorAll(
            "button:not([disabled]), textarea:not([disabled]), input:not([disabled])"
        );

        return Array.from(elements).filter(
            element => !element.hidden && element.offsetParent !== null
        );
    }

    function focusFirstElement() {
        const focusable = getFocusableElements();
        if (focusable.length) {
            focusable[1] ? focusable[1].focus() : focusable[0].focus();
        }
    }

    function handleKeyboard(event) {
        if (!state.isOpen) return;

        if (event.key === "Escape") {
            event.preventDefault();
            close();
            return;
        }

        if (
            event.key === "Enter" &&
            root.activeElement === ui.question &&
            !event.shiftKey
        ) {
            event.preventDefault();
            handleSubmit(event);
            return;
        }

        if (event.key !== "Tab") return;

        const focusable = getFocusableElements();
        if (!focusable.length) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const active = root.activeElement;

        if (event.shiftKey && active === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && active === last) {
            event.preventDefault();
            first.focus();
        }
    }

    /*
     * Envía la consulta a la IA backend con animación 'Escribiendo...'
     */
    async function sendQuestion() {
        state.isLoading = true;
        ui.send.disabled = true;

        // Mostrar indicador de 3 puntos escribiendo
        showTyping();

        try {
            const response = await fetch("/api/chat/ask/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    pregunta: state.pregunta,
                    provincia: state.provincia,
                    campo_estudio: state.campoEstudio,
                    sesion_uuid: state.sessionUuid
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `Error HTTP ${response.status}`);
            }

            // Ocultar animacion 'escribiendo' antes de imprimir respuesta
            hideTyping();

            if (data.texto_respuesta) {
                addMessage(data.texto_respuesta, "bot");
            }

            if (data.fallback_activado === true) {
                state.fallbackActivado = true;
                state.etapa = "lead";

                addMessage(
                    "No he podido identificar exactamente lo que necesitas. " +
                    "Para poder ayudarte mejor, podemos ponerte en contacto con nuestro equipo.",
                    "bot"
                );

                addMessage(
                    "Por favor, déjanos tus datos de contacto.",
                    "bot"
                );

                showLeadForm();

                return;
            }

            state.fallbackIntentos = 0;
            state.fallbackActivado = false;
            state.etapa = "pregunta";

            ui.question.focus();

        } catch (error) {
            console.error("Error chatbot:", error);
            hideTyping();
            addMessage(
                "No hemos podido procesar tu consulta. Inténtalo de nuevo.",
                "bot"
            );
        } finally {
            state.isLoading = false;
            ui.send.disabled = false;
        }
    }

        function showLeadForm() {
            ui.form.hidden = true;
            clearOptions();

            ui.lead.hidden = false;

            ui.name.focus();
        }

    async function sendLead() {
        state.isLoading = true;
        ui.leadSubmit.disabled = true;

        showTyping();

        try {
            const response = await fetch("/api/chat/lead/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    nombre: state.nombre,
                    email: state.email,
                    telefono: state.telefono,
                    provincia: state.provincia,
                    campo_estudio: state.campoEstudio,
                    sesion_uuid: state.sessionUuid
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `Error HTTP ${response.status}`);
            }

            hideTyping();

            addMessage(
                data.mensaje ||
                    "Gracias. He recibido tus datos. Se pondrán en contacto contigo.",
                "bot"
            );

            state.etapa = "finalizado";
            ui.lead.hidden = true;

        } catch (error) {
            console.error("Error enviando lead:", error);
            hideTyping();
            addMessage(
                "No hemos podido enviar tus datos. Inténtalo de nuevo.",
                "bot"
            );
        } finally {
            state.isLoading = false;
            ui.leadSubmit.disabled = false;
        }
    }

    function handleSubmit(event) {
        if (event) event.preventDefault();

        if (state.isLoading || state.etapa === "finalizado") return;

        const value = ui.question.value.trim();
        if (!value) return;

        addMessage(value, "user");
        ui.question.value = "";

        processTextAnswer(value);
    }

    function handleLeadSubmit(event) {
        event.preventDefault();

        if (state.isLoading) return;

        const nombre = ui.name.value.trim();
        const email = ui.email.value.trim();
        const telefono = ui.phone.value.trim();

        if (!nombre || !email || !telefono) return;

        state.nombre = nombre;
        state.email = email;
        state.telefono = telefono;

        addMessage(`Nombre: ${nombre}`, "user");
        addMessage(`Email: ${email}`, "user");
        addMessage(`Teléfono: ${telefono}`, "user");

        sendLead();
    }

    function init() {
        state.sessionUuid = getSessionUuid();

        ui.toggle.addEventListener("click", open);
        ui.close.addEventListener("click", close);

        ui.form.addEventListener("submit", handleSubmit);
        ui.lead.addEventListener("submit", handleLeadSubmit);

        root.addEventListener("keydown", handleKeyboard);
    }

    init();
})();