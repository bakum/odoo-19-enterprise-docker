/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import {Verifier} from "./components/verifier/verifier";
import {EUSigner} from "./components/signer/eusigner";
import {NavBar} from "./components/navbar/navbar";


export class OwlSigner extends Component {
    static template = "eusign_cp.owl_signer"
    static props = {}
    static components = {Verifier, EUSigner, NavBar}

    setup() {
        this.state = useState({
            loaded: false,
            signmode: true,
            status_key: '',
        })
        this.env.sharedState.state = this.state;
    }
}