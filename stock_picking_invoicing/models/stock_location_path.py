# -*- coding: utf-8 -*-
# Copyright (C) 2019-Today: Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class StockLocationPath(models.Model):
    _name = "stock.location.path"
    _inherit = [
        _name,
        "stock.invoice.state.mixin",
    ]

    @api.multi
    def _prepare_move_copy_values(self, move_to_copy, new_date):
        """
        Inherit to copy the invoice_state
        :param move_to_copy: stock.move recordset
        :param new_date:
        :return: dict
        """
        values = super(StockLocationPath, self)._prepare_move_copy_values(
            move_to_copy, new_date)
        key = 'invoice_state'
        target_obj = self.env['stock.move']
        # Load the default value
        default = target_obj.default_get([key]).get(key)
        values.update({
            key: self.invoice_state or default,
        })
        return values
