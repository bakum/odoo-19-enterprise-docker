/** @odoo-module **/

export class SignableObject {
    constructor(name, data) {
        this.name = name;
        this.data = data;
    }

    GetName() {
        return this.name;
    }

    GetData() {
        return this.data;
    }
}