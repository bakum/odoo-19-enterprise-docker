/** @odoo-module */

import {Component} from "@odoo/owl"

export class Downloader extends Component {
    static template = "eusign_cp.owl_downloader"
    static props = {
        certificates: {
            type: Array,
            optional: true,
            default: () => []
        },
        title: {type: String, required: true, default: ''},
    }
    saveFile(fileName, array) {
        const blob = new Blob([array], {type: "application/octet-stream"});
        saveAs(blob, fileName);
    }
    onLoadCertificate(el) {
        const elem = this.props.certificates.find(x => x.serial === el.target.innerHTML)
        if (elem) {
            this.saveFile(elem.serial, elem.certificate);
        }
    }
}