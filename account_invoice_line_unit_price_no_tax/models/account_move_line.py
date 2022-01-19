# Copyright 2021 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMoveLine(models.Model):

    _inherit = "account.move.line"

    price_unit_no_taxes = fields.Float(
        compute="_compute_price_unit_no_taxes", string="Price without Taxes", store=True
    )

    @api.depends("product_id", "price_unit", "tax_ids")
    def _compute_price_unit_no_taxes(self):
        for line in self:
            tot = line.tax_ids.compute_all(
                line.price_unit, quantity=1, product=line.product_id
            )
            line.price_unit_no_taxes = tot["total_excluded"]
