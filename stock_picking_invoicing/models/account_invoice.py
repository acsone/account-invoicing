# -*- coding: utf-8 -*-
# Copyright (C) 2019-Today: Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        relation="stock_picking_account_invoice_m2m",
        column1="invoice_id",
        column2="picking_id",
        copy=True,
        readonly=True,
    )

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

    @api.multi
    def action_cancel(self):
        """
        Inherit to update related picking as '2binvoiced' when the invoice is
        cancelled (only for invoices, not refunds)
        :return: bool
        """
        result = super(AccountInvoice, self).action_cancel()
        pickings = self.filtered(
            lambda i: i.picking_ids and
            i.type in ['out_invoice', 'in_invoice']).mapped("picking_ids")
        pickings._set_as_2binvoiced()
        return result

    @api.multi
    def unlink(self):
        """
        Inherit the unlink to update related picking as "2binvoiced"
        (only for invoices, not refunds)
        :return:
        """
        pickings = self.filtered(
            lambda i: i.picking_ids and
            i.type in ['out_invoice', 'in_invoice']).mapped("picking_ids")
        pickings._set_as_2binvoiced()
        return super(AccountInvoice, self).unlink()

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None,
                        description=None, journal_id=None):
        """
        Inherit to put link picking of the invoice into the new refund
        :param invoice: self recordset
        :param date_invoice: str
        :param date: str
        :param description: str
        :param journal_id: int
        :return: dict
        """
        result = super(AccountInvoice, self)._prepare_refund(
            invoice=invoice, date_invoice=date_invoice, date=date,
            description=description, journal_id=journal_id)
        result.update({
            'picking_ids': [(6, False, invoice.picking_ids.ids)],
        })
        return result
