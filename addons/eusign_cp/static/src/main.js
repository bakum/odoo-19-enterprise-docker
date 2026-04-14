/** @odoo-module **/

import {browser} from "@web/core/browser/browser";
import {_t} from "@web/core/l10n/translation";
import {Component, whenReady} from "@odoo/owl";
import { session } from "@web/session";
import {mountComponent} from "@web/env";
import {OwlSigner} from "./signer";

// Mount the Playground component when the document.body is ready
whenReady(async () => {
    // odoo.info = {
    //     db: session.db,
    //     server_version: session.server_version,
    //     server_version_info: session.server_version_info,
    //     isEnterprise: session.server_version_info ? session.server_version_info.slice(-1)[0] === "e" : undefined,
    // };
    // odoo.isReady = false;
    const root = document.getElementById('eusign_cp_signer');
    if (!root) {
        return;
    }
    if (window.__eusignCpMounted) {
        return;
    }
    window.__eusignCpMounted = true;

    const waitForPublicEnv = async (timeoutMs = 7000, stepMs = 50) => {
        const maxAttempts = Math.ceil(timeoutMs / stepMs);
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            if (Component.env) {
                return Component.env;
            }
            await new Promise((resolve) => setTimeout(resolve, stepMs));
        }
        return null;
    };

    const baseEnv = await waitForPublicEnv();
    if (!baseEnv) {
        console.error("EUSignCP: public OWL env is not ready");
        return;
    }
    const env = Object.assign(Object.create(baseEnv), {
        sharedState: {
            state: null,
        },
    });
    const root_mounted = await mountComponent(OwlSigner, root, { name: "Owl EUSignCP", env });
    odoo.__WOWL_DEBUG__ = { root_mounted };
    // odoo.isReady = true;
})

/**
 * This code is iterating over the cause property of an error object to console.error a string
 * containing the stack trace of the error and any errors that caused it.
 * @param {Event} ev
 */
function logError(ev) {
    ev.preventDefault();
    let error = ev?.error || ev.reason;

    if (error.seen) {
        // If an error causes the mount to crash, Owl will reject the mount promise and throw the
        // error. Therefore, this if statement prevents the same error from appearing twice.
        return;
    }
    error.seen = true;

    let errorMessage = error.stack;
    while (error.cause) {
        errorMessage += "\nCaused by: "
        errorMessage += error.cause.stack;
        error = error.cause;
    }
    console.error(errorMessage);
}

browser.addEventListener("error", (ev) => {
    logError(ev)
});
browser.addEventListener("unhandledrejection", (ev) => {
    logError(ev)
});