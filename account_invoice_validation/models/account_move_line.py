# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("display_type", "company_id")
    def _compute_account_id(self):
        """
        This prevents from removing account on lines when re-computing
        """
        old_line_id_by_account_id = {rec.id: rec.account_id for rec in self}
        ret = super()._compute_account_id()
        for rec in self:
            old_account_id = old_line_id_by_account_id.get(rec.id)
            if not rec.account_id and old_account_id:
                rec.account_id = old_account_id

        return ret
