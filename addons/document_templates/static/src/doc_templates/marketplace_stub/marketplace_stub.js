import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";

export class MarketplaceStub extends Component {
    static template = "document_templates.MarketplaceStub";
    static components = { DocShell };
}

registry.category("actions").add("doc_marketplace_stub", MarketplaceStub);
