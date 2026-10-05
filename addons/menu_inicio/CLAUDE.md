# Menú de inicio (módulo de Odoo `menu_inicio`)

Pantalla de inicio a pantalla completa con la cuadrícula de apps y un buscador de menús, en vez del desplegable de
apps de arriba a la izquierda de Community. Al usuario le gusta cómo lo hace Enterprise, pero se queda en Community:
este módulo es **código propio** (no copiar nada de Enterprise: su licencia no lo permite). Solo depende de `web`.

## Cómo funciona

```
static/src/home_menu_state.js   signal compartida isOpen + show/hide/toggle (la leen la barra y el menú)
static/src/home_menu.js/.xml    componente HomeMenu en registry "main_components": cuadrícula de apps
                                (webIconData = data URL; o webIcon "clase,color,fondo"), buscador con ruta
                                "App / Menú / Submenú", flechas + Enter, Esc vuelve a la app actual
static/src/home_menu.scss       overlay fijo bajo la barra (top: --o-navbar-height, z-index 990), degradado
static/src/navbar_patch.js/.xml el botón de apps (web.NavBar.AppsMenu) abre/cierra el menú; con el menú abierto se
                                ocultan nombre y secciones de la app; en móvil «All Apps» del lateral lo abre
static/src/webclient_patch.js   WebClient._loadDefaultApp: en /odoo sin acción se abre el menú en vez de la 1.ª app
```
- Se cierra solo cuando se carga otra acción (bus `ACTION_MANAGER:UI-UPDATED`).
- Sin app abierta (recién entrado) el botón y Esc no lo cierran: no hay nada detrás.
- Todo va en `web.assets_backend` (`static/src/**/*`).

## OWL 3 / Odoo 20 (comprobado)

- Estado: `proxy({...})` en componentes; compartido entre componentes con `signal(v)` de módulo (`s()` lee, `s.set(v)`).
- Refs: `x = signal.ref()` + `t-ref="this.x"`; en plantillas siempre `this.` delante.
- **No** `static props`: OWL 3 lo rechaza y rompe el webclient entero (pantalla en blanco). Si hacen falta props: `useProps`.
- Iconos: `<i class="oi" data-icon="search"/>` (no `oi-search`).
- Patch de getters: añadir un setter vacío al lado (como hace website/navbar.js).

## Probar

En una base de pruebas (`probar-modulo`). Sin la extensión de Chrome conectada, Chromium sin interfaz en Docker:
`node:20-alpine` + `apk add chromium font-noto` + `npm i puppeteer-core@23`, login en `/web/login?db=<bd>_test`
(enviar con Enter: hay varios botones submit), ir a `/odoo` y comprobar `.o_menu_inicio`, recoger `pageerror` y
errores de consola y hacer capturas. Un error de JS en un componente global deja el backend en blanco: mira siempre
la consola.
