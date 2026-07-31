import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { user } from "@web/core/user";
import { DocShell } from "../shell/doc_shell";
import { TemplateGrid } from "../templates/template_grid";

export class FavouriteTemplatesPage extends Component {
    static template = "document_templates.FavouriteTemplatesPage";
    static components = { DocShell, TemplateGrid };

    get domainExtra() {
        return [["favorite_user_ids", "in", [user.userId]]];
    }
}

registry.category("actions").add("doc_favourite_templates", FavouriteTemplatesPage);
