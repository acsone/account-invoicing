# Copyright 2021 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_cancelled_by_refund = fields.Boolean(
        compute='_compute_is_cancelled_by_refund',
        default=False)

    @api.depends('refund_invoice_ids')
    def _compute_is_cancelled_by_refund(self):
        for invoice in self.filtered(lambda x: x.move_type == 'out_invoice' and
                                     x.state == 'posted' and
                                     x.payment_state == 'paid'):
            cancelled = False
            if invoice.refund_invoice_ids:
                cancelled = True
            invoice.is_cancelled_by_refund = cancelled
