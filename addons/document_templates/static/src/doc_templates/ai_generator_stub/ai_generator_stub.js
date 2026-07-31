import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { DocShell } from "../shell/doc_shell";

export class AiGeneratorStub extends Component {
    static template = "document_templates.AiGeneratorStub";
    static components = { DocShell };
}

registry.category("actions").add("doc_ai_generator_stub", AiGeneratorStub);
