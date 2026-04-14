/** @odoo-module */

import {browser} from "@web/core/browser/browser"
import {Component, useEnv} from "@odoo/owl"

export class NavBar extends Component {
    static template = "eusign_cp.owl_navbar"
    static props = {
        loaded: {type: Boolean, default: false},
        status_key: {type: String, optional: true},
    }

    toggleMenu(ev) {
        const allPanels = document.getElementsByClassName("nav-link");
        const id = ev.target.id;

        if (id === "home") {
            browser.location.href = '/';
            return;
        }

        Array.from(allPanels).forEach(panel => panel.classList.remove("active"));

        this.sharedState.signmode = id === "sign";
        ev.target.classList.toggle("active");
    }

    setup() {
        this.env = useEnv()
        this.sharedState = this.env.sharedState.state
    }
}