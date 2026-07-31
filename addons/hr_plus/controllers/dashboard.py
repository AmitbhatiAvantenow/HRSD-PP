# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class DashboardController(http.Controller):
    @http.route("/hr_plus", auth="user")
    def hr_plus(self):
        return request.redirect("/web#action=hr_plus.action_dashboard")

    @http.route("/hr_plus/dashboard", type="jsonrpc", auth="user")
    def dashboard(self):
        return request.env["mn.hr.plus.dashboard"].sudo().data()

    @http.route("/hr_plus/dashboard/people", type="jsonrpc", auth="user")
    def people(self):
        return request.env["mn.hr.plus.dashboard"].sudo().people_data()

    @http.route("/hr_plus/dashboard/training", type="jsonrpc", auth="user")
    def training(self):
        return request.env["mn.hr.plus.dashboard"].sudo().training_data()

    @http.route("/hr_plus/dashboard/engagement", type="jsonrpc", auth="user")
    def engagement(self):
        return request.env["mn.hr.plus.dashboard"].sudo().engagement_data()
