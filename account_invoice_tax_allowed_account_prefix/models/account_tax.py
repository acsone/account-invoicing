# Copyright 2026 ACSONE SA/NV,BCIM
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountTax(models.Model):

    _inherit = "account.tax"

    allowed_account_prefix = fields.Char(
        help=(
            "If set, this tax can only be used on invoice lines whose "
            "account code starts with this prefix."
        ),
    )

    def _is_allowed_for_account(self, account, strict=False):
        """Check if tax is allowed for the given account."""
        self.ensure_one()
        if not account:
            return True
        if not self.allowed_account_prefix:
            return not strict
        return account.code.startswith(self.allowed_account_prefix)

    def _filter_allowed_for_account(self, account, strict=False):
        """Filter taxes allowed for the given account."""
        return self.filtered(
            lambda t: t._is_allowed_for_account(account, strict=strict)
        )
