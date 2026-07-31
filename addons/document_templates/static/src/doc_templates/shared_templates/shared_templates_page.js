import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { user } from "@web/core/user";
import { DocShell } from "../shell/doc_shell";
import { TemplateGrid } from "../templates/template_grid";

export class SharedTemplatesPage extends Component {
    static template = "document_templates.SharedTemplatesPage";
    static components = { DocShell, TemplateGrid };

    get domainExtra() {
        return ["|", ["access_level", "!=", "private"], ["shared_user_ids", "in", [user.userId]]];
    }
}

registry.category("actions").add("doc_shared_templates", SharedTemplatesPage);
