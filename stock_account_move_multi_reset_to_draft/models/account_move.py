# Copyright 2024 Tecnativa - Víctor Martínez
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models
from odoo.tools.float_utils import float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_draft(self):
        """If it is a purchase invoice, we will create a new SVL for each line with
        the sum of the value in opposite sign.
        """
        res = super().button_draft()
        for item in self.sudo().filtered(
            lambda x: x.is_inbound
            and any(line.stock_valuation_layer_ids for line in x.line_ids)
        ):
            for line in item.line_ids.filtered("stock_valuation_layer_ids"):
                svls = line.stock_valuation_layer_ids
                value = sum(svls.mapped("value"))
                if not float_is_zero(
                    value, precision_rounding=line.currency_id.rounding
                ):
                    svls[0].copy({"value": -value})
        return res

    def _compute_show_reset_to_draft_button(self):
        """Overwrite the value only if it is already posted and with SVLs.
        We use the same fields for filtering that account uses for the
        show_reset_to_draft_button field.
        """
        _self = self.sudo().filtered(
            lambda x: not x.restrict_mode_hash_table
            and x.state in ("posted", "cancel")
            and any(line.stock_valuation_layer_ids for line in x.line_ids)
        )
        for item in self:
            item.show_reset_to_draft_button = True
        return super(AccountMove, self - _self)._compute_show_reset_to_draft_button()
