# -*- coding: utf-8 -*-
# Copyright (C) 2019-Today: Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def _force_compute_invoice_tax_lines(self):
        """
        Force create new invoice taxes for current invoice
        :return: account.invoice.tax recordset
        """
        tax_created = self.env['account.invoice.tax'].browse()
        for record in self:
            taxes_grouped = record.get_taxes_values()
            tax_lines = record.tax_line_ids.browse()
            for tax in taxes_grouped.values():
                tax_lines += tax_lines.new(tax)
            record.tax_line_ids = tax_lines
            tax_created |= tax_lines
        return tax_created
